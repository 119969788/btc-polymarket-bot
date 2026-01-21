# API密钥生成指南

如果自动生成API密钥失败（出现404错误），可以使用以下方法手动生成。

## 方法1: 从Polymarket网站生成（推荐）

### 步骤：

1. **访问Polymarket网站**
   - 打开 https://polymarket.com
   - 登录你的账户

2. **进入API设置**
   - 点击右上角头像/设置
   - 找到 "API Keys" 或 "Developer Settings"
   - 如果没有看到，尝试访问：https://polymarket.com/settings/api

3. **创建API密钥**
   - 点击 "Create API Key" 或 "Generate New Key"
   - 复制生成的以下信息：
     - `apiKey` (或 `API Key`)
     - `secret` (或 `Secret`)
     - `passphrase` (或 `Passphrase`)

4. **配置到.env文件**
   ```env
   POLYMARKET_API_KEY=你的apiKey
   POLYMARKET_API_SECRET=你的secret
   POLYMARKET_API_PASSPHRASE=你的passphrase
   ```

## 方法2: 使用Polymarket CLOB API

如果网站方法不可用，可以尝试直接调用API：

```python
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
import hashlib

# 你的私钥
private_key = "0x你的私钥"
account = Account.from_key(private_key)

# 创建签名
message = "Create API Key"
message_hash = encode_defunct(text=message)
signed_message = account.sign_message(message_hash)

# 调用API（需要根据实际API文档调整）
# 注意：这只是一个示例，实际API端点可能不同
```

## 方法3: 使用py-clob-client的本地派生

某些版本的py-clob-client支持本地派生API密钥：

```python
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

client = ClobClient(
    host="https://clob.polymarket.com",
    key="你的私钥",
    chain_id=POLYGON,
    signature_type=1  # 根据你的钱包类型调整
)

# 尝试本地派生
try:
    import secrets
    nonce = secrets.token_hex(16)
    creds = client.derive_api_key(nonce)
    print(f"API Key: {creds['apiKey']}")
    print(f"Secret: {creds['secret']}")
    print(f"Passphrase: {creds['passphrase']}")
except Exception as e:
    print(f"派生失败: {e}")
```

## 常见问题

### Q: 为什么会出现404错误？

A: 可能的原因：
- API端点已更改
- 账户类型不匹配（需要正确的signature_type和funder）
- 网络问题或API暂时不可用
- 账户未完成必要的设置

### Q: 如何确定signature_type？

A:
- `0`: EOA钱包（如MetaMask直接导入）
- `1`: Proxy钱包（Magic Link等）
- `2`: Email钱包

### Q: 如何找到funder地址？

A:
- 对于Proxy钱包，funder地址是你的代理合约地址
- 可以在Polymarket网站的钱包设置中查看
- 或者通过 `client.get_funding_address()` 获取

### Q: API密钥是必需的吗？

A:
- 对于某些操作（如下单），API密钥是必需的
- 对于只读操作（如查询余额、订单簿），可能不需要
- 建议生成API密钥以确保所有功能正常

## 验证API密钥

生成API密钥后，运行以下命令验证：

```bash
python -m src.test_balance
```

如果显示余额，说明API密钥配置正确。

## 参考链接

- [Polymarket API文档](https://docs.polymarket.com/)
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)
- [Polymarket开发者门户](https://clob.polymarket.com)
