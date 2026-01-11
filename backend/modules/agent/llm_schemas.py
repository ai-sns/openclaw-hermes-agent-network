# -*- coding: utf-8 -*-
"""LLM configuration request/response schemas."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class LlmConfigBase(BaseModel):
    """LLM configuration base model."""
    name: str = Field(..., description="Display name")
    provider: str = Field(..., description="Provider: openai|claude|gemini|custom")
    plugin_id: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1)
    top_p: float = Field(default=1.0, ge=0, le=1)
    frequency_penalty: float = Field(default=0.0, ge=-2, le=2)
    presence_penalty: float = Field(default=0.0, ge=-2, le=2)
    stream: bool = True
    custom_params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False


class LlmConfigCreate(LlmConfigBase):
    """Create LLM configuration."""
    pass


class LlmConfigUpdate(BaseModel):
    """Update LLM configuration."""
    name: Optional[str] = None
    provider: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2)
    stream: Optional[bool] = None
    custom_params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class LlmConfigResponse(LlmConfigBase):
    """LLM configuration response."""
    id: int
    config_id: str
    position: int
    create_time: Optional[str] = None
    update_time: Optional[str] = None

    class Config:
        from_attributes = True


class LlmTestRequest(BaseModel):
    """Test LLM connection."""
    api_endpoint: str
    api_key: str
    model_name: str
    provider: str
