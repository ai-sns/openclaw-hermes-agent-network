# -*- coding: utf-8 -*-
"""
AI-SNS API Server - Modular Version
将PyQt5应用的后端功能暴露为REST API和WebSocket服务
重构为模块化架构
"""

import os
import sys
from pathlib import Path

# 设置工作目录
app_directory = Path(__file__).resolve().parent
os.chdir(app_directory)

import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# 导入所有模块的路由
from backend.modules.agent.router import router as agent_router
from backend.modules.agent.llm_router import router as llm_router
from backend.modules.agent.role_router import router as role_router
from backend.modules.chat.router import router as chat_router
from backend.modules.map.router import router as map_router
from backend.modules.km.router import router as km_router
from backend.modules.system.router import router as system_router
from backend.modules.plugins.router import router as plugins_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="AI-SNS API",
    description="AI Agent Social Network API Server - Modular Architecture",
    version="2.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/resource", StaticFiles(directory="resource"), name="resource")
app.mount("/scripts", StaticFiles(directory="scripts"), name="scripts")

# 注册所有模块路由
app.include_router(agent_router)
app.include_router(llm_router)
app.include_router(role_router)
app.include_router(chat_router)
app.include_router(map_router)
app.include_router(km_router)
app.include_router(system_router)
app.include_router(plugins_router)

# ==================== 根路由 ====================

@app.get("/")
async def root():
    """API 根路由"""
    return {
        "message": "AI-SNS API Server - Modular Version",
        "version": "2.0.0",
        "status": "running",
        "architecture": "modular",
        "modules": {
            "agent": "Agent management module",
            "chat": "AI chat and streaming module",
            "map": "Location-based features module",
            "km": "Knowledge management module",
            "system": "System configuration module",
            "plugins": "Plugin management module"
        },
        "endpoints": {
            "health": "GET /health",
            "agents": "GET /api/agents",
            "chat": "POST /api/chat",
            "stream_chat": "POST /api/chat/stream",
            "map_settings": "GET /api/map/settings",
            "knowledge_base": "GET /api/knowledge-base",
            "system_config": "GET /api/system/config",
            "plugins": "GET /api/plugins",
            "docs": "GET /docs (FastAPI auto-generated documentation)"
        },
        "documentation": {
            "openapi": "GET /openapi.json",
            "redoc": "GET /redoc",
            "swagger": "GET /docs"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "modules": [
            "agent",
            "chat",
            "map",
            "km",
            "system",
            "plugins"
        ]
    }


# ==================== 启动服务器 ====================

def start_server(host: str = "0.0.0.0", port: int = 8788, reload: bool = True):
    """启动API服务器"""
    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI-SNS API Server - Modular Version")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8788, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")

    args = parser.parse_args()

    logger.info(f"Starting AI-SNS Modular API Server on {args.host}:{args.port}")
    logger.info("Modules loaded: agent, chat, map, km, system, plugins")
    start_server(args.host, args.port, reload=args.reload)
