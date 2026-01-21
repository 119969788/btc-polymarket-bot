# 快速开始指南

## 🚀 5分钟快速安装（Linux服务器）

### 方法1: 使用自动安装脚本（推荐）

```bash
# 克隆项目
git clone https://github.com/119969788/btc-polymarket-bot.git
cd btc-polymarket-bot

# 运行安装脚本
chmod +x scripts/install.sh
./scripts/install.sh
```

### 方法2: 手动安装

```bash
# 1. 克隆项目
git clone https://github.com/119969788/btc-polymarket-bot.git
cd btc-polymarket-bot

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
nano .env  # 编辑配置文件
```

---

## ⚙️ 配置步骤

### 1. 生成API密钥

```bash
source .venv/bin/activate
python -m src.generate_api_key
```

将输出的API凭证复制到`.env`文件。

### 2. 编辑配置文件

```bash
nano .env
```

填写以下必需信息：
- `POLYMARKET_PRIVATE_KEY` - 钱包私钥
- `POLYMARKET_API_KEY` - 从步骤1生成
- `POLYMARKET_API_SECRET` - 从步骤1生成
- `POLYMARKET_API_PASSPHRASE` - 从步骤1生成

### 3. 测试配置

```bash
python -m src.test_balance
```

---

## 🎮 运行机器人

### 模拟模式（测试）

```bash
# 确保DRY_RUN=true在.env中
source .venv/bin/activate
python -m src.arbitrage_bot
```

### 实盘模式

```bash
# 1. 修改.env: DRY_RUN=false
nano .env

# 2. 运行机器人
source .venv/bin/activate
python -m src.arbitrage_bot
```

---

## 🔄 后台运行

### 使用systemd（推荐）

```bash
# 1. 创建服务文件
sudo nano /etc/systemd/system/btc-arbitrage-bot.service

# 2. 添加配置（参考INSTALL.md）

# 3. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable btc-arbitrage-bot.service
sudo systemctl start btc-arbitrage-bot.service

# 4. 查看日志
sudo tail -f /var/log/btc-arbitrage-bot.log
```

### 使用Screen

```bash
screen -S btc-bot
source .venv/bin/activate
python -m src.arbitrage_bot
# 按 Ctrl+A 然后 D 分离会话
```

---

## 📊 常用命令

```bash
# 查看服务状态（systemd）
sudo systemctl status btc-arbitrage-bot.service

# 重启服务
sudo systemctl restart btc-arbitrage-bot.service

# 查看日志
sudo tail -f /var/log/btc-arbitrage-bot.log

# 更新代码
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart btc-arbitrage-bot.service
```

---

## ⚠️ 重要提示

1. **首次运行务必使用模拟模式** (`DRY_RUN=true`)
2. **确保余额充足** - 至少需要 `ORDER_SIZE * BUY_PRICE` USDC
3. **保护私钥** - `.env`文件权限应设置为600
4. **监控日志** - 定期检查运行状态
5. **从小额开始** - 建议 `ORDER_SIZE=5` 开始测试

---

## 📚 详细文档

- **完整安装指南**: [INSTALL.md](INSTALL.md)
- **项目说明**: [README.md](README.md)

---

## 🆘 遇到问题？

1. 查看日志文件
2. 检查`.env`配置
3. 运行 `python -m src.test_balance` 验证配置
4. 参考 [INSTALL.md](INSTALL.md) 的故障排除部分
