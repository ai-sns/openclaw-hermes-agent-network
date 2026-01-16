# -*- coding: utf-8 -*-
"""
Chat module - API router
"""
import json
import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse

from .schemas import ChatRequest, StreamChatRequest, AiChatConfig
from .service import ChatService
from .streaming import StreamingService
from .dependencies import get_chat_service, get_streaming_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== AI Chat Config ====================

@router.get("/configs", response_model=dict)
async def get_ai_chat_configs(service: ChatService = Depends(get_chat_service)):
    """
    Get all AI chat configurations

    Returns:
        List of AI chat configurations
    """
    try:
        configs = service.get_all_ai_chat_configs()
        return {"success": True, "data": configs}
    except Exception as e:
        logger.error(f"Error getting AI chat configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs", response_model=dict)
async def create_ai_chat_config(
    config: AiChatConfig,
    service: ChatService = Depends(get_chat_service)
):
    """
    Create AI chat configuration

    Args:
        config: AI chat configuration

    Returns:
        Created configuration ID
    """
    try:
        config_id = service.create_ai_chat_config(**config.dict(exclude_unset=True))
        return {"success": True, "data": {"id": config_id}}
    except Exception as e:
        logger.error(f"Error creating AI chat config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chat ====================

@router.post("/", response_model=dict)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service)
):
    """
    Send chat message and get response

    Args:
        request: Chat request with agent_id and message

    Returns:
        Chat response
    """
    try:
        result = await service.send_chat_message(
            agent_id=request.agent_id,
            message=request.message,
            conversation_id=request.conversation_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{agent_id}", response_model=dict)
async def get_chat_history(
    agent_id: int,
    conversation_id: Optional[str] = None,
    service: ChatService = Depends(get_chat_service)
):
    """
    Get chat history

    Args:
        agent_id: Agent ID
        conversation_id: Optional conversation ID

    Returns:
        List of chat messages
    """
    try:
        messages = service.get_chat_history(agent_id, conversation_id)
        return {"success": True, "data": messages}
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=dict)
async def get_conversations(
    limit: int = 50,
    agent_id: Optional[int] = None,
    service: ChatService = Depends(get_chat_service)
):
    """
    Get conversation list (ordered by last message time)

    Args:
        limit: Maximum number of conversations to return
        agent_id: Filter by agent ID (optional)

    Returns:
        List of conversations
    """
    try:
        conversations = service.get_conversations(limit, agent_id)
        return {"success": True, "data": conversations}
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=dict)
async def get_conversation_messages(
    conversation_id: str,
    service: ChatService = Depends(get_chat_service)
):
    """
    Get all messages in a conversation

    Args:
        conversation_id: The conversation ID

    Returns:
        List of messages in chronological order
    """
    try:
        messages = service.get_conversation_messages(conversation_id)
        return {"success": True, "data": messages}
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def stream_chat_info():
    """
    Stream chat endpoint information (GET request)

    Returns:
        Information about how to use the streaming chat endpoint
    """
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


@router.post("/stream")
async def stream_chat(
    request: StreamChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    streaming_service: StreamingService = Depends(get_streaming_service)
):
    """
    Stream chat interface using SSE

    Args:
        request: Stream chat request with messages and optional model_config_id

    Returns:
        EventSourceResponse with streaming content
    """
    # If model_config_id is provided, fetch config from agent module
    if request.model_config_id:
        try:
            from backend.modules.agent.llm_service import LlmConfigService
            llm_service = LlmConfigService()
            model_config = llm_service.get_by_config_id(request.model_config_id)

            if not model_config:
                async def error_generator():
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": f"模型配置 ID {request.model_config_id} 不存在"
                        })
                    }
                return EventSourceResponse(error_generator())

            # Build ai_config from model_config
            ai_config = {
                'api_base': model_config.get('api_endpoint'),
                'api_key': model_config.get('api_key'),
                'model': model_config.get('model_name'),
                'temperature': model_config.get('temperature', 0.7),
                'max_tokens': model_config.get('max_tokens', 2048)
            }

            # Override with request parameters if provided
            model = request.model or ai_config['model']
            temperature = request.temperature if request.temperature is not None else ai_config['temperature']
            max_tokens = request.max_tokens or ai_config['max_tokens']

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error loading model config: {error_msg}")
            async def error_generator():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": f"加载模型配置失败: {error_msg}"
                    })
                }
            return EventSourceResponse(error_generator())
    else:
        # Use default ai_config.yaml configuration
        ai_config = chat_service.get_ai_config()

        # Check API key
        if not ai_config['api_key']:
            async def error_generator():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "API key 未配置。请在 ai_config.yaml 中配置 api_key"
                    })
                }
            return EventSourceResponse(error_generator())

        # Use request parameters or default values from config
        model = request.model or ai_config['model']
        temperature = request.temperature if request.temperature is not None else ai_config['temperature']
        max_tokens = request.max_tokens or ai_config['max_tokens']

    return EventSourceResponse(
        streaming_service.stream_chat(
            request.messages,
            ai_config,
            model,
            temperature,
            max_tokens,
            request.conversation_id  # Pass conversation_id
        )
    )


# ==================== Config Status ====================

@router.get("/status", response_model=dict)
async def config_status(service: ChatService = Depends(get_chat_service)):
    """
    Check AI configuration status

    Returns:
        Configuration status information
    """
    config = service.get_ai_config()
    has_api_key = bool(config.get('api_key'))

    return {
        "has_api_key": has_api_key,
        "api_base": config.get('api_base'),
        "model": config.get('model'),
        "api_key_preview": config.get('api_key', '')[:10] + "..." if has_api_key else "未配置",
        "config_file_exists": Path('ai_config.yaml').exists(),
        "recommendation": "配置正常" if has_api_key else "请在 ai_config.yaml 中配置 api_key"
    }
