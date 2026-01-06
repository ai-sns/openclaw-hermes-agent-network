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

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# 导入原有模块
from db.DBFactory import (
    add_AgentCfg, query_AgentCfg_All, update_AgentCfg, delete_AgentCfg,
    query_AiChatCfg, query_AiChatCfg_All, add_AiChatCfg, update_AiChatCfg, delete_AiChatCfg,
    query_SystemCfg, update_SystemCfg,
    query_AIChatMessages_All as query_AIChatMessages, add_AIChatMessages as add_AIChatMessage,
    query_KMCfg_All, add_KMCfg, update_KMCfg, delete_KMCfg
)

from Agent import Agent
from globals import global_agent_list, global_plugin_list, global_buddy_list

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

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

# Agent实例管理
agent_instances: Dict[str, Agent] = {}

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

# ==================== API路由 ====================

@app.get("/")
async def root():
    return {"message": "AI-SNS API Server", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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
                if agent_key in agent_instances:
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

def start_server(host: str = "0.0.0.0", port: int = 8765):
    """启动API服务器"""
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI-SNS API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind")

    args = parser.parse_args()

    logger.info(f"Starting AI-SNS API Server on {args.host}:{args.port}")
    start_server(args.host, args.port)
