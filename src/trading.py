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
        try:
            # 方法1: 尝试使用getBalanceAllowance（新方法）
            if hasattr(self.client, 'getBalanceAllowance'):
                try:
                    # 尝试导入类型（如果可用）
                    try:
                        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
                        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
                        result = self.client.getBalanceAllowance(params)
                        # 提取余额
                        if hasattr(result, 'balance'):
                            return float(result.balance)
                        elif isinstance(result, dict):
                            return float(result.get('balance', 0))
                    except ImportError:
                        # 如果类型不可用，使用字典方式
                        result = self.client.getBalanceAllowance({
                            'asset_type': 'COLLATERAL'
                        })
                        if isinstance(result, dict):
                            return float(result.get('balance', 0))
                        return float(result) if result else 0.0
                except Exception as e1:
                    print(f"⚠️  getBalanceAllowance失败: {e1}")
            
            # 方法2: 尝试使用get_balance（可能的旧方法）
            if hasattr(self.client, 'get_balance'):
                try:
                    balance = self.client.get_balance()
                    return float(balance) if balance else 0.0
                except Exception as e2:
                    print(f"⚠️  get_balance失败: {e2}")
            
            # 方法3: 尝试使用get_collateral（如果存在）
            if hasattr(self.client, 'get_collateral'):
                try:
                    balance = self.client.get_collateral()
                    return float(balance) if balance else 0.0
                except Exception as e3:
                    print(f"⚠️  get_collateral失败: {e3}")
            
            # 方法4: 尝试直接调用API端点
            try:
                # 使用底层的get方法
                if hasattr(self.client, 'get'):
                    response = self.client.get('/balance')
                    if isinstance(response, dict):
                        return float(response.get('balance', response.get('collateral', 0)))
            except Exception as e4:
                pass
            
            # 如果所有方法都失败
            raise AttributeError("无法找到获取余额的方法。请检查py-clob-client版本")
            
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
            # 使用ClobClient的新API创建订单
            # 方法1: 尝试使用create_and_post_order（新方法）
            if hasattr(self.client, 'create_and_post_order'):
                if HAS_ORDER_TYPES:
                    # 使用OrderArgs类型
                    order_side = BUY if side.upper() == "BUY" else SELL
                    order_args = OrderArgs(
                        token_id=token_id,
                        price=str(price),
                        size=str(size),
                        side=order_side,
                        order_type=order_type
                    )
                    resp = self.client.create_and_post_order(order_args)
                else:
                    # 使用字典方式
                    resp = self.client.create_and_post_order({
                        "token_id": token_id,
                        "price": str(price),
                        "size": str(size),
                        "side": side.upper(),
                        "order_type": order_type
                    })
            # 方法2: 尝试使用create_order（旧方法，需要先构建订单）
            elif hasattr(self.client, 'create_order'):
                # 构建订单对象
                order_data = {
                    "token_id": token_id,
                    "price": str(price),
                    "size": str(size),
                    "side": side.upper(),
                    "order_type": order_type
                }
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
