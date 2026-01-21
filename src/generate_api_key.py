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
        
        # 尝试多种方法生成API凭证
        api_creds = None
        error_messages = []
        
        # 方法1: 尝试使用derive_api_key（本地派生，不需要API调用）
        try:
            if hasattr(client, 'derive_api_key'):
                # derive_api_key通常只需要nonce，可以本地计算
                import secrets
                nonce = secrets.token_hex(16)
                api_creds = client.derive_api_key(nonce)
                print("✅ 使用本地派生方法生成API凭证")
        except Exception as e1:
            error_messages.append(f"derive_api_key失败: {str(e1)[:100]}")
        
        # 方法2: 尝试create_or_derive_api_creds
        if not api_creds:
            try:
                api_creds = client.create_or_derive_api_creds()
                print("✅ 使用create_or_derive_api_creds生成API凭证")
            except Exception as e2:
                error_messages.append(f"create_or_derive_api_creds失败: {str(e2)[:100]}")
        
        # 方法3: 尝试generate_api_key（旧方法）
        if not api_creds:
            try:
                api_creds = client.generate_api_key()
                print("✅ 使用generate_api_key生成API凭证")
            except Exception as e3:
                error_messages.append(f"generate_api_key失败: {str(e3)[:100]}")
        
        # 如果所有方法都失败，提供手动生成指南
        if not api_creds:
            print("\n" + "=" * 60)
            print("❌ 自动生成API密钥失败")
            print("=" * 60)
            print("\n所有自动生成方法都失败了。请使用以下方法之一：")
            print("\n方法1: 从Polymarket网站手动生成（推荐）")
            print("  1. 访问 https://polymarket.com")
            print("  2. 登录你的账户")
            print("  3. 进入 Settings -> API Keys")
            print("  4. 创建新的API密钥")
            print("  5. 复制 apiKey, secret, passphrase 到 .env 文件")
            print("\n方法2: 使用Polymarket开发者门户")
            print("  访问: https://clob.polymarket.com 或开发者文档")
            print("\n方法3: 检查配置")
            print("  - 确认 POLYMARKET_SIGNATURE_TYPE 正确（0=EOA, 1=Proxy, 2=Email）")
            print("  - 如果是Proxy钱包，确认 POLYMARKET_FUNDER 地址正确")
            print("  - 确认网络连接正常")
            print("\n错误详情:")
            for i, msg in enumerate(error_messages, 1):
                print(f"  {i}. {msg}")
            print("\n" + "=" * 60)
            return
        
        # 成功生成，显示结果
        print("\n" + "=" * 60)
        print("✅ API凭证生成成功！")
        print("=" * 60)
        print(f"\n请将以下内容添加到.env文件：")
        
        api_key = api_creds.get('apiKey', api_creds.get('api_key', ''))
        secret = api_creds.get('secret', '')
        passphrase = api_creds.get('passphrase', '')
        
        print(f"\nPOLYMARKET_API_KEY={api_key}")
        print(f"POLYMARKET_API_SECRET={secret}")
        print(f"POLYMARKET_API_PASSPHRASE={passphrase}")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ 生成API密钥失败: {e}")
        print("\n提示: 如果API端点返回404，可能需要：")
        print("  1. 从Polymarket网站手动生成API密钥")
        print("  2. 检查网络连接和API端点")
        print("  3. 确认账户类型和signature_type配置正确")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_api_key()
