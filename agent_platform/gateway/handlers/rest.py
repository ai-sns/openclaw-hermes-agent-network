"""
REST API Handlers

Provides RESTful API endpoints for the platform.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from agent_platform.gateway.schemas.requests import (
    ChatRequest, ChatResponse, TaskRequest, TaskResponse,
    AgentInfo, AgentListResponse, APIResponse, PaginatedResponse,
    CreateSessionRequest, CreateSessionResponse, SessionInfo,
    CreateAPIKeyRequest, CreateAPIKeyResponse, APIKeyInfo
)
from agent_platform.gateway.middleware.auth import get_current_api_key, require_scope
from agent_platform.security.api_key import APIKeyInfo as APIKeyInfoInternal, get_api_key_manager
from agent_platform.session import get_session_manager, get_thread_manager


rest_router = APIRouter(prefix="/api/v1", tags=["API v1"])


# ============ Health & Info ============

@rest_router.get("/", response_model=APIResponse)
async def root():
    """API root - returns basic info"""
    return APIResponse(
        success=True,
        data={
            "name": "AI Agent Open Platform",
            "version": "1.0.0",
            "status": "online"
        }
    )


@rest_router.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint"""
    return APIResponse(
        success=True,
        data={"status": "healthy", "timestamp": datetime.now().isoformat()}
    )


# ============ Agent Endpoints ============

@rest_router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    key_info: APIKeyInfoInternal = Depends(require_scope("agent:read")),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """List all available agents"""
    # Import here to avoid circular imports
    from globals import global_agent_list
    from db.DBFactory import query_AgentCfg_All

    try:
        # Query agents from database
        agents_cfg = query_AgentCfg_All()
        agents = []

        for cfg in agents_cfg[skip:skip + limit]:
            agents.append(AgentInfo(
                id=cfg.user_id,
                name=cfg.name,
                description=cfg.memo,
                capabilities=["chat"],
                tools=cfg.plugins.split(",") if cfg.plugins else [],
                model=cfg.defaultmodel,
                is_active=cfg.is_show
            ))

        return AgentListResponse(agents=agents, total=len(agents_cfg))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rest_router.get("/agents/{agent_id}", response_model=APIResponse)
