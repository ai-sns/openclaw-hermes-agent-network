# -*- coding: utf-8 -*-
"""
AI-SNS API Server
使用模块化后端架构，提供 REST API、WebSocket 和 JSON-RPC 接口
支持 Agent 管理、AI 聊天、地图功能、知识管理等模块
"""

import os
import sys
from pathlib import Path

# 设置工作目录
app_directory = Path(__file__).resolve().parent
os.chdir(app_directory)

# 将 backend 目录添加到 sys.path
sys.path.insert(0, str(app_directory / 'backend'))

import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 导入配置
from backend.config.settings import get_settings
from backend.config.database import init_db

# 导入 WebSocket 管理器 - 使用全局管理器
from backend.shared.websocket_manager import ConnectionManager, manager as ws_manager

# 配置日志（必须在使用 logger 之前）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入所有模块路由（使用 try-except 优雅处理依赖问题）
# Tools module (必须加载)
from backend.modules.tools.router import router as tools_router

# 其他模块（可选加载）
agent_router = None
llm_router = None
role_router = None
agent_chat_router = None
chat_router = None
map_router = None
km_router = None
system_router = None
plugins_router = None
wallet_router = None
sns_router = None

try:
    from backend.modules.agent.router import router as agent_router
    from backend.modules.agent.llm_router import router as llm_router
    from backend.modules.agent.role_router import router as role_router
    from backend.modules.agent.chat_router import router as agent_chat_router
except Exception as e:
    logger.warning(f"⚠ Agent modules not available: {e}")

try:
    from backend.modules.chat.router import router as chat_router
except Exception as e:
    logger.warning(f"⚠ Chat module not available: {e}")

try:
    from backend.modules.map.router import router as map_router
except Exception as e:
    logger.warning(f"⚠ Map module not available: {e}")

try:
    from backend.modules.km.router import router as km_router
except Exception as e:
    logger.warning(f"⚠ KM module not available: {e}")

try:
    from backend.modules.system.router import router as system_router
except Exception as e:
    logger.warning(f"⚠ System module not available: {e}")

try:
    from backend.modules.plugins.router import router as plugins_router
except Exception as e:
    logger.warning(f"⚠ Plugins module not available: {e}")

try:
    from backend.modules.wallet.router import router as wallet_router
except Exception as e:
    logger.warning(f"⚠ Wallet module not available: {e}")

try:
    from backend.modules.sns.router import router as sns_router
except Exception as e:
    logger.warning(f"⚠ SNS module not available: {e}")

# 获取配置
settings = get_settings()

# 不再创建新的 WebSocket 管理器，而是使用从模块导入的全局管理器

