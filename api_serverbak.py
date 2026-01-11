# -*- coding: utf-8 -*-
"""
AI-SNS API Server
将PyQt5应用的后端功能暴露为REST API和WebSocket服务
"""

import os
import sys
from pathlib import Path

# 设置工作目录
app_directory = Path(__file__).resolve().parent
os.chdir(app_directory)

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import yaml

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import httpx
from sse_starlette.sse import EventSourceResponse

# 导入原有模块
from db.DBFactory import (
    add_AgentCfg, query_AgentCfg_All, update_AgentCfg, delete_AgentCfg,
    query_AiChatCfg, query_AiChatCfg_All, add_AiChatCfg, update_AiChatCfg, delete_AiChatCfg,
    query_AiChatCfg_map, query_AiChatCfg_map_setting, update_AiChatCfg_map,
    query_SystemCfg, update_SystemCfg,
    query_AIChatMessages_All as query_AIChatMessages, add_AIChatMessages as add_AIChatMessage,
    query_KMCfg_All, add_KMCfg, update_KMCfg, delete_KMCfg,
    # 地图功能相关
    add_map_task, query_map_tasks, query_single_map_task, update_map_task, delete_map_task,
    add_map_tool, query_map_tools, query_single_map_tool, update_map_tool, delete_map_tool,
    add_map_trade, query_map_trades, query_single_map_trade, update_map_trade, delete_map_trade,
    add_map_visit, query_map_visits, query_single_map_visit, update_map_visit, delete_map_visit
)

# 延迟导入 Agent 模块以加快启动速度
# from Agent import Agent  # 注释掉，改为需要时才导入
# from globals import global_agent_list, global_plugin_list, global_buddy_list  # 注释掉，改为需要时才导入

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="AI-SNS API",
    description="AI Agent Social Network API Server",
    version="1.0.0"
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

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket, client_id):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_message(self, message, client_id):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

# Agent实例管理 (延迟导入，避免启动时加载autogen库)
agent_instances: Dict[str, Any] = {}

# AI配置管理（优先级：数据库 > 环境变量 > 配置文件）
def load_ai_config_from_file():
    """从配置文件加载 AI 配置"""
    config_file = Path(__file__).parent / 'ai_config.yaml'
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                ai_config = config.get('ai', {})
                return {
                    "api_base": ai_config.get('api_base', 'https://api.openai.com/v1'),
                    "api_key": ai_config.get('api_key', ''),
                    "model": ai_config.get('model', 'gpt-4o-mini'),
                    "temperature": ai_config.get('temperature', 1.0),
                    "max_tokens": ai_config.get('max_tokens', 4096)
                }
        except Exception as e:
            logger.warning(f"Failed to load AI config from file: {e}")
    return None

def get_ai_config():
    """
    获取AI配置
    优先级: 数据库配置 > 环境变量 > 配置文件 (ai_config.yaml)
    """
    # 1. 首先尝试从数据库读取第一个可用的AI配置
    try:
        configs = query_AiChatCfg_All(is_delete=0)
        if configs and len(configs) > 0:
            cfg = configs[0]
            api_key = getattr(cfg, 'api_key', '')
            # 只有当 API key 不为空时才使用数据库配置
            if api_key and api_key.strip():
                logger.info("Using AI config from database")
                return {
                    "api_base": getattr(cfg, 'api_base', 'https://api.openai.com/v1'),
                    "api_key": api_key,
                    "model": getattr(cfg, 'model', 'gpt-4o-mini'),
                    "temperature": getattr(cfg, 'temperature', 1.0),
                    "max_tokens": getattr(cfg, 'max_tokens', 4096)
                }
    except Exception as e:
        logger.warning(f"Failed to load AI config from database: {e}")

    # 2. 如果数据库中没有配置，尝试从环境变量读取
    if os.environ.get('OPENAI_API_KEY'):
        logger.info("Using AI config from environment variables")
        return {
            "api_base": os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1'),
            "api_key": os.environ.get('OPENAI_API_KEY'),
            "model": os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            "temperature": float(os.environ.get('OPENAI_TEMPERATURE', '1.0')),
            "max_tokens": int(os.environ.get('OPENAI_MAX_TOKENS', '4096'))
        }

    # 3. 如果环境变量也没有，从配置文件读取
    file_config = load_ai_config_from_file()
    if file_config and file_config.get('api_key'):
        logger.info("Using AI config from ai_config.yaml")
        return file_config

    # 4. 最后的默认配置（不应该到达这里）
    logger.error("No valid AI config found! Please configure API key in ai_config.yaml, environment variables, or database")
    return {
        "api_base": 'https://api.openai.com/v1',
        "api_key": '',
        "model": 'gpt-4o-mini',
        "temperature": 1.0,
        "max_tokens": 4096
    }

