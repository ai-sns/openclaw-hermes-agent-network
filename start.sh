#!/bin/bash

# AI-SNS Electron 启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  AI-SNS - AI Agent Social Network"
echo "  Electron Version"
echo "=========================================="

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未找到Node.js，请先安装Node.js"
    exit 1
fi

# 检查npm
if ! command -v npm &> /dev/null; then
    echo "错误: 未找到npm，请先安装npm"
    exit 1
fi

# 检查Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "错误: 未找到Python，请先安装Python"
    exit 1
fi

# 设置Python命令
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo ""
echo "正在检查依赖..."

# 检查是否安装了npm依赖
if [ ! -d "node_modules" ]; then
    echo "正在安装Node.js依赖..."
    npm install
fi

# 检查是否安装了Python依赖
echo "正在检查Python依赖..."
$PYTHON_CMD -c "import fastapi" 2>/dev/null || {
    echo "正在安装FastAPI..."
    pip install fastapi uvicorn
}

echo ""
echo "启动应用..."
echo ""

# 启动方式选择
if [ "$1" == "--dev" ]; then
    echo "开发模式启动..."
    npm run dev
elif [ "$1" == "--api-only" ]; then
    echo "仅启动API服务器..."
    $PYTHON_CMD api_server.py
elif [ "$1" == "--electron-only" ]; then
    echo "仅启动Electron (需要API服务器已运行)..."
    npm run start:electron
else
    echo "生产模式启动..."
    npm start
fi
