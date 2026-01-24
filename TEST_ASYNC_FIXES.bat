@echo off
echo ========================================
echo 测试异步优化修复
echo ========================================
echo.

echo [1/3] Python 语法检查...
python -m py_compile backend/modules/sns/ai_social_engine_adapter.py
if errorlevel 1 (
    echo [FAIL] ai_social_engine_adapter.py 语法检查失败
    pause
    exit /b 1
)
echo [PASS] ai_social_engine_adapter.py 语法检查通过

python -m py_compile backend/modules/sns/service_async.py
if errorlevel 1 (
    echo [FAIL] service_async.py 语法检查失败
    pause
    exit /b 1
)
echo [PASS] service_async.py 语法检查通过

python -m py_compile backend/modules/sns/router.py
if errorlevel 1 (
    echo [FAIL] router.py 语法检查失败
    pause
    exit /b 1
)
echo [PASS] router.py 语法检查通过

python -m py_compile backend/config/database.py
if errorlevel 1 (
    echo [FAIL] database.py 语法检查失败
    pause
    exit /b 1
)
echo [PASS] database.py 语法检查通过

echo.
echo [2/3] 测试服务器启动...
echo 启动中...
start /B python api_server.py
if errorlevel 1 (
    echo [FAIL] 服务器启动失败
    pause
    exit /b 1
)
echo [PASS] 服务器启动成功

echo.
echo [3/3] 测试 API 端点...
echo 注意：请确保服务器正在运行在 http://localhost:8788
echo.
echo 测试完成后按任意键关闭测试窗口...
pause
