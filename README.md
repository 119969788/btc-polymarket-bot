# BTC 15分钟套利机器人

基于Polymarket的BTC 15分钟市场套利机器人，实现**80买90卖**策略。

## 🎯 策略说明

**低买高卖策略**：
- 当价格达到 **$0.80** 时买入
- 当价格达到 **$0.90** 时卖出
- 预期利润：**$0.10 per share (12.5%)**

### 示例：

```
买入价格: $0.80
卖出价格: $0.90
─────────────────
利润:      $0.10 per share
利润率:    12.5%
```

## 🚀 安装

> 📖 **服务器安装**: 如需在Linux服务器上安装，请查看 [INSTALL.md](INSTALL.md) 获取详细步骤。

### 1. 克隆仓库

```bash
git clone https://github.com/119969788/btc-polymarket-bot.git
cd btc-polymarket-bot
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
# 或: source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，配置以下变量：

## 🔐 环境变量配置

### 必需变量

| 变量 | 描述 | 如何获取 |
|------|------|----------|
| `POLYMARKET_PRIVATE_KEY` | 钱包私钥（以0x开头） | 从钱包导出（MetaMask等） |
| `POLYMARKET_API_KEY` | Polymarket CLOB API密钥 | 运行 `python -m src.generate_api_key` |
| `POLYMARKET_API_SECRET` | Polymarket CLOB API密钥 | 运行 `python -m src.generate_api_key` |
| `POLYMARKET_API_PASSPHRASE` | Polymarket CLOB API密码 | 运行 `python -m src.generate_api_key` |

### 交易参数

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `BUY_PRICE` | 买入价格 | 0.80 |
| `SELL_PRICE` | 卖出价格 | 0.90 |
| `ORDER_SIZE` | 每次订单大小（shares） | 5 |
| `DRY_RUN` | 模拟模式（true/false） | true |

## 📋 使用步骤

### 1. 生成API密钥

```bash
python -m src.generate_api_key
```

将输出的API凭证添加到 `.env` 文件中。

### 2. 测试余额

```bash
python -m src.test_balance
```

确保钱包中有足够的USDC余额。

### 3. 运行机器人

#### 模拟模式（推荐先测试）

确保 `.env` 中 `DRY_RUN=true`，然后运行：

```bash
python -m src.arbitrage_bot
```

#### 实盘模式

1. 将 `.env` 中的 `DRY_RUN=false`
2. 确保钱包中有足够的USDC
3. 运行：

```bash
python -m src.arbitrage_bot
```

## 📊 功能特性

✅ **自动发现**活跃的BTC 15分钟市场  
✅ **价格监控**：实时监控UP和DOWN两个方向的价格  
✅ **自动买入**：当价格达到$0.80时自动买入  
✅ **自动卖出**：当价格达到$0.90时自动卖出  
✅ **持仓管理**：跟踪所有持仓，避免重复买入  
✅ **利润统计**：实时统计总投入和总利润  
✅ **模拟模式**：安全测试，不会执行真实交易  
✅ **余额检查**：交易前自动检查余额是否充足  

## 📈 输出示例

```
🚀 BTC 15分钟套利机器人启动
   模式: 🔸 模拟模式
   买入价: $0.80
   卖出价: $0.90
   订单大小: 5 shares
============================================================

🔍 正在查找BTC 15分钟市场...
✅ 找到市场: Will Bitcoin be above $XX,XXX in 15 minutes?
   市场ID: btc-updown-15m-1765301400
✅ UP条件ID: 0x1234...
✅ DOWN条件ID: 0x5678...

💰 当前余额: $100.00 USDC

🔄 开始扫描市场...
============================================================

[扫描 #1] 14:30:15

🎯 [UP] 买入机会！
   当前价格: $0.7950 <= 买入价 $0.80
✅ [UP] 买入成功！持仓: 5 shares @ $0.80

[扫描 #25] 14:32:45

🎯 [UP] 卖出机会！
   当前价格: $0.9050 >= 卖出价 $0.90
✅ [UP] 卖出成功！
   买入价: $0.80
   卖出价: $0.90
   利润: $0.50 (12.50%)

📊 当前状态:
   买入次数: 1
   卖出次数: 1
   总投入: $4.00
   总利润: $0.50
   当前持仓: 0 个
```

## 📁 项目结构

```
btc-polymarket-bot/
├── src/
│   ├── __init__.py
│   ├── arbitrage_bot.py    # 主套利机器人
│   ├── config.py           # 配置加载
│   ├── lookup.py           # 市场查找
│   ├── trading.py          # 交易执行
│   ├── generate_api_key.py # API密钥生成工具
│   └── test_balance.py     # 余额测试工具
├── .env                    # 环境变量（需创建）
├── .env.example            # 环境变量模板
├── .gitignore
├── requirements.txt        # Python依赖
└── README.md              # 本文档
```

## ⚠️ 风险警告

* ⚠️ **不要在没有资金的情况下使用 `DRY_RUN=false`**
* ⚠️ **市场波动可能导致价格无法达到目标价**
* ⚠️ **市场每15分钟关闭一次，注意持仓风险**
* ⚠️ **建议从小额订单开始（ORDER_SIZE=5）**
* ⚠️ **本软件仅供教育用途，使用风险自负**
* ⚠️ **永远不要分享你的私钥给任何人**

## 🔧 故障排除

### "Invalid signature" 错误

* 检查 `POLYMARKET_SIGNATURE_TYPE` 是否与钱包类型匹配
* 重新生成API凭证：`python -m src.generate_api_key`

### 余额显示为 $0 但实际有资金

* 确认私钥对应的是有资金的钱包
* 运行 `python -m src.test_balance` 查看钱包地址

### "No active BTC 15min market found"

* 市场每15分钟开放一次，等待下一个市场
* 检查网络连接
* 手动访问 https://polymarket.com/crypto/15M 确认

### 价格一直无法达到目标价

* 这是正常现象，市场可能不会达到你设定的价格
* 可以调整 `BUY_PRICE` 和 `SELL_PRICE` 以适应市场
* 注意：更高的买入价和更低的卖出价会减少利润空间

## 📚 相关资源

* [Polymarket](https://polymarket.com)
* [BTC 15分钟市场](https://polymarket.com/crypto/15M)
* [py-clob-client 文档](https://github.com/Polymarket/py-clob-client)

## ⚖️ 免责声明

本软件仅供教育用途。交易涉及风险。作者不对任何财务损失负责。请自行研究，永远不要投资超过你能承受损失的资金。
