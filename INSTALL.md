# 服务器安装详细流程

本文档提供在Linux服务器上安装和运行BTC 15分钟套利机器人的详细步骤。

## 📋 前置要求

- Linux服务器（Ubuntu 20.04+ / CentOS 7+ / Debian 10+）
- Python 3.8 或更高版本
- 至少 1GB 可用内存
- 稳定的网络连接
- 已配置的Polymarket账户和API凭证

---

## 🔧 步骤 1: 系统环境准备

### 1.1 更新系统包

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 1.2 安装Python和pip

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git

# CentOS/RHEL
sudo yum install -y python3 python3-pip git
```

### 1.3 验证Python版本

```bash
python3 --version
# 应该显示 Python 3.8 或更高版本
```

---

## 📥 步骤 2: 克隆项目

### 2.1 克隆仓库

```bash
cd ~
git clone https://github.com/119969788/btc-polymarket-bot.git
cd btc-polymarket-bot
```

### 2.2 查看项目结构

```bash
ls -la
```

---

## 🐍 步骤 3: 创建虚拟环境

### 3.1 创建虚拟环境

```bash
python3 -m venv .venv
```

### 3.2 激活虚拟环境

```bash
source .venv/bin/activate
```

**注意**: 激活后，命令行提示符前会显示 `(.venv)`

### 3.3 升级pip

```bash
pip install --upgrade pip
```

---

## 📦 步骤 4: 安装依赖

### 4.1 安装Python包

```bash
pip install -r requirements.txt
```

### 4.2 验证安装

```bash
pip list | grep -E "py-clob-client|python-dotenv|web3"
```

应该看到以下包：
- py-clob-client
- python-dotenv
- web3
- eth-account

---

## 🔐 步骤 5: 配置环境变量

### 5.1 复制环境变量模板

```bash
cp .env.example .env
```

### 5.2 编辑配置文件

```bash
nano .env
# 或使用 vim: vim .env
```

### 5.3 填写配置信息

```env
# Polymarket API配置
POLYMARKET_PRIVATE_KEY=0x你的私钥（从钱包导出）
POLYMARKET_API_KEY=你的API密钥
POLYMARKET_API_SECRET=你的API密钥
POLYMARKET_API_PASSPHRASE=你的API密码

# 交易配置
POLYMARKET_HOST=https://clob.polymarket.com
POLYMARKET_SIGNATURE_TYPE=1
POLYMARKET_FUNDER=0x你的钱包地址

# 套利策略参数
BUY_PRICE=0.80
SELL_PRICE=0.90
ORDER_SIZE=5
DRY_RUN=true

# WebSocket配置（可选）
USE_WSS=false
POLYMARKET_WS_URL=wss://ws-subscriptions-clob.polymarket.com
```

**重要提示**:
- `POLYMARKET_PRIVATE_KEY`: 从MetaMask或其他钱包导出，以`0x`开头
- `DRY_RUN=true`: 首次测试时保持为`true`（模拟模式）
- 保存文件：`Ctrl+O`，然后`Enter`，最后`Ctrl+X`退出（nano编辑器）

### 5.4 设置文件权限（安全）

```bash
chmod 600 .env
```

---

## 🔑 步骤 6: 生成API密钥

### 6.1 生成API凭证

```bash
python -m src.generate_api_key
```

### 6.2 复制输出的API凭证

将输出的以下内容添加到`.env`文件：

```
POLYMARKET_API_KEY=生成的密钥
POLYMARKET_API_SECRET=生成的密钥
POLYMARKET_API_PASSPHRASE=生成的密码
```

### 6.3 重新编辑.env文件

```bash
nano .env
```

更新API凭证，保存退出。

---

## ✅ 步骤 7: 测试配置

### 7.1 测试余额查询

```bash
python -m src.test_balance
```

**预期输出**:
```
======================================================================
POLYMARKET余额测试
======================================================================
...
💰 余额: $XX.XX USDC
======================================================================
测试完成
======================================================================
```

如果余额显示为`$0.00`，检查：
- 私钥是否正确
- 钱包地址是否匹配
- API凭证是否正确

### 7.2 测试市场查找（可选）

可以手动运行查找功能验证市场API是否正常。

---

## 🚀 步骤 8: 首次运行（模拟模式）

### 8.1 确认DRY_RUN=true

```bash
grep DRY_RUN .env
# 应该显示: DRY_RUN=true
```

### 8.2 运行机器人

```bash
python -m src.arbitrage_bot
```

### 8.3 观察输出

应该看到：
- ✅ 找到市场
- ✅ 余额检查通过
- 🔸 模拟模式标识
- 扫描日志

按 `Ctrl+C` 停止运行。

---

## 🔄 步骤 9: 配置后台运行（使用systemd）

### 9.1 创建systemd服务文件

```bash
sudo nano /etc/systemd/system/btc-arbitrage-bot.service
```

### 9.2 添加服务配置

```ini
[Unit]
Description=BTC 15min Arbitrage Bot
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/home/你的用户名/btc-polymarket-bot
Environment="PATH=/home/你的用户名/btc-polymarket-bot/.venv/bin"
ExecStart=/home/你的用户名/btc-polymarket-bot/.venv/bin/python -m src.arbitrage_bot
Restart=always
RestartSec=10
StandardOutput=append:/var/log/btc-arbitrage-bot.log
StandardError=append:/var/log/btc-arbitrage-bot-error.log

