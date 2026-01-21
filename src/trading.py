"""交易执行模块"""
from py_clob_client.client import ClobClient
from py_clob_client.utilities import create_signed_order
from py_clob_client.constants import POLYGON
from eth_account import Account
from decimal import Decimal
from typing import Optional, Dict
import time

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
                try:
                    if hasattr(self.client, 'create_or_derive_api_creds'):
                        creds = self.client.create_or_derive_api_creds()
                    elif hasattr(self.client, 'generate_api_key'):
                        creds = self.client.generate_api_key()
                    else:
                        raise AttributeError("无法找到生成API凭证的方法")
                    
                    # 设置API凭证
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
                    print(f"⚠️  无法自动生成API凭证: {e}")
                    print("   请运行 python -m src.generate_api_key 生成API凭证")
                    print("   或者手动在.env文件中配置API凭证")
            
            print("✅ 交易客户端初始化成功")
        except Exception as e:
            raise Exception(f"初始化交易客户端失败: {e}")
    
    def get_balance(self) -> float:
        """获取USDC余额"""
        try:
            balance = self.client.get_collateral()
            return float(balance) if balance else 0.0
        except Exception as e:
            print(f"❌ 获取余额失败: {e}")
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
            # 创建签名订单
            signed_order = create_signed_order(
                client=self.client,
                token_id=token_id,
                price=str(price),
                size=str(size),
                side=side,
                order_type=order_type,
            )
            
            # 提交订单
            resp = self.client.create_order(signed_order)
            order_id = resp.get("id")
            
            if order_id:
                print(f"✅ 订单已提交: {order_id} ({side} {size} @ ${price:.4f})")
                return order_id
            else:
                print(f"❌ 订单提交失败: {resp}")
                return None
                
        except Exception as e:
            print(f"❌ 下单失败: {e}")
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
