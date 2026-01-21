"""配置加载模块"""
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Config:
    """配置类"""
    
    # Polymarket API配置
    POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY", "")
    POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")
    POLYMARKET_API_SECRET = os.getenv("POLYMARKET_API_SECRET", "")
    POLYMARKET_API_PASSPHRASE = os.getenv("POLYMARKET_API_PASSPHRASE", "")
    POLYMARKET_HOST = os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com")
    POLYMARKET_SIGNATURE_TYPE = int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "1"))
    POLYMARKET_FUNDER = os.getenv("POLYMARKET_FUNDER", "")
    
    # 交易配置
    BUY_PRICE = float(os.getenv("BUY_PRICE", "0.80"))
    SELL_PRICE = float(os.getenv("SELL_PRICE", "0.90"))
    ORDER_SIZE = int(os.getenv("ORDER_SIZE", "5"))
    DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
    
    # WebSocket配置
    USE_WSS = os.getenv("USE_WSS", "false").lower() == "true"
    POLYMARKET_WS_URL = os.getenv("POLYMARKET_WS_URL", "wss://ws-subscriptions-clob.polymarket.com")
    
    @classmethod
    def validate(cls):
        """验证必需的配置"""
        required = [
            "POLYMARKET_PRIVATE_KEY",
            "POLYMARKET_API_KEY",
            "POLYMARKET_API_SECRET",
            "POLYMARKET_API_PASSPHRASE"
        ]
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"缺少必需的配置: {', '.join(missing)}")
        
        if cls.BUY_PRICE >= cls.SELL_PRICE:
            raise ValueError(f"买入价格 ({cls.BUY_PRICE}) 必须小于卖出价格 ({cls.SELL_PRICE})")
        
        if cls.ORDER_SIZE <= 0:
            raise ValueError("订单大小必须大于0")
