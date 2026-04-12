"""
A2A Protocol Router

API routes for Agent-to-Agent (A2A) protocol endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from agent_platform.protocols.a2a.agent_card import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    get_agent_card_manager
)
from agent_platform.protocols.a2a.task_manager import (
    A2ATask,
    A2ATaskType,
    A2ATaskStatus,
    get_a2a_task_manager
)
from agent_platform.protocols.a2a.handshake import (
    HandshakeRequest,
    HandshakeResponse,
    HandshakeStatus,
    get_handshake_manager
)
from agent_platform.gateway.middleware.auth import get_current_api_key, require_scope
from agent_platform.security.api_key import APIKeyInfo


# Router
a2a_router = APIRouter(prefix="/a2a", tags=["A2A Protocol"])


# Request/Response Models
class HandshakeRequestModel(BaseModel):
    """Handshake request model"""
    caller_agent_id: str
    caller_agent_name: str
    caller_endpoint: str
    caller_capabilities: List[str] = Field(default_factory=list)
    requested_capabilities: List[str] = Field(default_factory=list)
    signature: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HandshakeResponseModel(BaseModel):
    """Handshake response model"""
    request_id: str
    status: str
    responder_agent_id: str
    responder_agent_name: str
    responder_endpoint: str
    granted_capabilities: List[str] = Field(default_factory=list)
    session_token: Optional[str] = None
    session_expires_at: Optional[str] = None
    signature: Optional[str] = None
    message: str = ""


class TaskCreateRequest(BaseModel):
    """Task creation request"""
    agent_id: str
    messages: List[Dict[str, str]]
    task_type: str = "chat"
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """Task response model"""
    task_id: str
    agent_id: str
    task_type: str
    status: str
    progress: float = 0.0
    output: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Agent Card Endpoints
@a2a_router.get("/agent-card", response_model=Dict[str, Any])
async def get_agent_card(
    agent_id: str = Query(default="default", description="Agent ID")
):
    """
    Get agent card for discovery.

    This endpoint returns the Agent Card for the specified agent,
    following Google's A2A protocol specification.
    """
    # Priority 1: registered in-memory cards
    manager = get_agent_card_manager()
    card = manager.get_card(agent_id)
    if card:
        return card.to_dict()

    # Priority 2: map database agent_cfg into an A2A AgentCard
    # agent_id is expected to be the DB AgentCfg.id (integer) in this project.
    db_agent = None
    try:
        _aid = int(str(agent_id).strip())
        from backend.modules.agent.service import AgentService
        db_agent = AgentService.get_agent(_aid)
    except Exception:
        db_agent = None

    if isinstance(db_agent, dict):
        # Build a Google A2A compatible card from agent_cfg memo fields.
        name = str(db_agent.get("name") or "AI-SNS Agent")
        description = str(db_agent.get("description") or "")
        url = str(db_agent.get("url") or "").strip()
        if not url:
            url = "http://localhost:8000/a2a"

        version = str(db_agent.get("version") or "1.0.0")
        protocol_version = str(db_agent.get("protocol_version") or "0.3")

        cap_raw = db_agent.get("capabilities")
        capabilities = AgentCapabilities()
        if isinstance(cap_raw, dict):
            try:
                capabilities = AgentCapabilities(**cap_raw)
            except Exception:
                capabilities = AgentCapabilities()

        skills_raw = db_agent.get("skills")
        skills: List[AgentSkill] = []
        if isinstance(skills_raw, list):
            for item in skills_raw:
                if not isinstance(item, dict):
                    continue
                sid = (item.get("id") or item.get("name") or "").strip()
                if not sid:
                    continue
                try:
                    skills.append(AgentSkill(**item, id=str(sid)))
                except Exception:
                    # best-effort coercion
                    skills.append(
                        AgentSkill(
                            id=str(sid),
                            name=str(item.get("name") or sid),
                            description=str(item.get("description") or ""),
                            tags=item.get("tags") if isinstance(item.get("tags"), list) else [],
                            examples=item.get("examples") if isinstance(item.get("examples"), list) else [],
                            inputModes=item.get("inputModes") if isinstance(item.get("inputModes"), list) else ["text"],
                            outputModes=item.get("outputModes") if isinstance(item.get("outputModes"), list) else ["text"],
                        )
                    )

        default_input_modes = db_agent.get("default_input_modes")
        default_output_modes = db_agent.get("default_output_modes")

        card = AgentCard(
            id=str(db_agent.get("id") or agent_id),
            name=name,
            description=description,
            url=url,
            version=version,
            protocolVersion=protocol_version,
            capabilities=capabilities,
            skills=skills,
            defaultInputModes=default_input_modes if isinstance(default_input_modes, list) else ["text"],
            defaultOutputModes=default_output_modes if isinstance(default_output_modes, list) else ["text"],
        )
        return card.to_dict()

    # Priority 3: default fallback card (kept for backward compatibility)
    return AgentCard(
        id=str(agent_id or "default"),
        name="AI-SNS Agent",
        description="AI Agent Open Platform",
        url="http://localhost:8000/a2a",
        version="1.0.0",
        protocolVersion="0.3",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="chat",
                name="General Chat",
                description="General conversation and Q&A",
                tags=["conversation", "qa"],
                examples=["Hello!", "What can you do?"],
                inputModes=["text"],
                outputModes=["text"],
            )
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
    ).to_dict()


@a2a_router.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents():
    """List all registered agents"""
    # If running under api_server.py, prefer DB agents for discovery.
    try:
        from backend.modules.agent.service import AgentService
        agents = AgentService.get_all_agents()
        out: List[Dict[str, Any]] = []
        if isinstance(agents, list):
            for a in agents:
                if not isinstance(a, dict):
                    continue
                aid = a.get("id")
                if aid is None:
                    continue
                try:
                    out.append((await get_agent_card(agent_id=str(aid))))
                except Exception:
                    continue
        if out:
            return out
    except Exception:
        pass

    manager = get_agent_card_manager()
    return [card.to_dict() for card in manager.list_cards()]


# Handshake Endpoints
@a2a_router.post("/handshake", response_model=HandshakeResponseModel)
async def initiate_handshake(
    request: HandshakeRequestModel,
    auto_accept: bool = Query(default=True, description="Auto-accept handshake")
):
    """
    Initiate A2A handshake.

    This endpoint handles incoming handshake requests from other agents.
    It validates the request, negotiates capabilities, and creates a session.
    """
    manager = get_handshake_manager()

    # Create handshake request object
    hs_request = HandshakeRequest(
        request_id=manager.generate_request_id(),
        caller_agent_id=request.caller_agent_id,
        caller_agent_name=request.caller_agent_name,
        caller_endpoint=request.caller_endpoint,
        caller_capabilities=request.caller_capabilities,
        requested_capabilities=request.requested_capabilities,
        signature=request.signature,
        metadata=request.metadata
    )

    # Process handshake
    response = manager.process_handshake_request(hs_request, auto_accept=auto_accept)

    return HandshakeResponseModel(
        request_id=response.request_id,
        status=response.status.value,
        responder_agent_id=response.responder_agent_id,
        responder_agent_name=response.responder_agent_name,
        responder_endpoint=response.responder_endpoint,
        granted_capabilities=response.granted_capabilities,
        session_token=response.session_token,
        session_expires_at=response.session_expires_at.isoformat() if response.session_expires_at else None,
        signature=response.signature,
        message=response.message
    )


@a2a_router.post("/handshake/validate")
async def validate_session(
    session_token: str,
    required_capability: Optional[str] = None
):
    """Validate a session token"""
    manager = get_handshake_manager()
    session = manager.validate_session(session_token, required_capability)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {
        "valid": True,
        "session_id": session.session_id,
        "caller_agent_id": session.caller_agent_id,
        "granted_capabilities": session.granted_capabilities,
        "expires_at": session.expires_at.isoformat()
    }


@a2a_router.post("/handshake/revoke")
async def revoke_session(session_token: str):
    """Revoke a session"""
    manager = get_handshake_manager()

    if manager.revoke_session(session_token):
        return {"success": True, "message": "Session revoked"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


# Task Endpoints
@a2a_router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """
    Create an A2A task.

    This endpoint creates an async task for agent execution.
    The task is queued and processed asynchronously.
    """
    manager = get_a2a_task_manager()

    # Map task type
    task_type_map = {
        "chat": A2ATaskType.CHAT,
        "completion": A2ATaskType.COMPLETION,
        "tool_call": A2ATaskType.TOOL_CALL,
        "multi_step": A2ATaskType.MULTI_STEP
    }
    task_type = task_type_map.get(request.task_type, A2ATaskType.CHAT)

    # Create task
    task = await manager.create_task(
        agent_id=request.agent_id,
        messages=request.messages,
        task_type=task_type,
        caller_agent_id=key_info.user_id if key_info else None,
        webhook_url=request.webhook_url,
        webhook_secret=request.webhook_secret,
        metadata=request.metadata,
        timeout_seconds=request.timeout_seconds
    )

    return TaskResponse(
        task_id=task.task_id,
        agent_id=task.agent_id,
        task_type=task.task_type.value,
        status=task.status.value,
        progress=task.progress,
        created_at=task.created_at.isoformat(),
        metadata=task.metadata
    )


@a2a_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get task status"""
    manager = get_a2a_task_manager()
    task = await manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        task_id=task.task_id,
        agent_id=task.agent_id,
        task_type=task.task_type.value,
        status=task.status.value,
        progress=task.progress,
        output=task.output_message.content if task.output_message else None,
        error=task.error_message,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        metadata=task.metadata
    )


