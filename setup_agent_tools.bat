@echo off
chcp 65001 >nul
echo ========================================
echo Agent工具配置脚本
echo ========================================
echo.

echo 正在检查 api_server.py 是否运行...
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [警告] 检测到 Python 进程正在运行！
    echo 请先停止 api_server.py，然后再运行此脚本。
    echo.
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

echo.
echo 正在配置 Agent 工具关联...
echo.

sqlite3.exe db\db.sqlite < add_agent_tools.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✓ 配置成功！
    echo ========================================
    echo.
    echo 已为 Agent 1 配置以下工具：
    echo   • 高德地图 MCP (查询位置、路线)
    echo   • DuckDuckGo 搜索 MCP (搜索信息)
    echo.
    echo 下一步：
    echo   1. 启动 api_server.py
    echo   2. 在聊天界面测试：
    echo      - "查询北京到上海的路线"
    echo      - "搜索2024年的新闻"
    echo.
) else (
    echo.
    echo ========================================
    echo ✗ 配置失败
    echo ========================================
    echo.
    echo 可能的原因：
    echo   1. sqlite3.exe 不在 PATH 中
    echo   2. 数据库文件不存在或被锁定
    echo   3. SQL 语法错误
    echo.
    echo 请检查错误信息后重试。
    echo.
)

echo.
echo 按任意键退出...
pause >nul
