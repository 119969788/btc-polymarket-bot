"""生成Polymarket API密钥"""
from eth_account import Account
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from src.config import Config
import os

def generate_api_key():
    """生成API密钥"""
    config = Config()
    
    if not config.POLYMARKET_PRIVATE_KEY:
        print("❌ 请在.env文件中设置POLYMARKET_PRIVATE_KEY")
        return
    
    try:
        # 从私钥创建账户
        account = Account.from_key(config.POLYMARKET_PRIVATE_KEY)
        print(f"✅ 钱包地址: {account.address}")
        
        # 创建临时客户端（不需要API密钥）
        client = ClobClient(
            host=config.POLYMARKET_HOST,
            key="",  # 临时
            secret="",
            passphrase="",
            signature_type=config.POLYMARKET_SIGNATURE_TYPE,
            chain_id=POLYGON,
        )
        
        # 生成API凭证
        api_creds = client.generate_api_key()
        
        print("\n" + "=" * 60)
        print("✅ API凭证生成成功！")
        print("=" * 60)
        print(f"\n请将以下内容添加到.env文件：")
        print(f"\nPOLYMARKET_API_KEY={api_creds['apiKey']}")
        print(f"POLYMARKET_API_SECRET={api_creds['secret']}")
        print(f"POLYMARKET_API_PASSPHRASE={api_creds['passphrase']}")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ 生成API密钥失败: {e}")

if __name__ == "__main__":
    generate_api_key()
