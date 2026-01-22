"""交易执行模块"""
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from eth_account import Account
from decimal import Decimal
from typing import Optional, Dict
import time

# 尝试导入订单相关的类型（如果可用）
try:
    from py_clob_client.clob_types import OrderArgs
    from py_clob_client.order_builder.constants import BUY, SELL
    HAS_ORDER_TYPES = True
except ImportError:
    HAS_ORDER_TYPES = False

class TradingClient:
    """交易客户端"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.account = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化客户端"""
        try:
            # 从私钥创建账户
            self.account = Account.from_key(self.config.POLYMARKET_PRIVATE_KEY)
            
            # 创建ClobClient（只传入基本参数）
            client_params = {
                "host": self.config.POLYMARKET_HOST,
                "key": self.config.POLYMARKET_PRIVATE_KEY,  # 使用私钥，不是API key
                "chain_id": POLYGON,
                "signature_type": self.config.POLYMARKET_SIGNATURE_TYPE,
            }
            
            # 如果有funder地址，添加它（用于Proxy钱包）
            if self.config.POLYMARKET_FUNDER:
                client_params["funder"] = self.config.POLYMARKET_FUNDER
            
            self.client = ClobClient(**client_params)
            
            # 如果有API凭证，设置它们
            if (self.config.POLYMARKET_API_KEY and 
                self.config.POLYMARKET_API_SECRET and 
                self.config.POLYMARKET_API_PASSPHRASE):
                try:
                    api_creds = {
                        "apiKey": self.config.POLYMARKET_API_KEY,
                        "secret": self.config.POLYMARKET_API_SECRET,
                        "passphrase": self.config.POLYMARKET_API_PASSPHRASE
                    }
                    self.client.set_api_creds(api_creds)
                except AttributeError:
                    # 如果set_api_creds方法不存在，尝试其他方式
                    print("⚠️  set_api_creds方法不可用，尝试其他方式设置API凭证")
                    # 某些版本可能需要直接设置属性
                    try:
                        self.client.api_key = self.config.POLYMARKET_API_KEY
                        self.client.api_secret = self.config.POLYMARKET_API_SECRET
                        self.client.api_passphrase = self.config.POLYMARKET_API_PASSPHRASE
                    except:
                        print("⚠️  无法设置API凭证，某些功能可能受限")
            else:
                # 如果没有API凭证，尝试生成或派生
                print("⚠️  未找到API凭证，尝试自动生成...")
                creds = None
                
                # 方法1: 尝试本地派生（不需要API调用）
                try:
                    if hasattr(self.client, 'derive_api_key'):
                        import secrets
                        nonce = secrets.token_hex(16)
                        creds = self.client.derive_api_key(nonce)
                        print("✅ 使用本地派生方法生成API凭证")
                except Exception as e1:
                    pass
                
                # 方法2: 尝试create_or_derive_api_creds
                if not creds:
                    try:
                        if hasattr(self.client, 'create_or_derive_api_creds'):
                            creds = self.client.create_or_derive_api_creds()
                            print("✅ 使用create_or_derive_api_creds生成API凭证")
                    except Exception as e2:
                        pass
                
                # 方法3: 尝试generate_api_key（旧方法）
                if not creds:
                    try:
                        if hasattr(self.client, 'generate_api_key'):
                            creds = self.client.generate_api_key()
                            print("✅ 使用generate_api_key生成API凭证")
                    except Exception as e3:
                        pass
                
                if creds:
                    # 设置API凭证
                    try:
                        if hasattr(self.client, 'set_api_creds'):
                            self.client.set_api_creds(creds)
                        else:
                            # 尝试直接设置属性
                            self.client.api_key = creds.get('apiKey', creds.get('api_key', ''))
                            self.client.api_secret = creds.get('secret', '')
                            self.client.api_passphrase = creds.get('passphrase', '')
                        
                        print("⚠️  已自动生成API凭证，请保存到.env文件：")
                        api_key = creds.get('apiKey', creds.get('api_key', ''))
                        secret = creds.get('secret', '')
                        passphrase = creds.get('passphrase', '')
                        print(f"   POLYMARKET_API_KEY={api_key}")
                        print(f"   POLYMARKET_API_SECRET={secret}")
                        print(f"   POLYMARKET_API_PASSPHRASE={passphrase}")
                    except Exception as e:
                        print(f"⚠️  设置API凭证失败: {e}")
                else:
                    print("⚠️  无法自动生成API凭证")
                    print("   某些功能（如下单）可能需要API凭证")
                    print("   请运行: python -m src.generate_api_key")
                    print("   或参考: docs/API_KEY_GUIDE.md 手动生成")
            
            print("✅ 交易客户端初始化成功")
        except Exception as e:
            raise Exception(f"初始化交易客户端失败: {e}")
    
    def get_balance(self) -> float:
        """获取USDC余额"""
        from decimal import Decimal
        
        USDC_DECIMALS = Decimal("1e6")  # USDC使用6位小数
        
        try:
            # 兼容不同版本的命名：snake_case 和 camelCase
            get_fn = getattr(self.client, "get_balance_allowance", None) or \
                     getattr(self.client, "getBalanceAllowance", None)
            upd_fn = getattr(self.client, "update_balance_allowance", None) or \
                     getattr(self.client, "updateBalanceAllowance", None)
            
            if not get_fn:
                # 如果找不到方法，列出可用的方法帮助调试
                methods = [m for m in dir(self.client) if "balance" in m.lower() or "allow" in m.lower()]
                print(f"\n⚠️  无法找到 get_balance_allowance/getBalanceAllowance 方法")
                print(f"   可用的相关方法: {methods[:10] if methods else '无'}")
                print("   建议: pip install -U py-clob-client==0.34.5")
                return 0.0
            
            # 参数：USDC属于COLLATERAL类型，不需要token_id
            params = {"asset_type": "COLLATERAL"}
            
            # 先刷新缓存（避免返回旧值/0）
            if upd_fn:
                try:
                    upd_fn(params)
                except Exception as e:
                    print(f"⚠️  更新余额缓存失败（继续尝试获取）: {e}")
            
            # 获取余额
            resp = get_fn(params)
            
            # 解析响应
            if isinstance(resp, dict):
                bal_raw = resp.get("balance")
            elif hasattr(resp, "balance"):
                bal_raw = resp.balance
            else:
                raise RuntimeError(f"无法从响应解析balance: {resp}")
            
            if bal_raw is None:
                raise RuntimeError(f"响应中未找到balance字段: {resp}")
            
            # balance通常是最小单位（USDC 6位），需要除以1e6
            # 确保bal_raw是字符串或数字，然后转换为Decimal
            if isinstance(bal_raw, str):
                # 如果已经是字符串，直接使用
                bal_decimal = Decimal(bal_raw)
            else:
                # 如果是数字，转换为字符串再转Decimal
                bal_decimal = Decimal(str(bal_raw))
            
            # 除以1e6转换为实际USDC金额
            balance_decimal = bal_decimal / USDC_DECIMALS
            result = float(balance_decimal)
            
            # 调试信息（仅在开发时使用，可以注释掉）
            # print(f"DEBUG: bal_raw={bal_raw}, type={type(bal_raw)}, result={result}")
            
            return result
            
        except Exception as e:
            print(f"❌ 获取余额失败: {e}")
            import traceback
            traceback.print_exc()
            return 0.0
    
    def get_orderbook(self, token_id: str) -> Optional[Dict]:
        """获取订单簿"""
        try:
            orderbook = self.client.get_orderbook(token_id)
            return orderbook
        except Exception as e:
            print(f"❌ 获取订单簿失败: {e}")
            return None
    
    def get_best_price(self, token_id: str, side: str = "buy") -> Optional[float]:
        """
        获取最佳价格
        
        Args:
            token_id: 代币ID
            side: "buy" 获取最佳卖价（ask），"sell" 获取最佳买价（bid）
        
        Returns:
            最佳价格，如果不存在则返回None
        """
        orderbook = self.get_orderbook(token_id)
        if not orderbook:
            return None
        
        if side == "buy":
            # 买入时看卖单（asks），取最低价
            asks = orderbook.get("asks", [])
            if asks:
                return float(asks[0].get("price", 0))
        else:
            # 卖出时看买单（bids），取最高价
            bids = orderbook.get("bids", [])
            if bids:
                return float(bids[0].get("price", 0))
        
        return None
    
    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: int,
        order_type: str = "GTC"
    ) -> Optional[str]:
        """
        下单
        
        Args:
            token_id: 代币ID
            side: "BUY" 或 "SELL"
            price: 价格
            size: 数量
            order_type: 订单类型 (GTC, IOC, FOK)
        
        Returns:
            订单ID，如果失败则返回None
        """
        if self.config.DRY_RUN:
            print(f"🔸 [模拟] {side} {size} shares @ ${price:.4f}")
            return "simulated_order_id"
        
        try:
            # 获取fee_rate_bps（手续费率）
            # Polymarket的标准费率通常是30-50 bps (0.3%-0.5%)，不是300
            fee_rate_bps = 30  # 默认0.3%手续费（30 basis points）
            
            # 尝试从API获取实际费率
            try:
                # 方法1: 尝试调用get_fee_rate方法
                if hasattr(self.client, 'get_fee_rate'):
                    fee_info = self.client.get_fee_rate()
                    if isinstance(fee_info, dict):
                        fee_rate_bps = fee_info.get('fee_rate_bps', fee_info.get('feeRateBps', 30))
                    elif isinstance(fee_info, (int, float)):
                        fee_rate_bps = int(fee_info)
                # 方法2: 尝试从客户端属性获取
                elif hasattr(self.client, 'fee_rate_bps'):
                    fee_rate_bps = int(self.client.fee_rate_bps)
                elif hasattr(self.client, 'feeRateBps'):
                    fee_rate_bps = int(self.client.feeRateBps)
            except Exception as e:
                # 如果获取失败，使用默认值
                pass
            
            # 确保是整数
            fee_rate_bps = int(fee_rate_bps)
            
            # 使用ClobClient的新API创建订单
            # 方法1: 尝试使用create_and_post_order（新方法）
            if hasattr(self.client, 'create_and_post_order'):
                if HAS_ORDER_TYPES:
                    # 使用OrderArgs类型
                    order_side = BUY if side.upper() == "BUY" else SELL
                    # 尝试不同的参数格式，包括taker属性
                    try:
                        order_args = OrderArgs(
                            token_id=token_id,
                            price=str(price),
                            size=str(size),
                            side=order_side,
                            order_type=order_type,
                            fee_rate_bps=fee_rate_bps,
                            taker=self.account.address  # 添加taker地址
                        )
                    except TypeError as e1:
                        # 如果整数不行，尝试字符串
                        try:
                            order_args = OrderArgs(
                                token_id=token_id,
                                price=str(price),
                                size=str(size),
                                side=order_side,
                                order_type=order_type,
                                fee_rate_bps=str(fee_rate_bps),
                                taker=self.account.address
                            )
                        except TypeError as e2:
                            # 如果都不行，尝试不带fee_rate_bps但带taker
                            try:
                                order_args = OrderArgs(
                                    token_id=token_id,
                                    price=str(price),
                                    size=str(size),
                                    side=order_side,
                                    order_type=order_type,
                                    taker=self.account.address
                                )
                            except TypeError as e3:
                                # 最后尝试最简参数
                                order_args = OrderArgs(
                                    token_id=token_id,
                                    price=str(price),
                                    size=str(size),
                                    side=order_side,
                                    order_type=order_type
                                )
                    resp = self.client.create_and_post_order(order_args)
                else:
                    # 使用字典方式，尝试不同的参数格式
                    order_dict = {
                        "token_id": token_id,
                        "price": str(price),
                        "size": str(size),
                        "side": side.upper(),
                        "order_type": order_type
                    }
                    
                    # 尝试添加fee_rate_bps（不同可能的格式）
                    for fee_key in ["fee_rate_bps", "feeRateBps", "fee_rate", "feeRate"]:
                        try:
                            order_dict[fee_key] = fee_rate_bps
                            resp = self.client.create_and_post_order(order_dict)
                            break
                        except (TypeError, KeyError) as e:
                            if "fee" in str(e).lower():
                                # 如果错误提到fee，尝试下一个格式
                                if fee_key in order_dict:
                                    del order_dict[fee_key]
                                continue
                            else:
                                # 其他错误，直接抛出
                                raise
                    else:
                        # 如果所有fee格式都失败，尝试不带fee参数
                        resp = self.client.create_and_post_order(order_dict)
            # 方法2: 尝试使用create_order（旧方法，需要先构建订单）
            elif hasattr(self.client, 'create_order'):
                # 构建订单对象，尝试不同的fee参数格式
                order_data = {
                    "token_id": token_id,
                    "price": str(price),
                    "size": str(size),
                    "side": side.upper(),
                    "order_type": order_type
                }
                
                # 尝试添加fee_rate_bps
                for fee_key in ["fee_rate_bps", "feeRateBps"]:
                    try:
                        order_data[fee_key] = fee_rate_bps
                        resp = self.client.create_order(order_data)
                        break
                    except (TypeError, KeyError):
                        if fee_key in order_data:
                            del order_data[fee_key]
                else:
                    # 如果都不行，尝试不带fee
                    resp = self.client.create_order(order_data)
            # 方法3: 尝试使用post_order
            elif hasattr(self.client, 'post_order'):
                order_data = {
                    "token_id": token_id,
                    "price": str(price),
                    "size": str(size),
                    "side": side.upper(),
                    "order_type": order_type
                }
                
                # 尝试添加fee_rate_bps
                for fee_key in ["fee_rate_bps", "feeRateBps"]:
                    try:
                        order_data[fee_key] = fee_rate_bps
                        resp = self.client.post_order(order_data)
                        break
                    except (TypeError, KeyError):
                        if fee_key in order_data:
                            del order_data[fee_key]
                else:
                    resp = self.client.post_order(order_data)
            else:
                raise AttributeError("无法找到创建订单的方法")
            
            # 提取订单ID
            if isinstance(resp, dict):
                order_id = resp.get("id") or resp.get("order_id") or resp.get("orderId")
            elif hasattr(resp, 'id'):
                order_id = resp.id
            else:
                order_id = str(resp) if resp else None
            
            if order_id:
                print(f"✅ 订单已提交: {order_id} ({side} {size} @ ${price:.4f})")
                return str(order_id)
            else:
                print(f"❌ 订单提交失败: {resp}")
                return None
                
        except Exception as e:
            print(f"❌ 下单失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """获取订单状态"""
        if self.config.DRY_RUN:
            return {"status": "FILLED", "filled": "5"}
        
        try:
            order = self.client.get_order(order_id)
            return order
        except Exception as e:
            print(f"❌ 获取订单状态失败: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if self.config.DRY_RUN:
            print(f"🔸 [模拟] 取消订单: {order_id}")
            return True
        
        try:
            self.client.cancel_order(order_id)
            print(f"✅ 订单已取消: {order_id}")
            return True
        except Exception as e:
            print(f"❌ 取消订单失败: {e}")
            return False
