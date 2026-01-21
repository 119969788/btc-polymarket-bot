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
        
        # 创建客户端（使用私钥初始化）
        client_params = {
            "host": config.POLYMARKET_HOST,
            "key": config.POLYMARKET_PRIVATE_KEY,
            "chain_id": POLYGON,
            "signature_type": config.POLYMARKET_SIGNATURE_TYPE,
        }
        
        # 如果有funder地址，添加它（用于Proxy钱包）
        if config.POLYMARKET_FUNDER:
            client_params["funder"] = config.POLYMARKET_FUNDER
        
        client = ClobClient(**client_params)
        
        # 生成或派生API凭证
        try:
            api_creds = client.create_or_derive_api_creds()
        except AttributeError:
            # 如果方法不存在，尝试旧方法
            try:
                api_creds = client.generate_api_key()
            except:
                raise Exception("无法生成API凭证，请检查py-clob-client版本")
        
        print("\n" + "=" * 60)
        print("✅ API凭证生成成功！")
        print("=" * 60)
        print(f"\n请将以下内容添加到.env文件：")
        print(f"\nPOLYMARKET_API_KEY={api_creds.get('apiKey', api_creds.get('api_key', ''))}")
        print(f"POLYMARKET_API_SECRET={api_creds.get('secret', '')}")
        print(f"POLYMARKET_API_PASSPHRASE={api_creds.get('passphrase', '')}")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ 生成API密钥失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_api_key()
