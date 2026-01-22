"""
交易执行模块（最终可用覆盖版）
✅ 修复：
- ApiCreds dict -> ApiCreds 对象（避免 L2 headers 报 'dict' has no attribute api_secret）
- USDC 余额 6 位最小单位显示
- orderbook 兼容 dict / OrderBookSummary 对象（修复 ob.get / 属性差异）
- 兼容 get_order_book / get_orderbook / getOrderBook
- 下单：兼容不同版本 py-clob-client 对 OrderArgs.dict() 的依赖（自建 shim）
- 下单：自动补齐 fee_rate_bps / feeRateBps（修复 KeyError: fee_rate_bps）
- 下单：支持盘口价成交（用 create_market_order 优先；没有则退回 limit）
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any, Tuple, List

from eth_account import Account
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# side 常量（不同版本位置可能不同）
try:
    from py_clob_client.order_builder.constants import BUY, SELL
except Exception:
    BUY, SELL = "BUY", "SELL"

# OrderType（可能存在）
try:
    from py_clob_client.clob_types import OrderType  # noqa
    HAS_ORDER_TYPE = True
except Exception:
    HAS_ORDER_TYPE = False


class _ArgsShim:
    """
    ✅ 关键：兼容那些会调用 args.dict() 的 py-clob-client 版本
    同时提供属性访问（args.price / args.size ...）
    并且 dict() 里同时放 snake_case + camelCase，避免字段名不一致。
    """
    def __init__(self, **kwargs):
        self._d = dict(kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def dict(self, *args, **kwargs):
        return dict(self._d)


class TradingClient:
    def __init__(self, config):
        self.config = config
        self.client: Optional[ClobClient] = None
        self.account = None
        self._initialize_client()

    # -----------------------------
    # 兼容工具
    # -----------------------------
    def _get_method(self, *names):
        for n in names:
            fn = getattr(self.client, n, None)
            if callable(fn):
                return fn
        return None

    def _coerce_api_creds(self, creds: Any) -> Any:
        """dict -> ApiCreds 对象（关键修复：L2 headers 需要 creds.api_secret）"""
        try:
            from py_clob_client.clob_types import ApiCreds
        except Exception:
            return creds

        if isinstance(creds, ApiCreds):
            return creds

        if isinstance(creds, dict):
            api_key = creds.get("apiKey") or creds.get("api_key") or creds.get("API_KEY")
            api_secret = creds.get("secret") or creds.get("api_secret") or creds.get("API_SECRET")
            api_passphrase = creds.get("passphrase") or creds.get("api_passphrase") or creds.get("API_PASSPHRASE")
            return ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase)

        api_key = getattr(creds, "api_key", None) or getattr(creds, "apiKey", None)
        api_secret = getattr(creds, "api_secret", None) or getattr(creds, "secret", None)
        api_passphrase = getattr(creds, "api_passphrase", None) or getattr(creds, "passphrase", None)
        return ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase)

    def _set_api_creds_safely(self, creds: Any) -> bool:
        if not creds:
            return False
        creds_obj = self._coerce_api_creds(creds)

        set_fn = getattr(self.client, "set_api_creds", None)
        if callable(set_fn):
            self.client.set_api_creds(creds_obj)
            return True

        try:
            self.client.creds = creds_obj
            return True
        except Exception:
            return False

    # -----------------------------
    # 初始化
    # -----------------------------
    def _initialize_client(self):
        self.account = Account.from_key(self.config.POLYMARKET_PRIVATE_KEY)

        client_params = {
            "host": self.config.POLYMARKET_HOST,
            "key": self.config.POLYMARKET_PRIVATE_KEY,
            "chain_id": POLYGON,
            "signature_type": self.config.POLYMARKET_SIGNATURE_TYPE,
        }
        if getattr(self.config, "POLYMARKET_FUNDER", None):
            client_params["funder"] = self.config.POLYMARKET_FUNDER

        self.client = ClobClient(**client_params)

        if (
            getattr(self.config, "POLYMARKET_API_KEY", None)
            and getattr(self.config, "POLYMARKET_API_SECRET", None)
            and getattr(self.config, "POLYMARKET_API_PASSPHRASE", None)
        ):
            try:
                from py_clob_client.clob_types import ApiCreds
                api_creds_obj = ApiCreds(
                    api_key=self.config.POLYMARKET_API_KEY,
                    api_secret=self.config.POLYMARKET_API_SECRET,
                    api_passphrase=self.config.POLYMARKET_API_PASSPHRASE,
                )
                self._set_api_creds_safely(api_creds_obj)
            except Exception as e:
                print(f"⚠️ ApiCreds 设置失败: {e}")

        print("✅ 交易客户端初始化成功")

    # -----------------------------
    # 余额（USDC）
    # -----------------------------
    def get_balance(self) -> float:
        """返回单位：USDC（例如 2.2475）"""
        try:
            if hasattr(self.client, "creds") and isinstance(getattr(self.client, "creds"), dict):
                self.client.creds = self._coerce_api_creds(self.client.creds)

            get_fn = self._get_method("get_balance_allowance", "getBalanceAllowance")
            upd_fn = self._get_method("update_balance_allowance", "updateBalanceAllowance")
            if not get_fn:
                print("⚠️ 找不到 get_balance_allowance/getBalanceAllowance")
                return 0.0

            try:
                from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
                params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            except Exception:
                params = {"asset_type": "COLLATERAL"}

            if upd_fn:
                try:
                    upd_fn(params)
                except Exception:
                    pass

            result = get_fn(params)
            bal_raw = result.get("balance") if isinstance(result, dict) else getattr(result, "balance", None)
            if bal_raw is None:
                return 0.0

            raw_str = str(bal_raw).strip()
            if "." in raw_str:
                return float(Decimal(raw_str))
            return float(Decimal(raw_str) / Decimal("1e6"))
        except Exception as e:
            print(f"❌ 获取余额失败: {e}")
            return 0.0

    # -----------------------------
    # Orderbook 兼容
    # -----------------------------
    def _extract_levels(self, ob: Any) -> Tuple[List[Any], List[Any]]:
        if ob is None:
            return [], []
        if isinstance(ob, dict):
            return (ob.get("asks") or []), (ob.get("bids") or [])
        asks = getattr(ob, "asks", None)
        bids = getattr(ob, "bids", None)
        return (asks or []), (bids or [])

    def _level_price(self, lvl: Any) -> Optional[float]:
        if lvl is None:
            return None
        if isinstance(lvl, dict):
            p = lvl.get("price")
        else:
            p = getattr(lvl, "price", None)
        if p is None:
            return None
        try:
            return float(p)
        except Exception:
            return None

    def _level_size(self, lvl: Any) -> Optional[float]:
        if lvl is None:
            return None
        if isinstance(lvl, dict):
            s = lvl.get("size")
        else:
            s = getattr(lvl, "size", None)
        if s is None:
            return None
        try:
            return float(s)
        except Exception:
            return None

    def get_orderbook(self, token_id: str) -> Any:
        fn = self._get_method("get_order_book", "get_orderbook", "getOrderBook")
        if not fn:
            raise AttributeError("无法找到 get_order_book/get_orderbook/getOrderBook 方法")
        return fn(token_id)

    def get_best_price(self, token_id: str, side: str = "buy") -> Optional[float]:
        try:
            ob = self.get_orderbook(token_id)
            asks, bids = self._extract_levels(ob)

            if side == "buy":
                if not asks:
                    return None
                return self._level_price(asks[0])
            else:
                if not bids:
                    return None
                return self._level_price(bids[0])
        except Exception as e:
            print(f"❌ 获取最佳价格失败: {e}")
            return None

    def get_top_levels(self, token_id: str, depth: int = 5) -> Dict[str, List[Tuple[float, float]]]:
        """给你调试盘口用"""
        ob = self.get_orderbook(token_id)
        asks, bids = self._extract_levels(ob)
        out_asks, out_bids = [], []
        for lvl in (asks or [])[:depth]:
            p = self._level_price(lvl)
            s = self._level_size(lvl)
            if p is not None and s is not None:
                out_asks.append((p, s))
        for lvl in (bids or [])[:depth]:
            p = self._level_price(lvl)
            s = self._level_size(lvl)
            if p is not None and s is not None:
                out_bids.append((p, s))
        return {"asks": out_asks, "bids": out_bids}

    # -----------------------------
    # 下单（盘口价成交优先：market order + price limit）
    # -----------------------------
    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        order_type: str = "FAK",   # 盘口成交就用 FAK/FOK
    ) -> Optional[str]:
        """
        ✅ 盘口价成交推荐走 create_market_order（带 price limit + FAK/FOK）
        - BUY: amount=美元（USDC），这里用 size(shares) * price 估算
        - SELL: amount=shares（直接 size）
        同时补齐 fee_rate_bps/feeRateBps，修复 KeyError: fee_rate_bps
        """
        if getattr(self.config, "DRY_RUN", False):
            print(f"🔸 [模拟] {side} size={size} @ price={price}")
            return "simulated_order_id"

        side_u = side.strip().upper()
        if side_u not in ("BUY", "SELL"):
            print(f"❌ side必须BUY/SELL，当前={side}")
            return None

        token_id = str(token_id)
        px = float(price)
        sz = float(size)
        fee_bps = 0  # ✅ 必须给，否则某些版本会 KeyError: fee_rate_bps

        create_market_fn = self._get_method("create_market_order", "createMarketOrder")
        create_limit_fn = self._get_method("create_order", "createOrder")
        post_fn = self._get_method("post_order", "postOrder")
        create_and_post_fn = self._get_method("create_and_post_order", "createAndPostOrder")

        last_err = None

        # ---------- A) 优先：market order（FAK/FOK + price limit） ----------
        if create_market_fn and post_fn:
            try:
                amount = (px * sz) if side_u == "BUY" else sz

                m_args = _ArgsShim(
                    # 同时放 snake + camel，避免版本字段名不一致
                    token_id=token_id,
                    tokenID=token_id,
                    amount=float(amount),
                    side=BUY if side_u == "BUY" else SELL,
                    price=float(px),  # price limit
                    order_type=order_type,
                    orderType=order_type,
                    fee_rate_bps=int(fee_bps),
                    feeRateBps=int(fee_bps),
                )

                signed = create_market_fn(m_args)

                # post_order 的 orderType 参数：有的要关键字 orderType
                try:
                    resp = post_fn(signed, orderType=order_type)
                except TypeError:
                    # 有的只收 (signed, order_type) 或 (signed)
                    try:
                        resp = post_fn(signed, order_type)
                    except TypeError:
                        resp = post_fn(signed)

                oid = self._extract_order_id(resp)
                if oid:
                    return oid
            except Exception as e:
                last_err = e

        # ---------- B) 退回：limit order ----------
        if create_limit_fn and post_fn:
            try:
                l_args = _ArgsShim(
                    token_id=token_id,
                    tokenID=token_id,
                    price=float(px),
                    size=float(sz),
                    side=BUY if side_u == "BUY" else SELL,
                    fee_rate_bps=int(fee_bps),
                    feeRateBps=int(fee_bps),
                )
                signed = create_limit_fn(l_args)
                try:
                    resp = post_fn(signed)
                except Exception:
                    # 有的版本要求 orderType 关键字（即使 limit 也接收）
                    resp = post_fn(signed, orderType=order_type)
                oid = self._extract_order_id(resp)
                if oid:
                    return oid
            except Exception as e:
                last_err = e

        # ---------- C) 最后兜底：create_and_post_order ----------
        if create_and_post_fn:
            try:
                # 仍然用 shim，避免 .dict() 缺失
                payload = _ArgsShim(
                    token_id=token_id,
                    tokenID=token_id,
                    price=float(px),
                    size=float(sz),
                    side=BUY if side_u == "BUY" else SELL,
                    fee_rate_bps=int(fee_bps),
                    feeRateBps=int(fee_bps),
                )
                resp = create_and_post_fn(payload)
                oid = self._extract_order_id(resp)
                if oid:
                    return oid
            except Exception as e:
                last_err = e

        print(f"❌ 下单失败（market/limit/create_and_post 都不行）: {last_err}")
        return None

    def _extract_order_id(self, resp: Any) -> Optional[str]:
        if resp is None:
            return None
        if isinstance(resp, dict):
            oid = resp.get("id") or resp.get("order_id") or resp.get("orderId")
            return str(oid) if oid else None
        oid = getattr(resp, "id", None) or getattr(resp, "order_id", None) or getattr(resp, "orderId", None)
        return str(oid) if oid else str(resp)

    # -----------------------------
    # 订单状态 / 取消
    # -----------------------------
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        if getattr(self.config, "DRY_RUN", False):
            return {"status": "FILLED"}
        fn = self._get_method("get_order", "getOrder")
        if not fn:
            print("⚠️ 找不到 get_order/getOrder")
            return None
        try:
            return fn(order_id)
        except Exception as e:
            print(f"❌ 获取订单状态失败: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        if getattr(self.config, "DRY_RUN", False):
            print(f"🔸 [模拟] cancel {order_id}")
            return True
        fn = self._get_method("cancel_order", "cancelOrder")
        if not fn:
            print("⚠️ 找不到 cancel_order/cancelOrder")
            return False
        try:
            fn(order_id)
            return True
        except Exception as e:
            print(f"❌ 取消订单失败: {e}")
            return False
