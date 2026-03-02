# -*- coding: utf-8 -*-
"""
AI-SNS API Server
Uses a modular backend architecture that provides REST API, WebSocket, and JSON-RPC interfaces.
Supports agent management, AI chat, map features, knowledge management, and other modules.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

if os.environ.get("PYCHARM_HOSTED"):
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"



# Set working directory
app_directory = Path(__file__).resolve().parent
os.chdir(app_directory)

# Add the backend directory to sys.path
sys.path.insert(0, str(app_directory / 'backend'))

import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse

# Import configuration
from backend.config.settings import get_settings
from backend.config.database import init_db

# Import the WebSocket manager - use the global manager
from backend.shared.websocket_manager import ConnectionManager, manager as ws_manager

# Configure logging (must run before the logger is used)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all module routers (use try-except to gracefully handle dependency issues)
# Tools module (must be loaded)
from backend.modules.tools.router import router as tools_router

# DocSkill module (OpenClaw-style skills)
from backend.modules.skills_registry.router import router as skills_registry_router

# Other modules (optional)
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

# Temporary debug: check how many times the KM module is imported
import os
logger.info(f"⚠️ Attempting to import KM module (PID: {os.getpid()}, Path: {os.getcwd()})")
try:
    from backend.modules.km.router import router as km_router
    logger.info(f"✅ KM module imported successfully (PID: {os.getpid()})")
except Exception as e:
    logger.warning(f"⚠ KM module not available: {e}")
    import traceback
    logger.error(traceback.format_exc())

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
    from backend.apps.sns.router import router as sns_router
except Exception as e:
    logger.warning(f"⚠ SNS module not available: {e}")

# Load configuration
settings = get_settings()

# Do not create a new WebSocket manager; reuse the global manager imported from the module

# Create FastAPI application
app = FastAPI(
    title="AI-SNS API",
    description="AI Agent Social Network API Server - Modular Architecture with REST, WebSocket, and JSON-RPC support",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
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

# Register all module routes
# IMPORTANT: Register more specific routes BEFORE general routes to avoid path conflicts

# Register the Tools module first (must be available)
app.include_router(tools_router, prefix="/api/tools", tags=["Tools"])
logger.info("✓ Tools Module registered")

# Register the DocSkills module
app.include_router(skills_registry_router, prefix="/api/skills", tags=["Skills"])
logger.info("✓ Skills Registry Module registered")

# Register other modules when available
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

# Health check endpoint (maintain backward compatibility)
@app.get("/health")
async def health_check_compat():
    """Health check (legacy compatible)"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "architecture": "modular"
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "architecture": "modular"
    }


def _get_remote_ai_sns_server_base() -> str:
    try:
        from db.DBFactory import query_SystemCfg
        cfg = query_SystemCfg(is_delete=False)
        v = getattr(cfg, 'ai_sns_server', None)
        v = (v or '').strip()
        return v.rstrip('/') if v else ''
    except Exception:
        return ''


def _get_current_position_from_db():
    try:
        from db.DBFactory import query_AiChatCfg_map_setting
        import json

        setting = query_AiChatCfg_map_setting() or {}
        raw_pos = setting.get("current_position")
        if not raw_pos:
            return (None, None)

        if isinstance(raw_pos, list) and len(raw_pos) >= 2:
            return (float(raw_pos[0]), float(raw_pos[1]))

        if isinstance(raw_pos, str):
            parsed = json.loads(raw_pos)
            if isinstance(parsed, dict):
                lng = parsed.get("lng")
                lat = parsed.get("lat")
                return (float(lng), float(lat)) if lng is not None and lat is not None else (None, None)
            if isinstance(parsed, list) and len(parsed) >= 2:
                return (float(parsed[0]), float(parsed[1]))

        return (None, None)
    except Exception:
        return (None, None)


def _get_current_nation_id_from_db() -> str:
    try:
        from db.DBFactory import query_AiChatCfg_map_setting

        setting = query_AiChatCfg_map_setting() or {}
        nation_id = (setting.get("nationid") or setting.get("nation_id") or "").strip()
        return nation_id
    except Exception:
        return ""


