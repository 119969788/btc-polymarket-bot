#!/bin/bash
# BTC套利机器人自动安装脚本
# 适用于 Ubuntu/Debian 系统

set -e

echo "=========================================="
echo "BTC 15分钟套利机器人 - 自动安装脚本"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then 
   echo "❌ 请不要使用root用户运行此脚本"
   echo "   请使用普通用户，脚本会在需要时请求sudo权限"
   exit 1
fi

# 检查Python版本
echo "📋 检查系统环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，正在安装..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv git
else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    echo "✅ Python版本: $(python3 --version)"
fi

# 检查git
if ! command -v git &> /dev/null; then
    echo "❌ 未找到git，正在安装..."
    sudo apt install -y git
else
    echo "✅ Git已安装"
fi

# 获取项目目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo ""
echo "📁 项目目录: $PROJECT_DIR"
echo ""

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "🐍 创建Python虚拟环境..."
    python3 -m venv .venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境并安装依赖..."
source .venv/bin/activate

# 升级pip
pip install --upgrade pip --quiet

# 安装依赖
echo "📦 安装Python依赖包..."
pip install -r requirements.txt

echo ""
echo "✅ 依赖安装完成"
echo ""

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "📝 创建.env配置文件..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已从.env.example创建.env文件"
        echo ""
        echo "⚠️  重要: 请编辑.env文件并填写以下信息:"
        echo "   - POLYMARKET_PRIVATE_KEY"
        echo "   - POLYMARKET_API_KEY (运行 python -m src.generate_api_key 生成)"
        echo "   - POLYMARKET_API_SECRET"
        echo "   - POLYMARKET_API_PASSPHRASE"
        echo ""
        echo "   编辑命令: nano .env"
    else
        echo "⚠️  未找到.env.example文件"
    fi
else
    echo "✅ .env文件已存在"
fi

# 设置.env文件权限
if [ -f ".env" ]; then
    chmod 600 .env
    echo "✅ 已设置.env文件权限为600"
fi

echo ""
echo "=========================================="
echo "✅ 安装完成！"
echo "=========================================="
echo ""
echo "下一步操作:"
echo ""
echo "1. 配置环境变量:"
echo "   nano .env"
echo ""
echo "2. 生成API密钥:"
echo "   source .venv/bin/activate"
echo "   python -m src.generate_api_key"
echo ""
echo "3. 测试余额:"
echo "   python -m src.test_balance"
echo ""
echo "4. 运行机器人（模拟模式）:"
echo "   python -m src.arbitrage_bot"
echo ""
echo "5. 配置后台运行（参考INSTALL.md）:"
echo "   - 使用systemd服务"
echo "   - 或使用screen/tmux"
echo ""
echo "详细文档: 查看 INSTALL.md"
echo "=========================================="