@a2a_router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a pending task"""
    manager = get_a2a_task_manager()

    if await manager.cancel_task(task_id):
        return {"success": True, "message": "Task cancelled"}
    else:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel task (not pending or not found)"
        )


@a2a_router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    """
    Stream task progress via SSE.

    This endpoint provides real-time updates for task execution.
    """
    manager = get_a2a_task_manager()
    task = await manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def generate():
        async for event in manager.stream_task_progress(task_id):
            event_type = event.get("event", "message")
            data = json.dumps(event.get("data", {}))
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Synchronous execution endpoint
@a2a_router.post("/tasks/execute", response_model=TaskResponse)
async def execute_task_sync(
    request: TaskCreateRequest,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """
    Execute a task synchronously.

    This endpoint creates and immediately executes a task,
    returning the result in the response.
    """
    manager = get_a2a_task_manager()

    # Map task type
    task_type_map = {
        "chat": A2ATaskType.CHAT,
        "completion": A2ATaskType.COMPLETION,
        "tool_call": A2ATaskType.TOOL_CALL
    }
    task_type = task_type_map.get(request.task_type, A2ATaskType.CHAT)

    # Create task
    task = await manager.create_task(
        agent_id=request.agent_id,
        messages=request.messages,
        task_type=task_type,
        caller_agent_id=key_info.user_id if key_info else None,
        metadata=request.metadata,
        timeout_seconds=request.timeout_seconds
    )

    # Execute immediately
    task = await manager.execute_task(task.task_id)

    return TaskResponse(
        task_id=task.task_id,
        agent_id=task.agent_id,
        task_type=task.task_type.value,
        status=task.status.value,
        progress=task.progress,
        output=task.output_message.content if task.output_message else None,
        error=task.error_message,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        metadata=task.metadata
    )


# Stats endpoint
@a2a_router.get("/stats")
async def get_a2a_stats():
    """Get A2A protocol statistics"""
    task_manager = get_a2a_task_manager()
    handshake_manager = get_handshake_manager()
    card_manager = get_agent_card_manager()

    return {
        "tasks": task_manager.get_stats(),
        "handshake": handshake_manager.get_stats(),
        "registered_agents": len(card_manager.list_cards())
    }


# ============== JSON-RPC 2.0 Integration ==============

# Import and include JSON-RPC router
try:
    from agent_platform.protocols.a2a.jsonrpc.router import jsonrpc_router
    a2a_router.include_router(jsonrpc_router)
except ImportError:
    # JSON-RPC module not available
    pass