[Install]
WantedBy=multi-user.target
```

**重要**: 替换以下内容：
- `你的用户名`: 你的Linux用户名
- 检查路径是否正确

### 9.3 重新加载systemd

```bash
sudo systemctl daemon-reload
```

### 9.4 启用服务（开机自启）

```bash
sudo systemctl enable btc-arbitrage-bot.service
```

### 9.5 启动服务

```bash
sudo systemctl start btc-arbitrage-bot.service
```

### 9.6 检查服务状态

```bash
sudo systemctl status btc-arbitrage-bot.service
```

### 9.7 查看日志

```bash
# 实时查看日志
sudo tail -f /var/log/btc-arbitrage-bot.log

# 查看错误日志
sudo tail -f /var/log/btc-arbitrage-bot-error.log
```

---

## 🔄 步骤 10: 使用Screen/Tmux（替代方案）

如果不想使用systemd，可以使用screen或tmux：

### 10.1 安装Screen

```bash
# Ubuntu/Debian
sudo apt install -y screen

# CentOS/RHEL
sudo yum install -y screen
```

### 10.2 创建Screen会话

```bash
cd ~/btc-polymarket-bot
source .venv/bin/activate
screen -S btc-bot
```

### 10.3 运行机器人

```bash
python -m src.arbitrage_bot
```

### 10.4 分离Screen会话

按 `Ctrl+A`，然后按 `D`

### 10.5 重新连接会话

```bash
screen -r btc-bot
```

### 10.6 列出所有会话

```bash
screen -ls
```

---

## 📊 步骤 11: 切换到实盘模式

### 11.1 停止服务（如果正在运行）

```bash
sudo systemctl stop btc-arbitrage-bot.service
```

### 11.2 编辑配置文件

```bash
nano .env
```

将 `DRY_RUN=true` 改为 `DRY_RUN=false`

### 11.3 确认余额充足

```bash
python -m src.test_balance
```

确保余额足够执行交易（至少 `ORDER_SIZE * BUY_PRICE`）

### 11.4 重新启动服务

```bash
sudo systemctl start btc-arbitrage-bot.service
```

### 11.5 密切监控

```bash
sudo tail -f /var/log/btc-arbitrage-bot.log
```

---

## 🛠️ 常用管理命令

### 服务管理（systemd）

```bash
# 启动服务
sudo systemctl start btc-arbitrage-bot.service

# 停止服务
sudo systemctl stop btc-arbitrage-bot.service

# 重启服务
sudo systemctl restart btc-arbitrage-bot.service

# 查看状态
sudo systemctl status btc-arbitrage-bot.service

# 禁用开机自启
sudo systemctl disable btc-arbitrage-bot.service

# 启用开机自启
sudo systemctl enable btc-arbitrage-bot.service
```

### 日志管理

```bash
# 查看最新日志（最后50行）
sudo tail -n 50 /var/log/btc-arbitrage-bot.log

# 实时查看日志
sudo tail -f /var/log/btc-arbitrage-bot.log

# 查看错误日志
sudo tail -f /var/log/btc-arbitrage-bot-error.log

# 清空日志（谨慎使用）
sudo truncate -s 0 /var/log/btc-arbitrage-bot.log
```

### 更新代码

```bash
cd ~/btc-polymarket-bot
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart btc-arbitrage-bot.service
```

---

## 🔍 故障排除

### 问题1: 服务无法启动

```bash
# 检查服务状态
sudo systemctl status btc-arbitrage-bot.service

# 查看详细错误
sudo journalctl -u btc-arbitrage-bot.service -n 50
```

### 问题2: 找不到市场

- 检查网络连接
- 验证 `POLYMARKET_HOST` 配置
- 手动访问 https://polymarket.com/crypto/15M 确认市场存在

### 问题3: 余额为0

- 运行 `python -m src.test_balance` 检查
- 验证私钥和钱包地址
- 确认API凭证正确

### 问题4: 权限错误

```bash
# 检查.env文件权限
ls -la .env
# 应该是 600 (rw-------)

# 如果不对，修复权限
chmod 600 .env
```

### 问题5: Python模块未找到

```bash
# 确保虚拟环境已激活
source .venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

---

## 🔒 安全建议

1. **保护私钥**
   - `.env` 文件权限设置为 `600`
   - 不要将 `.env` 提交到Git
   - 定期备份私钥（加密存储）

2. **防火墙配置**
   - 只开放必要的端口
   - 使用SSH密钥而非密码登录

3. **定期更新**
   - 定期更新系统和Python包
   - 关注项目更新和安全补丁

4. **监控和告警**
   - 设置日志监控
   - 配置异常告警（可选）

---

## 📝 检查清单

安装完成后，确认以下项目：

- [ ] Python 3.8+ 已安装
- [ ] 虚拟环境已创建并激活
- [ ] 所有依赖已安装
- [ ] `.env` 文件已配置
- [ ] API凭证已生成并配置
- [ ] 余额测试通过
- [ ] 模拟模式测试成功
- [ ] 服务已配置（systemd或screen）
- [ ] 日志可以正常查看
- [ ] 实盘模式前已充分测试

---

## 📞 获取帮助

如果遇到问题：

1. 查看日志文件
2. 检查配置文件
3. 验证网络连接
4. 参考README.md文档
5. 检查GitHub Issues

---

## 🎉 完成！

如果所有步骤都成功完成，你的BTC套利机器人现在应该已经在服务器上运行了！

**下一步**:
- 监控日志确保正常运行
- 在模拟模式下观察一段时间
- 确认策略符合预期后再切换到实盘模式
- 定期检查余额和交易记录

祝交易顺利！🚀
