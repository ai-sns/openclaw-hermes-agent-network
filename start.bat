@echo off
chcp 65001 >nul
title AI-SNS - AI Agent Social Network

echo ==========================================
echo   AI-SNS - AI Agent Social Network
echo   Electron Version
echo ==========================================
echo.

cd /d "%~dp0"

:: 检查Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Node.js，请先安装Node.js
    pause
    exit /b 1
)

:: 检查npm
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到npm，请先安装npm
    pause
    exit /b 1
)

:: 检查Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

echo 正在检查依赖...

:: 检查是否安装了npm依赖
if not exist "node_modules" (
    echo 正在安装Node.js依赖...
    call npm install
)

echo.
echo 启动应用...
echo.

if "%1"=="--dev" (
    echo 开发模式启动...
    call npm run dev
) else if "%1"=="--api-only" (
    echo 仅启动API服务器...
    python api_server.py
) else if "%1"=="--electron-only" (
    echo 仅启动Electron (需要API服务器已运行)...
    call npm run start:electron
) else (
    echo 生产模式启动...
    call npm start
)

pause
