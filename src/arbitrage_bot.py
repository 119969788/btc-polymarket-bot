"""BTC 15分钟套利机器人 - 80买90卖策略"""
import time
from datetime import datetime
from typing import Optional, Dict
from src.config import Config
from src.lookup import find_btc_15min_market, get_market_conditions
from src.trading import TradingClient

class ArbitrageBot:
    """套利机器人"""
    
    def __init__(self):
        self.config = Config()
        self.config.validate()
        self.trading_client = TradingClient(self.config)
        self.market_info = None
        self.conditions = None
        self.positions = {}  # 持仓记录 {token_id: {"side": "BUY", "price": 0.80, "size": 5}}
        self.stats = {
            "total_buys": 0,
            "total_sells": 0,
            "total_profit": 0.0,
            "total_invested": 0.0
        }
    
    def find_market(self) -> bool:
        """查找并设置当前市场"""
        print("🔍 正在查找BTC 15分钟市场...")
        market = find_btc_15min_market(self.config.POLYMARKET_HOST)
        
        if not market:
            print("❌ 未找到活跃的BTC 15分钟市场")
            return False
        
        self.market_info = market
        print(f"✅ 找到市场: {market['question']}")
        print(f"   市场ID: {market['market_id']}")
        
        # 获取市场条件
        conditions = get_market_conditions(
            self.config.POLYMARKET_HOST,
            market['market_id']
        )
        
        if not conditions:
            print("❌ 无法获取市场条件（UP/DOWN）")
            return False
        
        self.conditions = conditions
        print(f"✅ UP条件ID: {conditions.get('UP')}")
        print(f"✅ DOWN条件ID: {conditions.get('DOWN')}")
        
        return True
    
    def check_balance(self) -> bool:
        """检查余额"""
        balance = self.trading_client.get_balance()
        print(f"💰 当前余额: ${balance:.2f} USDC")
        
        if balance < self.config.ORDER_SIZE * self.config.BUY_PRICE:
            print(f"⚠️  余额不足，至少需要 ${self.config.ORDER_SIZE * self.config.BUY_PRICE:.2f} USDC")
            return False
        
        return True
    
    def scan_and_trade(self):
        """扫描市场并执行交易"""
        if not self.conditions:
            return
        
        # 检查UP和DOWN两个方向
        for side_name, token_id in self.conditions.items():
            self._check_and_trade_token(token_id, side_name)
    
    def _check_and_trade_token(self, token_id: str, side_name: str):
        """检查单个代币并执行交易"""
        # 获取当前最佳价格
        best_ask = self.trading_client.get_best_price(token_id, side="buy")
        best_bid = self.trading_client.get_best_price(token_id, side="sell")
        
        if not best_ask or not best_bid:
            return
        
        # 检查是否有持仓
        has_position = token_id in self.positions
        
        if not has_position:
            # 没有持仓，检查是否可以买入（Ask价格 <= BUY_PRICE）
            # Ask是卖价，即我们要买入时需要支付的价格
            if best_ask <= self.config.BUY_PRICE:
                print(f"\n🎯 [{side_name}] 触发买入：Ask=${best_ask:.4f} <= ${self.config.BUY_PRICE:.4f}（盘口价成交）")
                
                order_id = self.trading_client.place_order(
                    token_id=token_id,
                    side="BUY",
                    price=self.config.BUY_PRICE,
                    size=self.config.ORDER_SIZE,
                    order_type="GTC"
                )
                
                if order_id:
                    # 等待订单确认
                    time.sleep(1)
                    order_status = self.trading_client.get_order_status(order_id)
                    
                    if order_status and order_status.get("status") == "FILLED":
                        self.positions[token_id] = {
                            "side": "BUY",
                            "price": self.config.BUY_PRICE,
                            "size": self.config.ORDER_SIZE,
                            "order_id": order_id,
                            "side_name": side_name
                        }
                        self.stats["total_buys"] += 1
                        self.stats["total_invested"] += self.config.BUY_PRICE * self.config.ORDER_SIZE
                        print(f"✅ [{side_name}] 买入成功！持仓: {self.config.ORDER_SIZE} shares @ ${self.config.BUY_PRICE:.4f}")
                else:
                    print(f"❌ [{side_name}] 买单提交失败（本场已标记尝试过，不再重复买）")
        else:
            # 有持仓，检查是否可以卖出（价格 >= SELL_PRICE）
            position = self.positions[token_id]
            
            if best_bid >= self.config.SELL_PRICE:
                print(f"\n🎯 [{side_name}] 卖出机会！")
                print(f"   当前价格: ${best_bid:.4f} >= 卖出价 ${self.config.SELL_PRICE:.4f}")
                
                order_id = self.trading_client.place_order(
                    token_id=token_id,
                    side="SELL",
                    price=self.config.SELL_PRICE,
                    size=position["size"],
                    order_type="GTC"
                )
                
                if order_id:
                    # 等待订单确认
                    time.sleep(1)
                    order_status = self.trading_client.get_order_status(order_id)
                    
                    if order_status and order_status.get("status") == "FILLED":
                        # 计算利润
                        profit = (self.config.SELL_PRICE - position["price"]) * position["size"]
                        self.stats["total_profit"] += profit
                        self.stats["total_sells"] += 1
                        
                        print(f"✅ [{side_name}] 卖出成功！")
                        print(f"   买入价: ${position['price']:.4f}")
                        print(f"   卖出价: ${self.config.SELL_PRICE:.4f}")
                        print(f"   利润: ${profit:.4f} ({profit / (position['price'] * position['size']) * 100:.2f}%)")
                        
                        # 清除持仓
                        del self.positions[token_id]
    
    def print_status(self):
        """打印当前状态"""
        print(f"\n📊 当前状态:")
        print(f"   买入次数: {self.stats['total_buys']}")
        print(f"   卖出次数: {self.stats['total_sells']}")
        print(f"   总投入: ${self.stats['total_invested']:.2f}")
        print(f"   总利润: ${self.stats['total_profit']:.2f}")
        print(f"   当前持仓: {len(self.positions)} 个")
        
        if self.positions:
            for token_id, pos in self.positions.items():
                print(f"     - {pos['side_name']}: {pos['size']} shares @ ${pos['price']:.4f}")
    
    def run(self):
        """运行机器人"""
        mode_str = "🔸 模拟模式" if self.config.DRY_RUN else "🔴 实盘模式"
        print(f"\n🚀 BTC 15分钟套利机器人启动")
        print(f"   模式: {mode_str}")
        print(f"   买入价: ${self.config.BUY_PRICE:.2f}")
        print(f"   卖出价: ${self.config.SELL_PRICE:.2f}")
        print(f"   订单大小: {self.config.ORDER_SIZE} shares")
        print("=" * 60)
        
        # 查找市场
        if not self.find_market():
            return
        
        # 检查余额
        if not self.check_balance():
            return
        
        print("\n🔄 开始扫描市场...")
        print("=" * 60)
        
        scan_count = 0
        try:
            while True:
                scan_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[扫描 #{scan_count}] {timestamp}")
                
                # 扫描并交易
                self.scan_and_trade()
                
                # 每10次扫描打印一次状态
                if scan_count % 10 == 0:
                    self.print_status()
                
                # 短暂延迟，避免请求过快
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断")
        finally:
            print("\n" + "=" * 60)
            print("🏁 机器人停止")
            self.print_status()
            print("=" * 60)

if __name__ == "__main__":
    bot = ArbitrageBot()
    bot.run()