async def get_agent(
    agent_id: str,
    key_info: APIKeyInfoInternal = Depends(require_scope("agent:read"))
):
    """Get agent details"""
    from db.DBFactory import query_AgentCfg

    try:
        cfg = query_AgentCfg(user_id=agent_id)
        if not cfg:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent = AgentInfo(
            id=cfg.user_id,
            name=cfg.name,
            description=cfg.memo,
            capabilities=["chat"],
            tools=cfg.plugins.split(",") if cfg.plugins else [],
            model=cfg.defaultmodel,
            is_active=cfg.is_show
        )

        return APIResponse(success=True, data=agent.dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Chat Endpoints ============

@rest_router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    key_info: APIKeyInfoInternal = Depends(require_scope("chat:write"))
):
    """
    Synchronous chat endpoint.

    For streaming responses, use /chat/stream with SSE.
    """
    from globals import global_agent_list
    from db.DBFactory import query_AgentCfg

    try:
        # Get or create session
        session_manager = get_session_manager()

        if request.session_id:
            session = session_manager.get_session(request.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session = session_manager.create_session(
                user_id=key_info.user_id,
                agent_id=request.agent_id
            )

        # Get agent
        agent_key = f"agent_{request.agent_id}"
        if agent_key not in global_agent_list:
            # Try to load agent
            cfg = query_AgentCfg(user_id=request.agent_id)
            if not cfg:
                raise HTTPException(status_code=404, detail="Agent not found")

            from Agent import Agent
            agent = Agent(cfg)
            global_agent_list[agent_key] = agent
        else:
            agent = global_agent_list[agent_key]

        # Add user message to session
        session_manager.add_message(session.session_id, {
            "role": "user",
            "content": request.message
        })

        # Get response from agent
        import time
        start_time = time.time()

        # Build messages from history
        messages = session.messages if request.history is None else [
            {"role": m.role, "content": m.content} for m in request.history
        ]
        messages.append({"role": "user", "content": request.message})

        # Call agent
        response = agent.ask_it(
            request.message,
            messages,
            None,  # browser_page
            session.session_id  # task_id
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Add assistant message to session
        session_manager.add_message(session.session_id, {
            "role": "assistant",
            "content": response
        })

        return ChatResponse(
            message=response,
            session_id=session.session_id,
            thread_id=session.thread_id,
            latency_ms=latency_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Task Endpoints ============

@rest_router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    key_info: APIKeyInfoInternal = Depends(require_scope("task:create"))
):
    """Create an async task"""
    from agent_platform.async_tasks import get_task_queue

    try:
        task_queue = get_task_queue()
        task = await task_queue.enqueue(
            agent_id=request.agent_id,
            task_type=request.task_type,
            input_data=request.input_data,
            priority=request.priority,
            webhook_url=request.webhook_url,
            metadata=request.metadata
        )

        return TaskResponse(
            task_id=task.task_id,
            status=task.status,
            created_at=task.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rest_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    key_info: APIKeyInfoInternal = Depends(require_scope("task:read"))
):
    """Get task status"""
    from agent_platform.async_tasks import get_task_queue

    try:
        task_queue = get_task_queue()
        task = await task_queue.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse(
            task_id=task.task_id,
            status=task.status,
            output_data=task.output_data,
            error=task.error_message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            execution_time_ms=task.execution_time_ms
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Session Endpoints ============

@rest_router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    key_info: APIKeyInfoInternal = Depends(require_scope("session:write"))
):
    """Create a new session"""
    session_manager = get_session_manager()

    session = session_manager.create_session(
        user_id=key_info.user_id,
        agent_id=request.agent_id,
        context=request.context,
        expires_in_hours=request.expires_in_hours
    )

    return CreateSessionResponse(
        session_id=session.session_id,
        thread_id=session.thread_id,
        expires_at=session.expires_at,
        created_at=session.created_at
    )


@rest_router.get("/sessions/{session_id}", response_model=APIResponse)
async def get_session(
    session_id: str,
    key_info: APIKeyInfoInternal = Depends(require_scope("session:read"))
):
    """Get session details"""
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return APIResponse(
        success=True,
        data=SessionInfo(
            session_id=session.session_id,
            thread_id=session.thread_id,
            agent_id=session.agent_id,
            status=session.status,
            message_count=session.message_count,
            created_at=session.created_at,
            last_activity_at=session.last_activity_at,
            expires_at=session.expires_at
        ).dict()
    )


@rest_router.delete("/sessions/{session_id}", response_model=APIResponse)
async def close_session(
    session_id: str,
    key_info: APIKeyInfoInternal = Depends(require_scope("session:write"))
):
    """Close a session"""
    session_manager = get_session_manager()

    if session_manager.close_session(session_id):
        return APIResponse(success=True, data={"message": "Session closed"})
    else:
        raise HTTPException(status_code=404, detail="Session not found")


# ============ API Key Endpoints ============

@rest_router.post("/api-keys", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    key_info: APIKeyInfoInternal = Depends(require_scope("admin"))
):
    """Create a new API key (admin only)"""
    api_key_manager = get_api_key_manager()

    key = api_key_manager.generate_key(
        name=request.name,
        user_id=key_info.user_id,
        scopes=request.scopes,
        rate_limit=request.rate_limit,
        expires_in_days=request.expires_in_days
    )

    # Get key info (for the response)
    key_info_new = api_key_manager.validate_key(key)

    return CreateAPIKeyResponse(
        key=key,
        key_prefix=key_info_new.key_prefix,
        name=key_info_new.name,
        scopes=key_info_new.scopes,
        rate_limit=key_info_new.rate_limit,
        created_at=key_info_new.created_at,
        expires_at=key_info_new.expires_at
    )


@rest_router.get("/api-keys", response_model=APIResponse)
async def list_api_keys(
    key_info: APIKeyInfoInternal = Depends(require_scope("admin"))
):
    """List all API keys for the user"""
    api_key_manager = get_api_key_manager()
    keys = api_key_manager.list_keys(key_info.user_id)

    return APIResponse(
        success=True,
        data=[
            APIKeyInfo(
                key_prefix=k.key_prefix,
                name=k.name,
                scopes=k.scopes,
                rate_limit=k.rate_limit,
                is_active=k.is_active,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
                expires_at=k.expires_at
            ).dict() for k in keys
        ]
    )


@rest_router.delete("/api-keys/{key_prefix}", response_model=APIResponse)
async def revoke_api_key(
    key_prefix: str,
    key_info: APIKeyInfoInternal = Depends(require_scope("admin"))
):
    """Revoke an API key"""
    api_key_manager = get_api_key_manager()

    if api_key_manager.revoke_by_prefix(key_prefix):
        return APIResponse(success=True, data={"message": "API key revoked"})
    else:
        raise HTTPException(status_code=404, detail="API key not found")