# ==================== 数据模型 ====================

class AgentConfig(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = ""
    model: Optional[str] = "gpt-4"
    api_key: Optional[str] = ""
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    system_prompt: Optional[str] = ""
    is_active: Optional[bool] = True

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    agent_id: int
    message: str
    conversation_id: Optional[str] = None

class AiChatConfig(BaseModel):
    id: Optional[int] = None
    name: str
    api_base: Optional[str] = ""
    api_key: Optional[str] = ""
    model: Optional[str] = "gpt-4"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    is_delete: Optional[int] = 0

class KMConfig(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = ""
    km_type: Optional[str] = "vector"
    path: Optional[str] = ""

class SystemConfig(BaseModel):
    theme: Optional[str] = "dark"
    language: Optional[str] = "zh"
    minirunontray: Optional[bool] = True

# ==================== 地图功能数据模型 ====================

class MapConfig(BaseModel):
    """地图配置"""
    id: Optional[int] = None
    map_type: Optional[str] = "baidu"  # "baidu" 或 "google"
    map_api_key: Optional[str] = ""
    map_id: Optional[str] = ""
    current_position: Optional[Dict[str, Any]] = None
    home_position: Optional[Dict[str, Any]] = None
    route_status: Optional[str] = "stopped"  # "playing" 或 "stopped"
    route_start: Optional[str] = ""
    route_end: Optional[str] = ""
    route_current_position: Optional[Dict[str, Any]] = None
    route_distance: Optional[float] = 0.0

class MapMarker(BaseModel):
    """地图标记"""
    id: Optional[str] = None
    location: Dict[str, float]  # {"lng": 116.3974, "lat": 39.9093}
    type: Optional[str] = "person"
    data: Optional[Dict[str, Any]] = None
    visible: Optional[bool] = True

class RouteRequest(BaseModel):
    """路线请求"""
    start: str  # 地址或坐标字符串
    end: str    # 地址或坐标字符串
    position_type: Optional[str] = "address"  # "address" 或 "coordinates"

class RouteControl(BaseModel):
    """路线控制"""
    action: str  # "start", "stop", "pause", "resume"

class ChatMessageMap(BaseModel):
    """地图聊天消息"""
    from_user: str
    to_user: str
    content: str
    location: Optional[Dict[str, float]] = None

class StreamChatRequest(BaseModel):
    """流式聊天请求"""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = 4096

# ==================== API路由 ====================

@app.post("/jsonrpc")
async def jsonrpc(request: dict):
    """JSON-RPC 2.0 接口"""
    try:
        # 验证 JSON-RPC 版本
        if request.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "JSON-RPC version must be 2.0"
                },
                "id": request.get("id")
            }

        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # 处理不同的方法
        if method == "get_map_settings":
            result = await get_map_settings()
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "update_map_settings":
            result = await update_map_settings(MapConfig(**params))
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "send_map_chat_message":
            result = await send_map_chat_message(ChatMessageMap(**params))
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "get_home_position":
            result = await get_home_position()
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "update_home_position":
            result = await update_home_position(params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "plan_route":
            result = await plan_route(RouteRequest(**params))
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "control_route":
            route_id = params.get("route_id")
            control = RouteControl(**params.get("control"))
            result = await control_route(route_id, control)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "get_map_markers":
            result = await get_map_markers()
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "add_map_marker":
            result = await add_map_marker(MapMarker(**params))
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "update_map_marker":
            marker_id = params.get("marker_id")
            marker = MapMarker(**params.get("marker"))
            result = await update_map_marker(marker_id, marker)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "delete_map_marker":
            result = await delete_map_marker(params.get("marker_id"))
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        elif method == "get_map_chat_history":
            result = await get_map_chat_history()
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
        logger.error(f"JSON-RPC error: {e}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": "Server error",
                "data": str(e)
            },
            "id": request.get("id")
        }

