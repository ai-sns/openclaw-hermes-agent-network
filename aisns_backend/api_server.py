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
from runtime.shared import debug_info

if os.environ.get("PYCHARM_HOSTED"):
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"



# Set working directory
app_directory = Path(__file__).resolve().parent
os.chdir(app_directory)

app_directory_parent = app_directory.parent


# Add the runtime directory to sys.path
sys.path.insert(0, str(app_directory / 'runtime'))

import logging
import copy
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse

# Import configuration
from runtime.config.settings import get_settings
from db.database import init_db

# Import the WebSocket manager - use the global manager
from runtime.shared.websocket_manager import ConnectionManager, manager as ws_manager
from runtime.i18n import lt
# Configure logging (must run before the logger is used)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _build_uvicorn_log_config() -> dict:
    """Build a uvicorn log config without ANSI colors and with time-only prefix."""
    cfg = copy.deepcopy(getattr(uvicorn.config, "LOGGING_CONFIG", {}))
    if not isinstance(cfg, dict):
        cfg = {}

    formatters = cfg.setdefault("formatters", {})
    formatters["default"] = {
        "()": "uvicorn.logging.DefaultFormatter",
        "fmt": "%(asctime)s %(levelname)s:%(name)s:%(message)s",
        "datefmt": "%H:%M:%S",
        "use_colors": False,
    }
    formatters["access"] = {
        "()": "uvicorn.logging.AccessFormatter",
        "fmt": "%(asctime)s %(levelname)s:%(client_addr)s - \"%(request_line)s\" %(status_code)s",
        "datefmt": "%H:%M:%S",
        "use_colors": False,
    }

    handlers = cfg.setdefault("handlers", {})
    if isinstance(handlers.get("default"), dict):
        handlers["default"]["formatter"] = "default"
    if isinstance(handlers.get("access"), dict):
        handlers["access"]["formatter"] = "access"

    return cfg

# Import all module routers (use try-except to gracefully handle dependency issues)
# Tools module (must be loaded)
from runtime.modules.tools.router import router as tools_router

# DocSkill module (OpenClaw-style skills)
from runtime.modules.skills_registry.router import router as skills_registry_router

# Other modules (optional)
agent_router = None
llm_router = None
role_router = None
agent_chat_router = None
chat_router = None
map_router = None
km_router = None
system_router = None
sns_router = None
a2a_router = None

try:
    from runtime.modules.agent.router import router as agent_router
    from runtime.modules.agent.llm_router import router as llm_router
    from runtime.modules.agent.role_router import router as role_router
    from runtime.modules.agent.chat_router import router as agent_chat_router
except Exception as e:
    logger.warning(f"⚠ Agent modules not available: {e}")

try:
    from runtime.modules.chat.router import router as chat_router
except Exception as e:
    logger.warning(f"⚠ Chat module not available: {e}")

try:
    from runtime.modules.map.router import router as map_router
except Exception as e:
    logger.warning(f"⚠ Map module not available: {e}")

try:
    from runtime.modules.km.router import router as km_router
except Exception as e:
    logger.warning(f"⚠ KM module not available: {e}")

try:
    from runtime.modules.system.router import router as system_router
except Exception as e:
    logger.warning(f"⚠ System module not available: {e}")

try:
    from runtime.apps.sns.router import router as sns_router
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
    if os.path.exists("static"):
        # Ensure git-ignored map-config files exist (created from their
        # *.example templates) before the /static mount serves them, so the
        # map iframe never 404s even before any map config has been saved.
        try:
            from runtime.modules.map.file_replace import ensure_map_files_from_templates
            ensure_map_files_from_templates(logger)
        except Exception as _e:
            logger.warning("Failed to ensure map-config files from templates: %s", _e)
        app.mount("/static", StaticFiles(directory="static"), name="static")

    # Create uploads directory if not exists
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    logger.info("✓ Uploads directory mounted")

    # Mount backend scripts directory for static access if present
    if os.path.exists("scripts"):
        app.mount("/scripts", StaticFiles(directory="scripts"), name="scripts")
        logger.info("✓ Scripts directory mounted")
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

if sns_router:
    app.include_router(sns_router, prefix="/api/sns", tags=["SNS"])
    logger.info("✓ SNS Module registered")
    logger.info(lt("home.config.title","cjrok"))


