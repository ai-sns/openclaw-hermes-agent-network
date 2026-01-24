#!/bin/bash

echo "=========================================="
echo "AI SNS 异步优化依赖安装脚本"
echo "=========================================="
echo ""

# 检查 Python 环境
if ! command -v python3 &> /dev/null
then
    echo "❌ 错误: Python3 未安装"
    exit 1
fi

echo "✅ Python3 已安装"

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "🔧 激活虚拟环境..."
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️  警告: 虚拟环境不存在，使用全局 Python"
fi

echo ""
echo "📦 安装异步依赖..."
echo "----------------------------------------"

# 安装异步依赖
pip install --upgrade pip
pip install --upgrade setuptools

echo "安装 sqlalchemy[asyncio]..."
pip install "sqlalchemy[asyncio]>=2.0.0"

echo "安装 aiosqlite..."
pip install "aiosqlite>=0.19.0"

echo "安装 httpx..."
pip install "httpx>=0.25.0"

echo "----------------------------------------"
echo "✅ 异步依赖安装完成"
echo ""

echo "🔍 验证安装..."
python3 -c "
import sys
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    print('✅ SQLAlchemy Async: OK')
except ImportError as e:
    print(f'❌ SQLAlchemy Async: {e}')
    sys.exit(1)

try:
    import aiosqlite
    print('✅ aiosqlite: OK')
except ImportError as e:
    print(f'❌ aiosqlite: {e}')
    sys.exit(1)

try:
    import httpx
    print('✅ httpx: OK')
except ImportError as e:
    print(f'❌ httpx: {e}')
    sys.exit(1)

print('')
print('🎉 所有依赖安装成功！')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "📝 下一步操作："
    echo "=========================================="
    echo ""
    echo "1. 应用 ai_social_engine_adapter.py 补丁："
    echo "   参考 ASYNC_PATCH_INSTRUCTIONS.md"
    echo ""
    echo "2. 启动 API 服务器："
    echo "   python api_server.py"
    echo ""
    echo "3. 测试异步端点："
    echo "   GET  http://localhost:8000/api/sns/user-stats"
    echo "   POST http://localhost:8000/api/sns/start-engine"
    echo ""
    echo "4. 查看详细文档："
    echo "   cat ASYNC_MODIFICATION_COMPLETE.md"
    echo ""
else
    echo ""
    echo "❌ 依赖验证失败，请检查错误信息"
    exit 1
fi
