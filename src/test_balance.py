"""测试余额"""
from src.config import Config
from src.trading import TradingClient

def test_balance():
    """测试余额"""
    print("=" * 60)
    print("POLYMARKET余额测试")
    print("=" * 60)
    
    try:
        config = Config()
        config.validate()
        
        print(f"\n主机: {config.POLYMARKET_HOST}")
        print(f"签名类型: {config.POLYMARKET_SIGNATURE_TYPE}")
        print(f"私钥: {'✓' if config.POLYMARKET_PRIVATE_KEY else '✗'}")
        print(f"API密钥: {'✓' if config.POLYMARKET_API_KEY else '✗'}")
        print(f"API密钥: {'✓' if config.POLYMARKET_API_SECRET else '✗'}")
        print(f"API密码: {'✓' if config.POLYMARKET_API_PASSPHRASE else '✗'}")
        print("=" * 60)
        
        print("\n1. 创建交易客户端...")
        trading_client = TradingClient(config)
        
        print("\n2. 获取钱包地址...")
        from eth_account import Account
        account = Account.from_key(config.POLYMARKET_PRIVATE_KEY)
        print(f"   ✓ 地址: {account.address}")
        
        print("\n3. 获取USDC余额...")
        balance = trading_client.get_balance()
        print(f"   💰 余额: ${balance:.2f} USDC")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    test_balance()