@app.get("/.well-known/agent.json")
async def well_known_agent_json(
    request: Request,
    agent_id: str = "default",
):
    origin = str(getattr(request, "base_url", "") or "").rstrip("/")

    card: dict = {}

    if not isinstance(card, dict) or not card:
        db_agent = None
        try:
            _aid = int(str(agent_id).strip())
            from runtime.modules.agent.service import AgentService
            db_agent = AgentService.get_agent(_aid)
        except Exception:
            db_agent = None

        if isinstance(db_agent, dict):
            capabilities = db_agent.get("capabilities") if isinstance(db_agent.get("capabilities"), dict) else {
                "streaming": True,
                "pushNotifications": True,
                "stateTransitionHistory": False,
            }
            skills = db_agent.get("skills") if isinstance(db_agent.get("skills"), list) else []
            default_input_modes = db_agent.get("default_input_modes")
            default_output_modes = db_agent.get("default_output_modes")

            card = {
                "name": str(db_agent.get("name") or "AI-SNS Agent"),
                "description": str(db_agent.get("description") or ""),
                "url": str(db_agent.get("url") or "").strip(),
                "version": str(db_agent.get("version") or "1.0.0"),
                "protocolVersion": str(db_agent.get("protocol_version") or "0.3"),
                "capabilities": capabilities,
                "skills": skills,
                "defaultInputModes": default_input_modes if isinstance(default_input_modes, list) else ["text"],
                "defaultOutputModes": default_output_modes if isinstance(default_output_modes, list) else ["text"],
                "id": str(db_agent.get("id") or agent_id),
            }
        else:
            card = {
                "name": "AI-SNS Agent",
                "description": "AI Agent Open Platform",
                "url": "",
                "version": "1.0.0",
                "protocolVersion": "0.3",
                "capabilities": {
                    "streaming": True,
                    "pushNotifications": True,
                    "stateTransitionHistory": False,
                },
                "skills": [
                    {
                        "id": "chat",
                        "name": "General Chat",
                        "description": "General conversation and Q&A",
                        "tags": ["conversation", "qa"],
                        "examples": ["Hello!", "What can you do?"],
                        "inputModes": ["text"],
                        "outputModes": ["text"],
                    }
                ],
                "defaultInputModes": ["text"],
                "defaultOutputModes": ["text"],
                "id": str(agent_id or "default"),
            }

    if origin:
        url_val = str(card.get("url") or "").strip()
        if (not url_val) or url_val.startswith("http://localhost:8000"):
            card["url"] = origin

    return JSONResponse(content=jsonable_encoder(card))


@app.get("/agent-card.json")
async def agent_card_json(
    request: Request,
    agent_id: str = "default",
):
    return await well_known_agent_json(request=request, agent_id=agent_id)


@app.get("/a2a/{agent_id}/.well-known/agent-card.json")
async def a2a_agent_card_json(
    request: Request,
    agent_id: str,
):
    return await well_known_agent_json(request=request, agent_id=agent_id)

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
        from db.DBFactory import query_AISnsCfg_map_setting
        import json

        setting = query_AISnsCfg_map_setting() or {}
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
        from db.DBFactory import query_AISnsCfg_map_setting

        setting = query_AISnsCfg_map_setting() or {}
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
async def get_people_list(lng: float = None, lat: float = None, include_me: int = 0):
    remote_base = _get_remote_ai_sns_server_base()
    exclude_nation_id = "" if include_me else _get_current_nation_id_from_db()
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

    # Fallback: return empty list when remote is not configured or remote call failed
    return JSONResponse(content=[])


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
        from runtime.modules.map.dependencies import get_map_service

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
            "tools": "Tools management module (Plugins, MCP, Functions, Skills)"
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

    # Module registration logs are emitted at app.include_router() sites above;
    # do not re-print a hardcoded module list here to avoid masking real load state.

    # Ensure system_cfg DB columns exist before reading them
    try:
        from db.DBFactory import _ensure_system_cfg_columns
        _ensure_system_cfg_columns()
    except Exception as e:
        logger.warning("Failed to ensure system_cfg columns: %s", e)

    # Load language setting and start A2A server if enabled
    try:
        from db.DBFactory import query_SystemCfg
        from runtime.globals import global_env
        sys_cfg = query_SystemCfg(is_delete=False)
        if sys_cfg:
            lang = getattr(sys_cfg, 'language', None) or 'en'
            global_env["lang"] = lang
            logger.info("Language set to: %s", lang)
            logger.info(lt("home.config.title", "Configuration"))

            try:
                from runtime.shared.utils import set_debug_mode
                debug_mode_value = getattr(sys_cfg, 'debug_mode', '') or ''
                set_debug_mode(debug_mode_value)
                logger.info("Debug mode: %s", debug_mode_value or '(off)')
            except Exception as _e:
                logger.warning("Failed to apply debug mode: %s", _e)

            a2a_enabled = getattr(sys_cfg, 'a2a_server_enabled', False)
            logger.info("A2A server enabled: %s", a2a_enabled)
            if a2a_enabled:
                _start_a2a_server_subprocess()
        else:
            logger.info("No system config found, using defaults")
    except Exception as e:
        logger.warning("Failed to load system config: %s", e, exc_info=True)

    # Start XMPP client
    if sns_router:
        try:
            from runtime.apps.sns.xmpp_client import XMPPClientManager
            xmpp_manager = XMPPClientManager.get_instance()
            await xmpp_manager.start()
            logger.info("✓ XMPP Client started")
        except Exception as e:
            logger.warning(f"⚠ Failed to start XMPP client: {e}")

    try:
        from runtime.apps.sns.xmpp_client import XMPPClientManager
        XMPPClientManager.get_instance().maybe_schedule_startup_log_cleanup(delay_seconds=45)
    except Exception as e:
        logger.warning("Failed to schedule startup backend log cleanup: %s", e)

    try:
        async def _stop_sns_engine_if_active():
            try:
                from runtime.apps.sns.service_async import SNSService

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