def _normalize_and_filter_people_list(data, exclude_nation_id: str):
    if not isinstance(data, list):
        return data

    exclude_nation_id = (exclude_nation_id or "").strip()
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue

        nation_id = (item.get("nation_id") or item.get("nationid") or "").strip()
        if exclude_nation_id and nation_id == exclude_nation_id:
            continue

        if nation_id:
            if not (item.get("nation_id") or "").strip():
                item["nation_id"] = nation_id
            if not (item.get("nationid") or "").strip():
                item["nationid"] = nation_id

        result.append(item)
    return result


@app.get("/api/get_news_list/")
async def get_news_list():
    remote_base = _get_remote_ai_sns_server_base()
    if remote_base:
        try:
            import httpx
            url = f"{remote_base}/news.json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return JSONResponse(content=resp.json())
        except Exception as e:
            logger.warning(f"Failed to fetch news list from remote server: {e}")

    return JSONResponse(
        content={
            "top": [],
            "hot": [],
            "latest": [],
            "recommended": []
        }
    )


@app.get("/api/get_people_list/")
async def get_people_list(lng: float = None, lat: float = None):
    remote_base = _get_remote_ai_sns_server_base()
    exclude_nation_id = _get_current_nation_id_from_db()
    if remote_base:
        try:
            import httpx

            if lng is None or lat is None:
                db_lng, db_lat = _get_current_position_from_db()
                lng = db_lng if lng is None else lng
                lat = db_lat if lat is None else lat

            params = {}
            if lng is not None and lat is not None:
                params = {"lng": lng, "lat": lat}

            url = f"{remote_base}/api/get_people_list/"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, data=params)
                resp.raise_for_status()
                return JSONResponse(content=_normalize_and_filter_people_list(resp.json(), exclude_nation_id))
        except Exception as e:
            logger.warning(f"Failed to fetch people list from remote server: {e}")

    try:
        import json
        local_path = Path("scripts") / "personsdata.json"
        if not local_path.exists():
            raise FileNotFoundError(str(local_path))
        data = json.loads(local_path.read_text(encoding="utf-8"))
        return JSONResponse(content=_normalize_and_filter_people_list(data, exclude_nation_id))
    except Exception as e:
        logger.error(f"Failed to load local personsdata.json: {e}")
        raise HTTPException(status_code=500, detail="Failed to provide people list")


@app.get("/personsdata.json")
async def get_personsdata_json():
    remote_base = _get_remote_ai_sns_server_base()
    if remote_base:
        try:
            import httpx
            url = f"{remote_base}/personsdata.json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return JSONResponse(content=resp.json())
        except Exception as e:
            logger.warning(f"Failed to fetch personsdata.json from remote server: {e}")

    try:
        import json
        local_path = Path("scripts") / "personsdata.json"
        if not local_path.exists():
            raise FileNotFoundError(str(local_path))
        return JSONResponse(content=json.loads(local_path.read_text(encoding="utf-8")))
    except Exception as e:
        logger.error(f"Failed to load local personsdata.json: {e}")
        raise HTTPException(status_code=500, detail="Failed to provide persons data")


@app.get("/news.json")
async def get_news_json():
    remote_base = _get_remote_ai_sns_server_base()
    if remote_base:
        try:
            import httpx
            url = f"{remote_base}/news.json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return JSONResponse(content=resp.json())
        except Exception as e:
            logger.warning(f"Failed to fetch news.json from remote server: {e}")

    return JSONResponse(
        content={
            "top": [],
            "hot": [],
            "latest": [],
            "recommended": []
        }
    )


@app.get("/aigccenter.html")
async def aigc_center_redirect():
    remote_base = _get_remote_ai_sns_server_base()
    if not remote_base:
        raise HTTPException(status_code=404, detail="AIGC center is not configured")
    return RedirectResponse(url=f"{remote_base}/aigccenter.html")

# WebSocket endpoint - general endpoint (auto-generates client_id)
@app.websocket("/ws")
async def websocket_general_endpoint(websocket: WebSocket):
    """
    General WebSocket connection endpoint (auto-generates client_id)
    """
    import uuid
    client_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, client_id)
    logger.info(f"WebSocket client {client_id} connected (auto-generated)")

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            logger.info(f"Received from {client_id}: {data}")

            # Handle message type
            msg_type = data.get('type', '')

            if msg_type == 'ping':
                # Respond to ping
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

# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket connection endpoint

    Args:
        websocket: WebSocket connection
        client_id: Client ID
    """
    await ws_manager.connect(websocket, client_id)
    logger.info(f"WebSocket client {client_id} connected")

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            logger.info(f"Received from {client_id}: {data}")

            # Handle message type
            msg_type = data.get('type', '')

            if msg_type == 'ping':
                # Respond to ping
                await ws_manager.send_message({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }, client_id)

            elif msg_type == 'broadcast':
                # Broadcast message
                await ws_manager.broadcast({
                    'type': 'message',
                    'from': client_id,
                    'content': data.get('content', '')
                })

            elif msg_type == 'map_chat':
                # Map chat message
                await ws_manager.broadcast({
                    'type': 'map_chat_message',
                    'from_user': data.get('from_user', client_id),
                    'to_user': data.get('to_user', ''),
                    'content': data.get('content', ''),
                    'timestamp': data.get('timestamp', '')
                })

            else:
                # Echo unknown message
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

# JSON-RPC 2.0 endpoint (backward compatible)
@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: Request):
    """
    JSON-RPC 2.0 interface (compatible with the legacy frontend)

    Route JSON-RPC requests to the corresponding REST API endpoints
    """
    try:
        body = await request.json()

        # Validate the JSON-RPC version
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

        # Import required module services (lazy load)
        from backend.modules.map.dependencies import get_map_service

        # Create the service instance (MapService uses static methods, so no db parameter is required)
        map_service = get_map_service()

        # Route to the corresponding method
        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "ok": True,
                    "message": "pong",
                    "echo": params,
                    "server_time": datetime.utcnow().isoformat() + "Z"
                },
                "id": request_id
            }

        elif method == "get_map_settings":
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
            # Broadcast chat messages through WebSocket
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

        elif method == "update_location_and_get_nearest_place":
            lng = params.get("lng")
            lat = params.get("lat")
            max_distance_m = params.get("max_distance_m", 1000)
            result = map_service.update_location_and_get_nearest_place(
                lng=lng,
                lat=lat,
                max_distance_m=max_distance_m,
            )
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "get_map_chat_history":
            # TODO: Implement chat history lookup
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

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - returns API information"""
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

# Startup event
@app.on_event("startup")
async def startup_event():
    """Execute when the application starts"""
    logger.info("="*60)
    logger.info("AI-SNS API Server Starting...")
    logger.info(f"Version: 2.0.0")
    logger.info(f"Architecture: Modular")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Server: {settings.server.host}:{settings.server.port}")
    logger.info("="*60)

    # Initialize the database
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
            from backend.apps.sns.xmpp_client import XMPPClientManager
            xmpp_manager = XMPPClientManager.get_instance()
            await xmpp_manager.start()
            logger.info("✓ XMPP Client started")
        except Exception as e:
            logger.warning(f"⚠ Failed to start XMPP client: {e}")

    try:
        async def _stop_sns_engine_if_active():
            try:
                from backend.apps.sns.service_async import SNSService

                service = SNSService(db=None)
                status = await service.get_social_engine_status()
                task_status = str((status or {}).get("task_status") or "").lower()
                active = bool((status or {}).get("running")) or bool((status or {}).get("started"))
                if task_status in ("started", "paused"):
                    active = True

                if not active:
                    return

                logger.info("No WebSocket clients connected. Stopping SNS engine...")
                await service.stop_social_engine()
            except Exception as e:
                logger.warning(f"Failed to stop SNS engine on zero WebSocket clients: {e}")

        ws_manager.add_on_zero_clients_callback(_stop_sns_engine_if_active)
    except Exception as e:
        logger.warning(f"Failed to register zero-clients hook: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Execute when the application shuts down"""
    logger.info("AI-SNS API Server shutting down...")

    # Stop XMPP client
    if sns_router:
        try:
            from backend.apps.sns.xmpp_client import XMPPClientManager
            xmpp_manager = XMPPClientManager.get_instance()
            await xmpp_manager.stop()
            logger.info("✓ XMPP Client stopped")
        except Exception as e:
            logger.warning(f"⚠ Failed to stop XMPP client: {e}")

# Main function
def main():
    """Start the server"""
    reload = settings.server.reload and not os.environ.get("PYCHARM_HOSTED")
    try:
        uvicorn.run(
            app,
            host=settings.server.host,
            port=settings.server.port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