# 创建FastAPI应用
app = FastAPI(
    title="AI-SNS API",
    description="AI Agent Social Network API Server - Modular Architecture with REST, WebSocket, and JSON-RPC support",
    version="2.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
try:
    if os.path.exists("images"):
        app.mount("/images", StaticFiles(directory="images"), name="images")
    if os.path.exists("resource"):
        app.mount("/resource", StaticFiles(directory="resource"), name="resource")
    if os.path.exists("scripts"):
        app.mount("/scripts", StaticFiles(directory="scripts"), name="scripts")

    # Create uploads directory if not exists
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    logger.info("✓ Uploads directory mounted")
except Exception as e:
    logger.warning(f"Failed to mount static files: {e}")

# 注册所有模块路由
# IMPORTANT: Register more specific routes BEFORE general routes to avoid path conflicts

# 优先注册 Tools 模块（必须可用）
app.include_router(tools_router, prefix="/api/tools", tags=["Tools"])
logger.info("✓ Tools Module registered")

# 注册其他模块（如果可用）
if llm_router:
    app.include_router(llm_router, prefix="/api/agent", tags=["Agent-LLM"])
    logger.info("✓ Agent LLM Module registered")

if role_router:
    app.include_router(role_router, prefix="/api/agent", tags=["Agent-Role"])
    logger.info("✓ Agent Role Module registered")

if agent_chat_router:
    app.include_router(agent_chat_router, prefix="/api/agent", tags=["Agent-Chat"])
    logger.info("✓ Agent Chat Module registered")

if agent_router:
    app.include_router(agent_router, prefix="/api/agent", tags=["Agent"])
    logger.info("✓ Agent Module registered")

if chat_router:
    app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
    logger.info("✓ Chat Module registered")

if map_router:
    app.include_router(map_router, prefix="/api/map", tags=["Map"])
    logger.info("✓ Map Module registered")

if km_router:
    app.include_router(km_router, prefix="/api/km", tags=["Knowledge Base"])
    logger.info("✓ KM Module registered")

if system_router:
    app.include_router(system_router, prefix="/api/system", tags=["System"])
    logger.info("✓ System Module registered")

if plugins_router:
    app.include_router(plugins_router, prefix="/api/plugins", tags=["Plugins"])
    logger.info("✓ Plugins Module registered")

if wallet_router:
    app.include_router(wallet_router, prefix="/api/wallet", tags=["Blockchain Wallet"])
    logger.info("✓ Wallet Module registered")

if sns_router:
    app.include_router(sns_router, prefix="/api/sns", tags=["SNS"])
    logger.info("✓ SNS Module registered")

# 健康检查端点（保持向后兼容）
@app.get("/health")
async def health_check_compat():
    """健康检查（兼容旧版）"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "architecture": "modular"
    }

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "architecture": "modular"
    }

# WebSocket 端点 - 通用端点（自动生成client_id）
@app.websocket("/ws")
async def websocket_general_endpoint(websocket: WebSocket):
    """
    通用 WebSocket 连接端点（自动生成client_id）
    """
    import uuid
    client_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, client_id)
    logger.info(f"WebSocket client {client_id} connected (auto-generated)")

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            logger.info(f"Received from {client_id}: {data}")

            # 处理消息类型
            msg_type = data.get('type', '')

            if msg_type == 'ping':
                # 响应 ping
                await ws_manager.send_message({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }, client_id)

    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        ws_manager.disconnect(client_id)

# WebSocket 端点
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket 连接端点

    Args:
        websocket: WebSocket 连接
        client_id: 客户端ID
    """
    await ws_manager.connect(websocket, client_id)
    logger.info(f"WebSocket client {client_id} connected")

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            logger.info(f"Received from {client_id}: {data}")

            # 处理消息类型
            msg_type = data.get('type', '')

            if msg_type == 'ping':
                # 响应 ping
                await ws_manager.send_message({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }, client_id)

            elif msg_type == 'broadcast':
                # 广播消息
                await ws_manager.broadcast({
                    'type': 'message',
                    'from': client_id,
                    'content': data.get('content', '')
                })

            elif msg_type == 'map_chat':
                # 地图聊天消息
                await ws_manager.broadcast({
                    'type': 'map_chat_message',
                    'from_user': data.get('from_user', client_id),
                    'to_user': data.get('to_user', ''),
                    'content': data.get('content', ''),
                    'timestamp': data.get('timestamp', '')
                })

            else:
                # 回显未知消息
                await ws_manager.send_message({
                    'type': 'echo',
                    'data': data
                }, client_id)

    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        ws_manager.disconnect(client_id)

# JSON-RPC 2.0 端点（向后兼容）
@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: Request):
    """
    JSON-RPC 2.0 接口（兼容旧版前端）

    将 JSON-RPC 请求路由到对应的 REST API 端点
    """
    try:
        body = await request.json()

        # 验证 JSON-RPC 版本
        if body.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "JSON-RPC version must be 2.0"
                },
                "id": body.get("id")
            }

        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        # 导入需要的模块服务（懒加载）
        from backend.modules.map.dependencies import get_map_service

        # 创建服务实例（MapService使用静态方法，不需要db参数）
        map_service = get_map_service()

        # 路由到对应的方法
        if method == "get_map_settings":
            result = map_service.get_map_settings()
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "update_map_settings":
            result = map_service.update_map_settings(**params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "get_home_position":
            result = map_service.get_home_position()
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "update_home_position":
            result = map_service.update_home_position(**params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "plan_route":
            result = map_service.plan_route(**params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "control_route":
            route_id = params.get("route_id")
            control_params = params.get("control", params)
            result = map_service.control_route(route_id, control_params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "get_map_markers":
            result = map_service.get_map_markers()
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "add_map_marker":
            result = map_service.add_map_marker(**params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "update_map_marker":
            marker_id = params.get("marker_id")
            marker_data = params.get("marker", params)
            result = map_service.update_map_marker(marker_id, marker_data)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "delete_map_marker":
            marker_id = params.get("marker_id")
            result = map_service.delete_map_marker(marker_id)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "send_map_chat_message":
            # 广播聊天消息通过 WebSocket
            await ws_manager.broadcast({
                "type": "map_chat_message",
                "from_user": params.get("from_user", ""),
                "to_user": params.get("to_user", ""),
                "content": params.get("content", ""),
                "timestamp": params.get("timestamp", "")
            })
            return {
                "jsonrpc": "2.0",
                "result": {"success": True},
                "id": request_id
            }

        elif method == "get_map_chat_history":
            # TODO: 实现聊天历史查询
            result = map_service.get_map_chat_history()
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": f"Method '{method}' not supported"
                },
                "id": request_id
            }

    except Exception as e:
        logger.error(f"JSON-RPC error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": "Server error",
                "data": str(e)
            },
            "id": body.get("id") if 'body' in locals() else None
        }

# 根端点
@app.get("/")
async def root():
    """根端点 - 返回 API 信息"""
    return {
        "message": "AI-SNS API Server",
        "name": "AI-SNS API",
        "version": "2.0.0",
        "status": "running",
        "architecture": "modular",
        "docs": "/docs",
        "modules": {
            "agent": "Agent management module",
            "chat": "AI chat and streaming module",
            "map": "Location-based features module (with WebSocket)",
            "km": "Knowledge management module",
            "system": "System configuration module",
            "plugins": "Plugin management module",
            "tools": "Tools management module (Plugins, MCP, Functions, Skills)",
            "wallet": "Blockchain wallet module"
        },
        "endpoints": {
            "health": "GET /health - Health check endpoint",
            "agents": "GET /api/agent/list - List all agents",
            "llm": "GET /api/agent/llm - LLM management",
            "roles": "GET /api/agent/roles - Role management",
            "chat": "POST /api/chat - Chat with AI",
            "stream_chat": "POST /api/chat/stream - Streaming chat with AI (SSE)",
            "map_settings": "GET /api/map/settings - Map settings",
            "knowledge_base": "GET /api/km - Knowledge management",
            "system_config": "GET /api/system/config - System configuration",
            "plugins": "GET /api/plugins - Plugin management",
            "tools": "GET /api/tools/plugins - Tools management (Plugins, MCP, Functions, Skills)",
            "websocket": "WS /ws/{client_id} - WebSocket connection",
            "jsonrpc": "POST /jsonrpc - JSON-RPC 2.0 interface (legacy compatibility)"
        },
        "documentation": {
            "openapi": "/openapi.json - OpenAPI specification",
            "swagger": "/docs - Swagger UI",
            "redoc": "/redoc - ReDoc UI"
        }
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("="*60)
    logger.info("AI-SNS API Server Starting...")
    logger.info(f"Version: 2.0.0")
    logger.info(f"Architecture: Modular")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Server: {settings.server.host}:{settings.server.port}")
    logger.info("="*60)

    # 初始化数据库
    try:
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")

    logger.info("✓ All modules loaded:")
    logger.info("  - Agent Module")
    logger.info("  - Agent LLM Module")
    logger.info("  - Agent Role Module")
    logger.info("  - Chat Module (with SSE streaming)")
    logger.info("  - Map Module (with WebSocket)")
    logger.info("  - Knowledge Base Module")
    logger.info("  - System Module")
    logger.info("  - Plugins Module")
    logger.info("  - Tools Module")
    logger.info("  - Wallet Module")
    logger.info("  - SNS Module")
    logger.info("="*60)

    # Start XMPP client
    if sns_router:
        try:
            from backend.modules.sns.xmpp_client import XMPPClientManager
            xmpp_manager = XMPPClientManager.get_instance()
            await xmpp_manager.start()
            logger.info("✓ XMPP Client started")
        except Exception as e:
            logger.warning(f"⚠ Failed to start XMPP client: {e}")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("AI-SNS API Server shutting down...")

    # Stop XMPP client
    if sns_router:
        try:
            from backend.modules.sns.xmpp_client import XMPPClientManager
            xmpp_manager = XMPPClientManager.get_instance()
            await xmpp_manager.stop()
            logger.info("✓ XMPP Client stopped")
        except Exception as e:
            logger.warning(f"⚠ Failed to stop XMPP client: {e}")

# 主函数
def main():
    """启动服务器"""
    try:
        uvicorn.run(
            "api_server:app",
            host=settings.server.host,
            port=settings.server.port,
            reload=settings.server.reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
