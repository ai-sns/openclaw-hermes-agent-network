@echo off
chcp 65001 >nul
echo ==========================================
echo AI SNS 异步优化依赖安装脚本
echo ==========================================
echo.

REM 检查 Python 环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: Python 未安装
    pause
    exit /b 1
)
echo ✅ Python 已安装
echo.

REM 激活虚拟环境（如果存在）
if exist venv\Scripts\activate.bat (
    echo 🔧 激活虚拟环境...
    call venv\Scripts\activate.bat
    echo ✅ 虚拟环境已激活
) else (
    echo ⚠️  警告: 虚拟环境不存在，使用全局 Python
)

echo.
echo 📦 安装异步依赖...
echo ----------------------------------------
echo.

REM 升级 pip
echo 升级 pip...
python -m pip install --upgrade pip
echo.

REM 安装异步依赖
echo 安装 sqlalchemy[asyncio]...
python -m pip install "sqlalchemy[asyncio]>=2.0.0"
echo.

echo 安装 aiosqlite...
python -m pip install "aiosqlite>=0.19.0"
echo.

echo 安装 httpx...
python -m pip install "httpx>=0.25.0"
echo.

echo ----------------------------------------
echo ✅ 异步依赖安装完成
echo.

echo 🔍 验证安装...
echo.
python -c "import sys; sys.path.insert(0, '.'); from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession; print('✅ SQLAlchemy Async: OK')"
if %errorlevel% neq 0 (
    echo ❌ SQLAlchemy Async: 导入失败
    pause
    exit /b 1
)

python -c "import sys; sys.path.insert(0, '.'); import aiosqlite; print('✅ aiosqlite: OK')"
if %errorlevel% neq 0 (
    echo ❌ aiosqlite: 导入失败
    pause
    exit /b 1
)

python -c "import sys; sys.path.insert(0, '.'); import httpx; print('✅ httpx: OK')"
if %errorlevel% neq 0 (
    echo ❌ httpx: 导入失败
    pause
    exit /b 1
)

echo.
echo 🎉 所有依赖安装成功！
echo.

echo ==========================================
echo 📝 下一步操作：
echo ==========================================
echo.
echo 1. 应用 ai_social_engine_adapter.py 补丁：
echo    参考 ASYNC_PATCH_INSTRUCTIONS.md
echo.
echo 2. 启动 API 服务器：
echo    python api_server.py
echo.
echo 3. 测试异步端点：
echo    GET  http://localhost:8000/api/sns/user-stats
echo    POST http://localhost:8000/api/sns/start-engine
echo.
echo 4. 查看详细文档：
echo    type ASYNC_MODIFICATION_COMPLETE.md
echo.

pause
