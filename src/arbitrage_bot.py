"""BTC 15分钟套利机器人（自动进入下一场 | 盘口价成交 | 每方向每场只买一次）
策略（按你最新要求）：
- 买入：Ask >= BUY_PRICE（例如 >=0.80）
- 卖出：Bid >= SELL_PRICE（例如 >=0.90） 且必须有持仓
- 成交价：买=best_ask，卖=best_bid（盘口价）
"""

import time
from datetime import datetime
from typing import Dict, Optional

from src.config import Config
from src.lookup import find_btc_15min_market, get_market_conditions
from src.trading import TradingClient


class ArbitrageBot:
    def __init__(self):
        self.config = Config()
        self.config.validate()
        self.trading_client = TradingClient(self.config)

        self.market_info: Optional[Dict] = None
        self.conditions: Optional[Dict[str, str]] = None

        self.positions: Dict[str, Dict] = {}
        self._buy_once_guard = set()

        self._last_roll_check_ts = 0
        self._orderbook_fail_streak = 0

        self.stats = {
            "total_buys": 0,
            "total_sells": 0,
            "total_profit": 0.0,
            "total_invested": 0.0
        }

    def find_market(self) -> bool:
        print("🔍 正在查找BTC 15分钟市场...")
        market = find_btc_15min_market(self.config.POLYMARKET_HOST)
        if not market:
            print("❌ 未找到BTC 15分钟市场")
            return False

        self.market_info = market
        
        # 检查市场是否live
        is_live = market.get('is_live', False)
        start_ts = market.get('start_ts', 0)
        end_ts = market.get('end_ts', 0)
        now_ts = int(time.time())
        
        print(f"✅ 找到市场: {market.get('question')}")
        print(f"   market_id: {market.get('market_id')}")
        print(f"   slug: {market.get('slug')}")
        print(f"   is_live: {is_live}")
        print(f"   当前时间: {now_ts} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_ts))})")
        if start_ts:
            print(f"   开始时间: {start_ts} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_ts))})")
        if end_ts:
            print(f"   结束时间: {end_ts} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_ts))})")
        
        if not is_live:
            print("⚠️  市场未开启，尝试查找下一个活跃市场...")
            # 可以在这里添加重新查找逻辑，或者等待市场开启

        conditions = get_market_conditions(self.config.POLYMARKET_HOST, market["market_id"])
        if not conditions:
            print("❌ 无法获取市场条件（UP/DOWN token_id）")
            return False

        self.conditions = conditions
        print(f"✅ UP TokenID: {conditions.get('UP')}")
        print(f"✅ DOWN TokenID: {conditions.get('DOWN')}")
        return True

    def _roll_market_if_needed(self, force: bool = False) -> bool:
        now = time.time()
        if not force and (now - self._last_roll_check_ts) < 10:
            return True
        self._last_roll_check_ts = now

        latest = find_btc_15min_market(self.config.POLYMARKET_HOST)
        if not latest:
            return True

        cur_slug = (self.market_info or {}).get("slug") or ""
        latest_slug = latest.get("slug") or ""

        if latest_slug and cur_slug and latest_slug != cur_slug:
            print(f"\n🔁 发现新场次：{cur_slug} -> {latest_slug}，正在切换...")
            self.market_info = latest

            conditions = get_market_conditions(self.config.POLYMARKET_HOST, latest["market_id"])
            if not conditions:
                print("❌ 新场次无法获取 UP/DOWN token_id，稍后重试...")
                return False

            self.conditions = conditions

            if self.positions:
                print("🧹 切场：清空上一场持仓记录（避免跨场 token_id 不一致）")
                self.positions.clear()

            self._orderbook_fail_streak = 0

            print(f"✅ 已切换到新场: {latest.get('question')}")
            print(f"   market_id: {latest.get('market_id')}")
            print(f"   slug: {latest_slug}")
            print(f"✅ UP TokenID: {conditions.get('UP')}")
            print(f"✅ DOWN TokenID: {conditions.get('DOWN')}")
            return True

        if self._orderbook_fail_streak >= 8:
            print("⚠️ orderbook 连续失败，强制重找市场...")
            self._orderbook_fail_streak = 0
            return self.find_market()

        return True

    def check_balance(self) -> bool:
        balance = self.trading_client.get_balance()
        print(f"💰 当前余额: ${balance:.6f} USDC")
        return True

    def _pct(self, price: float) -> float:
        p = float(price)
        if p < 0:
            p = 0.0
        if p > 1:
            p = 1.0
        return p * 100.0

    def scan_and_trade(self):
        if not self.conditions or not self.market_info:
            return
        for side_name, token_id in self.conditions.items():
            self._check_and_trade_token(token_id, side_name)

    def _check_and_trade_token(self, token_id: str, side_name: str):
        slug = (self.market_info or {}).get("slug") or ""
        buy_guard_key = (slug, side_name)

        best_ask = self.trading_client.get_best_price(token_id, side="buy")
        best_bid = self.trading_client.get_best_price(token_id, side="sell")

        if best_ask is None or best_bid is None:
            self._orderbook_fail_streak += 1
            return
        else:
            self._orderbook_fail_streak = 0

        print(
            f"   🎲 [{side_name}] Ask(买): ${best_ask:.4f} ({self._pct(best_ask):.2f}%) | "
            f"Bid(卖): ${best_bid:.4f} ({self._pct(best_bid):.2f}%)"
        )

        has_position = token_id in self.positions
        already_tried_buy = buy_guard_key in self._buy_once_guard

        # ✅ 买入：Ask <= BUY_PRICE（价格低时买入）
        if (not has_position) and (not already_tried_buy):
            if best_ask <= float(self.config.BUY_PRICE):
                print(f"\n🎯 [{side_name}] 触发买入：Ask=${best_ask:.4f} <= {self.config.BUY_PRICE:.4f}（盘口价成交）")
                
                # 标准化价格：真实ask + 小buffer，最大0.99
                order_price = min(0.99, best_ask + 0.005)
                order_price = round(order_price, 4)
                order_size = round(float(self.config.ORDER_SIZE), 2)

                order_id = self.trading_client.place_order(
                    token_id=token_id,
                    side="BUY",
                    price=order_price,
                    size=order_size,
                    order_type="FOK",  # 使用FOK确保全成或取消
                )

                self._buy_once_guard.add(buy_guard_key)

                if order_id:
                    self.positions[token_id] = {
                        "side": "BUY",
                        "price": float(best_ask),
                        "size": float(self.config.ORDER_SIZE),
                        "order_id": order_id,
                        "side_name": side_name,
                        "slug": slug,
                    }
                    self.stats["total_buys"] += 1
                    self.stats["total_invested"] += float(best_ask) * float(self.config.ORDER_SIZE)
                    print(f"✅ [{side_name}] 买单已提交: {order_id}")
                else:
                    print(f"❌ [{side_name}] 买单提交失败（本场已标记尝试过，不再重复买）")

        # ✅ 卖出：Bid >= SELL_PRICE 且有持仓
        if has_position:
            pos = self.positions[token_id]
            if best_bid >= float(self.config.SELL_PRICE):
                # 标准化价格：使用合理卖价
                order_price = max(0.01, best_bid - 0.005)
                order_price = round(order_price, 4)
                order_size = round(float(pos["size"]), 2)
                print(f"\n🎯 [{side_name}] 触发卖出：Bid=${best_bid:.4f} >= {self.config.SELL_PRICE:.4f}（盘口价成交）")

                order_id = self.trading_client.place_order(
                    token_id=token_id,
                    side="SELL",
                    price=order_price,
                    size=order_size,
                    order_type="FOK",  # 使用FOK确保全成或取消
                )

                if order_id:
                    profit = (float(best_bid) - float(pos["price"])) * float(pos["size"])
                    self.stats["total_profit"] += profit
                    self.stats["total_sells"] += 1
                    print(f"✅ [{side_name}] 卖单已提交: {order_id} | 估算利润: ${profit:.4f}")
                    del self.positions[token_id]
                else:
                    print(f"❌ [{side_name}] 卖单提交失败（下一轮继续尝试）")

    def print_status(self):
        print(f"\n📊 当前状态:")
        print(f"   买入次数: {self.stats['total_buys']}")
        print(f"   卖出次数: {self.stats['total_sells']}")
        print(f"   总投入: ${self.stats['total_invested']:.4f}")
        print(f"   总利润: ${self.stats['total_profit']:.4f}")
        print(f"   当前持仓: {len(self.positions)} 个")
        if self.positions:
            for _, pos in self.positions.items():
                print(f"     - {pos['side_name']}: {pos['size']} @ ${pos['price']:.4f} (slug={pos.get('slug')})")

    def run(self):
        mode_str = "🔸 模拟模式" if self.config.DRY_RUN else "🔴 实盘模式"
        print(f"\n🚀 BTC 15分钟套利机器人启动")
        print(f"   模式: {mode_str}")
        print(f"   买入价: ${self.config.BUY_PRICE:.2f} ({self.config.BUY_PRICE*100:.0f}%)")
        print(f"   卖出价: ${self.config.SELL_PRICE:.2f} ({self.config.SELL_PRICE*100:.0f}%)")
        print(f"   订单大小: {self.config.ORDER_SIZE} shares")
        print("=" * 60)

        if not self.find_market():
            return

        self.check_balance()

        print("\n🔄 开始扫描市场（自动进入下一场已开启）...")
        print("=" * 60)

        scan_count = 0
        try:
            while True:
                scan_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[扫描 #{scan_count}] {timestamp}")

                if not self._roll_market_if_needed():
                    time.sleep(2)
                    continue

                self.scan_and_trade()

                if scan_count % 20 == 0:
                    self.print_status()

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断")
        finally:
            print("\n" + "=" * 60)
            print("🏁 机器人停止")
            self.print_status()
            print("=" * 60)


if __name__ == "__main__":
    ArbitrageBot().run()