@app.get("/")
async def root():
    return {
        "message": "AI-SNS API Server",
        "version": "1.0.0",
        "status": "running",
        "jsonrpc": "2.0 available",
        "endpoints": {
            "health": "GET /health",
            "stream_chat": "POST /api/chat/stream (流式聊天)",
            "agents": "GET /api/agents (获取所有 Agent)",
            "ai_configs": "GET /api/ai-chat/configs (获取 AI 配置)",
            "map_settings": "GET /api/map/settings (地图设置)",
            "docs": "GET /docs (FastAPI 自动文档)"
        },
        "test": {
            "browser": "在浏览器中访问 /api/chat/stream 查看使用说明",
            "script": "运行 python test_stream_api.py 测试流式聊天"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/config/status")
async def config_status():
    """检查 AI 配置状态"""
    config = get_ai_config()
    has_api_key = bool(config.get('api_key'))

    return {
        "has_api_key": has_api_key,
        "api_base": config.get('api_base'),
        "model": config.get('model'),
        "api_key_preview": config.get('api_key', '')[:10] + "..." if has_api_key else "未配置",
        "config_file_exists": Path('ai_config.yaml').exists(),
        "recommendation": "配置正常" if has_api_key else "请在 ai_config.yaml 中配置 api_key"
    }

# ==================== Agent 管理 ====================

@app.get("/api/agents")
async def get_agents():
    """获取所有Agent配置"""
    try:
        agents = query_AgentCfg_All()
        result = []
        for agent in agents:
            result.append({
                "id": agent.id,
                "name": agent.name,
                "description": getattr(agent, 'description', ''),
                "model": getattr(agent, 'model', 'gpt-4'),
                "is_active": getattr(agent, 'is_active', True)
            })
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents")
async def create_agent(config: AgentConfig):
    """创建新Agent"""
    try:
        agent_id = add_AgentCfg(
            name=config.name,
            description=config.description,
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            system_prompt=config.system_prompt
        )
        return {"success": True, "data": {"id": agent_id}}
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: int, config: AgentConfig):
    """更新Agent配置"""
    try:
        update_AgentCfg(agent_id, **config.dict(exclude_unset=True))
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: int):
    """删除Agent"""
    try:
        delete_AgentCfg(agent_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== AI Chat 配置 ====================

@app.get("/api/ai-chat/configs")
async def get_ai_chat_configs():
    """获取所有AI聊天配置"""
    try:
        configs = query_AiChatCfg_All(is_delete=0)
        result = []
        for cfg in configs:
            result.append({
                "id": cfg.id,
                "name": getattr(cfg, 'name', ''),
                "model": getattr(cfg, 'model', 'gpt-4'),
                "api_base": getattr(cfg, 'api_base', ''),
                "temperature": getattr(cfg, 'temperature', 0.7)
            })
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting AI chat configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai-chat/configs")
async def create_ai_chat_config(config: AiChatConfig):
    """创建AI聊天配置"""
    try:
        config_id = add_AiChatCfg(**config.dict(exclude_unset=True))
        return {"success": True, "data": {"id": config_id}}
    except Exception as e:
        logger.error(f"Error creating AI chat config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 聊天功能 ====================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """发送聊天消息并获取回复"""
    try:
        # 获取或创建Agent实例
        agent_key = f"agent_{request.agent_id}"
        if agent_key not in agent_instances:
            # 延迟导入 Agent 模块（避免启动时加载autogen库）
            from Agent import Agent
            # 从数据库加载Agent配置并创建实例
            agent_instances[agent_key] = Agent()

        agent = agent_instances[agent_key]

        # 发送消息并获取回复
        response = await asyncio.to_thread(
            agent.chat,
            request.message,
            request.conversation_id
        )

        # 保存消息到数据库
        add_AIChatMessage(
            agent_id=request.agent_id,
            role="user",
            content=request.message,
            conversation_id=request.conversation_id
        )
        add_AIChatMessage(
            agent_id=request.agent_id,
            role="assistant",
            content=response,
            conversation_id=request.conversation_id
        )

        return {
            "success": True,
            "data": {
                "response": response,
                "conversation_id": request.conversation_id
            }
        }
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{agent_id}")
async def get_chat_history(agent_id: int, conversation_id: Optional[str] = None):
    """获取聊天历史"""
    try:
        messages = query_AIChatMessages(
            agent_id=agent_id,
            conversation_id=conversation_id
        )
        result = []
        for msg in messages:
            result.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": str(msg.timestamp) if hasattr(msg, 'timestamp') else None
            })
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/stream")
async def stream_chat_info():
    """流式聊天端点信息（GET 请求）"""
    return {
        "message": "这是一个 POST 端点，用于流式聊天",
        "method": "POST",
        "url": "/api/chat/stream",
        "content_type": "application/json",
        "accept": "text/event-stream",
        "request_body": {
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "model": "gpt-4o-mini (可选)",
            "temperature": 1.0,
            "max_tokens": 4096
        },
        "example_curl": (
            'curl -N -X POST http://localhost:8788/api/chat/stream '
            '-H "Content-Type: application/json" '
            '-H "Accept: text/event-stream" '
            '-d \'{"messages": [{"role": "user", "content": "你好"}]}\''
        ),
        "test_script": "运行 python test_stream_api.py 进行测试"
    }

@app.post("/api/chat/stream")
async def stream_chat(request: StreamChatRequest):
    """流式聊天接口（使用 SSE）"""
    ai_config = get_ai_config()

    # 检查 API key
    if not ai_config['api_key']:
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "API key 未配置。请在 ai_config.yaml 中配置 api_key"
                })
            }
        return EventSourceResponse(error_generator())

    # 使用请求中的参数或配置中的默认值
    model = request.model or ai_config['model']
    temperature = request.temperature if request.temperature is not None else ai_config['temperature']
    max_tokens = request.max_tokens or ai_config['max_tokens']

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                api_url = f"{ai_config['api_base'].rstrip('/')}/chat/completions"

                request_data = {
                    "model": model,
                    "messages": request.messages,
                    "stream": True,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                logger.info(f"Streaming chat request to: {api_url}")
                logger.info(f"Using model: {model}")

                async with client.stream(
                    'POST',
                    api_url,
                    json=request_data,
                    headers={
                        'Authorization': f"Bearer {ai_config['api_key']}",
                        'Content-Type': 'application/json'
                    }
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"API error: {response.status_code} - {error_text.decode()}")
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "error": f"HTTP {response.status_code}: {error_text.decode()}"
                            })
                        }
                        return

                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        chunk_str = chunk.decode('utf-8')
                        buffer += chunk_str

                        lines = buffer.split('\n')
                        buffer = lines.pop() if lines else ""

                        for line in lines:
                            line = line.strip()
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    yield {
                                        "event": "done",
                                        "data": json.dumps({"status": "completed"})
                                    }
                                    return
                                try:
                                    parsed = json.loads(data)
                                    choices = parsed.get('choices', [])
                                    if choices and len(choices) > 0:
                                        content = choices[0].get('delta', {}).get('content', '')
                                        if content:
                                            yield {
                                                "event": "message",
                                                "data": json.dumps({"content": content})
                                            }
                                except json.JSONDecodeError as e:
                                    logger.debug(f"JSON parse error: {e} for line: {line}")
                                    continue

                    # 处理剩余的 buffer
                    if buffer.strip():
                        line = buffer.strip()
                        if line.startswith('data: ') and line[6:] != '[DONE]':
                            try:
                                parsed = json.loads(line[6:])
                                choices = parsed.get('choices', [])
                                if choices and len(choices) > 0:
                                    content = choices[0].get('delta', {}).get('content', '')
                                    if content:
                                        yield {
                                            "event": "message",
                                            "data": json.dumps({"content": content})
                                        }
                            except json.JSONDecodeError:
                                pass

                    yield {
                        "event": "done",
                        "data": json.dumps({"status": "completed"})
                    }

        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())

# ==================== 知识库 ====================

@app.get("/api/knowledge-base")
async def get_knowledge_bases():
    """获取所有知识库"""
    try:
        kbs = query_KMCfg_All()
        result = []
        for kb in kbs:
            result.append({
                "id": kb.id,
                "name": getattr(kb, 'name', ''),
                "description": getattr(kb, 'description', ''),
                "km_type": getattr(kb, 'km_type', 'vector'),
                "path": getattr(kb, 'path', '')
            })
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting knowledge bases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge-base")
async def create_knowledge_base(config: KMConfig):
    """创建知识库"""
    try:
        kb_id = add_KMCfg(**config.dict(exclude_unset=True))
        return {"success": True, "data": {"id": kb_id}}
    except Exception as e:
        logger.error(f"Error creating knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge-base/{kb_id}/upload")
async def upload_to_knowledge_base(kb_id: int, file: UploadFile = File(...)):
    """上传文件到知识库"""
    try:
        # 保存文件
        upload_dir = Path(f"km/uploads/{kb_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # TODO: 处理文件并添加到向量数据库

        return {"success": True, "data": {"filename": file.filename, "path": str(file_path)}}
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 系统配置 ====================

@app.get("/api/system/config")
async def get_system_config():
    """获取系统配置"""
    try:
        config = query_SystemCfg()
        return {
            "success": True,
            "data": {
                "theme": getattr(config, 'theme', 'dark'),
                "language": getattr(config, 'language', 'zh'),
                "minirunontray": getattr(config, 'minirunontray', True)
            }
        }
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/system/config")
async def update_system_config(config: SystemConfig):
    """更新系统配置"""
    try:
        update_SystemCfg(**config.dict(exclude_unset=True))
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 地图功能 API ====================

@app.get("/api/map/settings")
async def get_map_settings():
    """获取地图配置"""
    try:
        cfg = query_AiChatCfg_map()
        if cfg:
            return {
                "success": True,
                "data": {
                    "id": cfg.id,
                    "map_type": getattr(cfg, 'map_type', 'baidu'),
                    "map_api_key": getattr(cfg, 'map_api_key', ''),
                    "map_id": getattr(cfg, 'map_id', ''),
                    "current_position": json.loads(getattr(cfg, 'current_position', '{}')) if getattr(cfg, 'current_position', None) else {"lng": 116.3974, "lat": 39.9093},
                    "home_position": json.loads(getattr(cfg, 'home_position', '{}')) if getattr(cfg, 'home_position', None) else {},
                    "route_status": getattr(cfg, 'route_status', 'stopped'),
                    "route_start": getattr(cfg, 'route_start', ''),
                    "route_end": getattr(cfg, 'route_end', ''),
                    "route_current_position": json.loads(getattr(cfg, 'route_current_position', '{}')) if getattr(cfg, 'route_current_position', None) else {},
                    "route_distance": getattr(cfg, 'route_distance', 0.0),
                    "avatar3d": getattr(cfg, 'avatar3d', 'default.glb'),
                    "nationid": getattr(cfg, 'nationid', '123456'),
                    "account": getattr(cfg, 'account', 'user@example.com'),
                    "nick_name": getattr(cfg, 'nickname', '用户昵称'),
                    "avatar": getattr(cfg, 'avatar', 'avatar.png'),
                    "profile": getattr(cfg, 'sign', '个人简介'),
                    "sns_url": getattr(cfg, 'sns_url', 'https://example.com'),
                    "status": getattr(cfg, 'status', 'online')
                }
            }
        # 如果没有配置，返回默认配置
        default_config = {
            "map_type": "baidu",
            "map_api_key": "",
            "map_id": "",
            "current_position": {"lng": 116.3974, "lat": 39.9093},
            "home_position": {},
            "route_status": "stopped",
            "route_start": "",
            "route_end": "",
            "route_current_position": {},
            "route_distance": 0.0,
            "avatar3d": "default.glb",
            "nationid": "123456",
            "account": "user@example.com",
            "nick_name": "用户昵称",
            "avatar": "avatar.png",
            "profile": "个人简介",
            "sns_url": "https://example.com",
            "status": "online"
        }
        return {"success": True, "data": default_config}
    except Exception as e:
        logger.error(f"Error getting map settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/map/settings")
async def update_map_settings(config: MapConfig):
    """更新地图配置"""
    try:
        cfg = query_AiChatCfg_map()
        if cfg:
            # 更新现有配置
            update_AiChatCfg_map(
                cfg.id,
                map_type=config.map_type,
                map_api_key=config.map_api_key,
                map_id=config.map_id,
                current_position=json.dumps(config.current_position) if config.current_position else '{}',
                home_position=json.dumps(config.home_position) if config.home_position else '{}',
                route_status=config.route_status,
                route_start=config.route_start,
                route_end=config.route_end,
                route_current_position=json.dumps(config.route_current_position) if config.route_current_position else '{}',
                route_distance=config.route_distance
            )
            return {"success": True}
        else:
            # 如果没有配置，这里不应该创建新配置，因为 aichat_cfg 表的记录应该通过其他方式创建
            raise HTTPException(status_code=404, detail="Map configuration not found")
    except Exception as e:
        logger.error(f"Error updating map settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/map/settings/home")
async def get_home_position():
    """获取住址配置"""
    try:
        cfg = query_AiChatCfg_map()
        if cfg:
            return {
                "success": True,
                "data": json.loads(getattr(cfg, 'home_position', '{}'))
            }
        return {"success": True, "data": {}}
    except Exception as e:
        logger.error(f"Error getting home position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/map/settings/home")
async def update_home_position(home_position: Dict[str, Any]):
    """更新住址配置"""
    try:
        cfg = query_AiChatCfg_map()
        if cfg:
            update_AiChatCfg_map(cfg.id, home_position=json.dumps(home_position))
        else:
            raise HTTPException(status_code=404, detail="Map configuration not found")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating home position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/map/route")
async def plan_route(request: RouteRequest):
    """规划路线"""
    try:
        # TODO: 实现路线规划逻辑
        # 目前返回模拟数据
        distance = 5.2  # 公里
        duration = 1200  # 秒
        return {
            "success": True,
            "data": {
                "distance": distance,
                "duration": duration,
                "polyline": [],
                "status": "completed"
            }
        }
    except Exception as e:
        logger.error(f"Error planning route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/map/route/{route_id}/control")
async def control_route(route_id: str, request: RouteControl):
    """控制路线模拟"""
    try:
        action = request.action
        if action not in ["start", "stop", "pause", "resume"]:
            raise HTTPException(status_code=400, detail="Invalid action")
        # TODO: 实现路线控制逻辑
        return {"success": True, "data": {"action": action, "status": "ok"}}
    except Exception as e:
        logger.error(f"Error controlling route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/map/markers")
async def get_map_markers():
    """获取地图标记列表"""
    try:
        # TODO: 从数据库或其他数据源获取标记
        markers = []
        return {"success": True, "data": markers}
    except Exception as e:
        logger.error(f"Error getting map markers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/map/markers")
async def add_map_marker(marker: MapMarker):
    """添加地图标记"""
    try:
        # TODO: 保存标记到数据库
        return {"success": True, "data": {"id": marker.id or "marker_" + str(datetime.now().timestamp())}}
    except Exception as e:
        logger.error(f"Error adding map marker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/map/markers/{marker_id}")
async def update_map_marker(marker_id: str, marker: MapMarker):
    """更新地图标记"""
    try:
        # TODO: 更新标记信息
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating map marker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/map/markers/{marker_id}")
async def delete_map_marker(marker_id: str):
    """删除地图标记"""
    try:
        # TODO: 删除标记
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting map marker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/map/chat")
async def send_map_chat_message(message: ChatMessageMap):
    """发送地图聊天消息"""
    try:
        # TODO: 保存聊天消息到数据库
        # 通过WebSocket广播消息
        await manager.broadcast({
            "type": "map_chat_message",
            "message": {
                "user": message.user,
                "content": message.content,
                "timestamp": datetime.now().isoformat()
            }
        })
        return {"success": True}
    except Exception as e:
        logger.error(f"Error sending map chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/map/chat/history")
async def get_map_chat_history():
    """获取地图聊天历史"""
    try:
        # TODO: 从数据库获取聊天历史
        messages = []
        return {"success": True, "data": messages}
    except Exception as e:
        logger.error(f"Error getting map chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== WebSocket ====================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接端点，用于实时消息推送"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()

            # 处理不同类型的消息
            msg_type = data.get("type", "")

            if msg_type == "chat":
                # 处理聊天消息
                agent_id = data.get("agent_id")
                message = data.get("message")

                # 获取Agent回复
                agent_key = f"agent_{agent_id}"
                if agent_key not in agent_instances:
                    # 延迟导入 Agent 模块
                    from Agent import Agent
                    agent_instances[agent_key] = Agent()

                agent = agent_instances[agent_key]
                response = await asyncio.to_thread(agent.chat, message)

                await manager.send_message({
                    "type": "chat_response",
                    "agent_id": agent_id,
                    "response": response
                }, client_id)

            elif msg_type == "ping":
                await manager.send_message({"type": "pong"}, client_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)

# ==================== 插件系统 ====================

@app.get("/api/plugins")
async def get_plugins():
    """获取所有插件"""
    try:
        plugins = []
        plugin_dir = Path("pluginsmanager/plugins_gui")
        if plugin_dir.exists():
            for plugin_path in plugin_dir.iterdir():
                if plugin_path.is_dir() and (plugin_path / "main.py").exists():
                    plugins.append({
                        "name": plugin_path.name,
                        "path": str(plugin_path),
                        "enabled": True
                    })
        return {"success": True, "data": plugins}
    except Exception as e:
        logger.error(f"Error getting plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 文件服务 ====================

@app.get("/api/files/{file_path:path}")
async def get_file(file_path: str):
    """获取文件"""
    try:
        full_path = Path(file_path)
        if full_path.exists() and full_path.is_file():
            return FileResponse(full_path)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 启动服务器 ====================

def start_server(host: str = "0.0.0.0", port: int = 8788, reload: bool = True):
    """启动API服务器"""
    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI-SNS API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8788, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")

    args = parser.parse_args()

    logger.info(f"Starting AI-SNS API Server on {args.host}:{args.port}")
    start_server(args.host, args.port, reload=args.reload)
