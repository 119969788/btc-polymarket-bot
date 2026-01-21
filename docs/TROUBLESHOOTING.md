# 故障排除指南

## 常见错误和解决方案

### 1. ImportError: cannot import name 'create_signed_order'

**错误信息**:
```
ImportError: cannot import name 'create_signed_order' from 'py_clob_client.utilities'
```

**原因**: 
- 代码已更新，但服务器上的代码还没有拉取最新版本
- `create_signed_order` 在新版本的 `py-clob-client` 中已不存在

**解决方案**:

1. **更新代码**（推荐）:
   ```bash
   cd ~/btc-polymarket-bot
   git pull origin main
   ```

2. **如果git pull失败，检查是否有本地修改**:
   ```bash
   git status
   # 如果有修改，先保存或丢弃
   git stash  # 保存修改
   # 或
   git reset --hard origin/main  # 丢弃本地修改（谨慎使用）
   ```

3. **重新安装依赖**（如果需要）:
   ```bash
   source .venv/bin/activate
   pip install --upgrade py-clob-client
   ```

4. **验证修复**:
   ```bash
   python -m src.test_balance
   ```

---

### 2. PolyApiException[status_code=404]

**错误信息**:
```
PolyApiException[status_code=404, error_message=... Not Found]
```

**原因**: API端点不存在或已更改

**解决方案**:
- 参考 [API_KEY_GUIDE.md](API_KEY_GUIDE.md) 手动生成API密钥
- 检查 `POLYMARKET_SIGNATURE_TYPE` 和 `POLYMARKET_FUNDER` 配置

---

### 3. ClobClient.__init__() got an unexpected keyword argument 'secret'

**错误信息**:
```
TypeError: ClobClient.__init__() got an unexpected keyword argument 'secret'
```

**原因**: 使用了错误的初始化参数

**解决方案**:
- 确保代码是最新版本: `git pull origin main`
- API凭证应该通过 `set_api_creds()` 设置，而不是在初始化时传入

---

### 4. 余额显示为 $0.00

**可能原因**:
- 私钥不正确
- 钱包地址不匹配
- API凭证未正确配置
- 账户确实没有余额

**解决方案**:
1. 验证钱包地址:
   ```bash
   python -c "from eth_account import Account; from src.config import Config; c=Config(); a=Account.from_key(c.POLYMARKET_PRIVATE_KEY); print(f'地址: {a.address}')"
   ```

2. 检查API凭证:
   ```bash
   python -m src.test_balance
   ```

3. 确认Polymarket账户中有USDC余额

---

### 5. 找不到市场

**错误信息**:
```
❌ 未找到活跃的BTC 15分钟市场
```

**解决方案**:
- 市场每15分钟开放一次，等待下一个市场
- 检查网络连接
- 手动访问 https://polymarket.com/crypto/15M 确认市场存在

---

### 6. 权限错误

**错误信息**:
```
PermissionError: [Errno 13] Permission denied
```

**解决方案**:
```bash
# 检查文件权限
ls -la .env

# 设置正确的权限
chmod 600 .env
```

---

### 7. Python模块未找到

**错误信息**:
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**:
```bash
# 激活虚拟环境
source .venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

---

### 8. 服务无法启动（systemd）

**检查服务状态**:
```bash
sudo systemctl status btc-arbitrage-bot.service
```

**查看日志**:
```bash
sudo journalctl -u btc-arbitrage-bot.service -n 50
sudo tail -f /var/log/btc-arbitrage-bot.log
```

**常见问题**:
- 路径不正确：检查systemd服务文件中的路径
- 权限问题：确保服务用户有权限访问项目目录
- 虚拟环境路径：确保使用正确的Python解释器路径

---

## 更新代码流程

如果遇到代码相关的问题，按以下步骤更新：

```bash
# 1. 进入项目目录
cd ~/btc-polymarket-bot

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 拉取最新代码
git pull origin main

# 4. 如果有冲突，解决冲突
git status

# 5. 更新依赖（如果需要）
pip install -r requirements.txt

# 6. 重启服务（如果使用systemd）
sudo systemctl restart btc-arbitrage-bot.service

# 7. 验证
python -m src.test_balance
```

---

## 获取帮助

如果以上方法都无法解决问题：

1. **查看详细错误信息**:
   ```bash
   python -m src.test_balance 2>&1 | tee error.log
   ```

2. **检查py-clob-client版本**:
   ```bash
   pip show py-clob-client
   ```

3. **查看项目文档**:
   - [README.md](../README.md)
   - [INSTALL.md](INSTALL.md)
   - [API_KEY_GUIDE.md](API_KEY_GUIDE.md)

4. **检查GitHub Issues**: 查看是否有类似问题

---

## 快速修复命令

```bash
# 一键更新和重启
cd ~/btc-polymarket-bot && \
source .venv/bin/activate && \
git pull origin main && \
pip install -r requirements.txt && \
sudo systemctl restart btc-arbitrage-bot.service && \
python -m src.test_balance
```