# ── A2A Server subprocess management ─────────────────────────────────────────
_a2a_process = None
_a2a_process_log_fp = None

def _start_a2a_server_subprocess():
    """Launch a2aserver/server.py as a subprocess."""
    global _a2a_process, _a2a_process_log_fp
    if _a2a_process and _a2a_process.poll() is None:
        logger.info("A2A server already running (pid=%d)", _a2a_process.pid)
        return

    import socket
    import subprocess
    import time

    def _is_port_open(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except Exception:
            return False

    if _is_port_open("127.0.0.1", 8789):
        logger.info("A2A server already listening on port 8789, skipping subprocess start")
        return

    server_script_path = app_directory_parent / "a2aserver" / "server.py"
    if not server_script_path.exists():
        logger.error("A2A server script not found: %s", str(server_script_path))
        return

    log_dir = app_directory / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "a2aserver_subprocess.log"

    try:
        if _a2a_process_log_fp:
            try:
                _a2a_process_log_fp.close()
            except Exception:
                pass
            _a2a_process_log_fp = None

        _a2a_process_log_fp = open(log_file, "a", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        _a2a_process = subprocess.Popen(
            [sys.executable, str(server_script_path)],
            cwd=str(app_directory_parent),
            stdout=_a2a_process_log_fp,
            stderr=_a2a_process_log_fp,
            env=env,
        )

        time.sleep(0.2)
        if _a2a_process.poll() is not None:
            logger.error(
                "A2A server subprocess exited immediately (returncode=%s). See log: %s",
                _a2a_process.returncode,
                str(log_file),
            )
            _a2a_process = None
            return

        for _ in range(20):
            if _is_port_open("127.0.0.1", 8789):
                logger.info("✓ A2A Server started (pid=%d, port=8789)", _a2a_process.pid)
                return
            time.sleep(0.1)

        logger.warning(
            "A2A server subprocess started but port 8789 is not ready yet (pid=%d). See log: %s",
            _a2a_process.pid,
            str(log_file),
        )
    except Exception as e:
        logger.error("Failed to start A2A server subprocess: %s", e, exc_info=True)


def _stop_a2a_server_subprocess():
    """Terminate the A2A server subprocess."""
    global _a2a_process, _a2a_process_log_fp
    if _a2a_process:
        try:
            _a2a_process.terminate()
            _a2a_process.wait(timeout=5)
            logger.info("✓ A2A Server stopped")
        except Exception as e:
            logger.warning("Failed to stop A2A server: %s", e)
            try:
                _a2a_process.kill()
            except Exception:
                pass
        _a2a_process = None

    if _a2a_process_log_fp:
        try:
            _a2a_process_log_fp.close()
        except Exception:
            pass
        _a2a_process_log_fp = None


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Execute when the application shuts down"""
    logger.info("AI-SNS API Server shutting down...")

    _stop_a2a_server_subprocess()

    if sns_router:
        try:
            from runtime.apps.sns.xmpp_client import XMPPClientManager
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
            log_level="info",
            log_config=_build_uvicorn_log_config(),
            use_colors=False,
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
