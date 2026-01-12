# -*- coding: utf-8 -*-
"""
Agent Chat Router - Agent问答API接口
支持流式和非流式问答，按ID或名称调用Agent
"""
import logging
import json
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agent_manager import agent_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class AgentChatRequest(BaseModel):
    """Agent问答请求"""
    message: str
    conversation_id: Optional[str] = None
    use_memory: bool = True
    use_knowledge_base: bool = True


class AgentChatResponse(BaseModel):
    """Agent问答响应"""
    success: bool
    reply: Optional[str] = None
    conversation_id: Optional[str] = None
    error: Optional[str] = None


# ==================== Agent Chat Endpoints ====================

@router.post("/{agent_id}/chat", response_model=dict)
async def agent_chat_by_id(
    agent_id: int,
    request: AgentChatRequest
):
    """
    Agent非流式问答（按ID）

    Args:
        agent_id: Agent ID
        request: 问答请求

    Returns:
        问答响应
    """
    try:
        # 获取Agent实例
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # 调用agent问答
        reply = await agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            use_memory=request.use_memory,
            use_knowledge_base=request.use_knowledge_base
        )

        return {
            "success": True,
            "data": {
                "reply": reply,
                "conversation_id": request.conversation_id or "default",
                "agent_id": agent_id,
                "agent_name": agent.name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/chat/stream")
async def agent_chat_stream_by_id(
    agent_id: int,
    request: AgentChatRequest
):
    """
    Agent流式问答（按ID）- 使用SSE

    Args:
        agent_id: Agent ID
        request: 问答请求

    Returns:
        SSE流式响应
    """
    try:
        # 获取Agent实例
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        async def generate():
            """SSE生成器"""
            try:
                async for chunk in agent.chat_stream(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    use_memory=request.use_memory,
                    use_knowledge_base=request.use_knowledge_base
                ):
                    # SSE格式
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                # 发送完成信号
                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent流式问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/name/{agent_name}/chat", response_model=dict)
async def agent_chat_by_name(
    agent_name: str,
    request: AgentChatRequest
):
    """
    Agent非流式问答（按名称）

    Args:
        agent_name: Agent名称
        request: 问答请求

    Returns:
        问答响应
    """
    try:
        # 获取Agent实例
        agent = agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # 调用agent问答
        reply = await agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            use_memory=request.use_memory,
            use_knowledge_base=request.use_knowledge_base
        )

        return {
            "success": True,
            "data": {
                "reply": reply,
                "conversation_id": request.conversation_id or "default",
                "agent_id": agent.agent_id,
                "agent_name": agent.name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/name/{agent_name}/chat/stream")
async def agent_chat_stream_by_name(
    agent_name: str,
    request: AgentChatRequest
):
    """
    Agent流式问答（按名称）- 使用SSE

    Args:
        agent_name: Agent名称
        request: 问答请求

    Returns:
        SSE流式响应
    """
    try:
        # 获取Agent实例
        agent = agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        async def generate():
            """SSE生成器"""
            try:
                async for chunk in agent.chat_stream(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    use_memory=request.use_memory,
                    use_knowledge_base=request.use_knowledge_base
                ):
                    # SSE格式
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                # 发送完成信号
                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent流式问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Memory Management ====================

@router.delete("/{agent_id}/memory")
async def clear_agent_memory(
    agent_id: int,
    conversation_id: Optional[str] = None
):
    """
    清除Agent的对话记忆

    Args:
        agent_id: Agent ID
        conversation_id: 对话ID，如果为None则清除所有

    Returns:
        成功状态
    """
    try:
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        agent.clear_memory(conversation_id)

        return {
            "success": True,
            "message": f"Memory cleared for agent {agent_id}" + (f" conversation {conversation_id}" if conversation_id else " (all conversations)")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/memory")
async def get_agent_memory(
    agent_id: int,
    conversation_id: Optional[str] = None
):
    """
    获取Agent的对话记忆

    Args:
        agent_id: Agent ID
        conversation_id: 对话ID

    Returns:
        对话历史
    """
    try:
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        memory = agent._get_conversation_memory(conversation_id)

        return {
            "success": True,
            "data": {
                "conversation_id": conversation_id or "default",
                "messages": memory
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Instance Management ====================

@router.get("/{agent_id}/info")
async def get_agent_info(agent_id: int):
    """
    获取Agent实例信息

    Args:
        agent_id: Agent ID

    Returns:
        Agent信息
    """
    try:
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {
            "success": True,
            "data": agent.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/reload")
async def reload_agent(agent_id: int):
    """
    重新加载Agent（刷新配置）

    Args:
        agent_id: Agent ID

    Returns:
        成功状态
    """
    try:
        agent = agent_manager.reload_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {
            "success": True,
            "message": f"Agent {agent_id} reloaded",
            "data": agent.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新加载Agent失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cached")
async def get_cached_agents():
    """
    获取所有已缓存的Agent

    Returns:
        缓存的Agent列表
    """
    try:
        agents = agent_manager.get_all_cached_agents()

        return {
            "success": True,
            "data": [agent.to_dict() for agent in agents]
        }

    except Exception as e:
        logger.error(f"获取缓存Agent失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
