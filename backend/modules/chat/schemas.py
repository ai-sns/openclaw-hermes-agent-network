# -*- coding: utf-8 -*-
"""
Chat module - Pydantic schemas
"""
from typing import Optional, List, Dict
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    agent_id: int
    message: str
    conversation_id: Optional[str] = None


class StreamChatRequest(BaseModel):
    """Stream chat request model"""
    messages: List[Dict[str, str]]
    conversation_id: Optional[str] = None  # Conversation ID for message history
    model_config_id: Optional[str] = None  # LLM configuration ID from agent module
    model: Optional[str] = None
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = 4096


class AiChatConfig(BaseModel):
    """AI chat configuration model"""
    id: Optional[int] = None
    name: str
    api_base: Optional[str] = ""
    api_key: Optional[str] = ""
    model: Optional[str] = "gpt-4"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    is_delete: Optional[int] = 0
