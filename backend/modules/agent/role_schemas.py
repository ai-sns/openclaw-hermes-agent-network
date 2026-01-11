# -*- coding: utf-8 -*-
"""Role configuration request/response schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class RoleConfigBase(BaseModel):
    """Role configuration base model."""
    name: str = Field(..., description="Role name")
    display_name: Optional[str] = None
    system_prompt: str = Field(..., description="System prompt")
    greeting_message: Optional[str] = None
    category: Optional[str] = Field(None, description="Category: developer|writer|analyst|assistant|other")
    avatar: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    is_active: bool = True
    is_default: bool = False


class RoleConfigCreate(RoleConfigBase):
    """Create role configuration."""
    pass


class RoleConfigUpdate(BaseModel):
    """Update role configuration."""
    name: Optional[str] = None
    display_name: Optional[str] = None
    system_prompt: Optional[str] = None
    greeting_message: Optional[str] = None
    category: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class RoleConfigResponse(RoleConfigBase):
    """Role configuration response."""
    id: int
    role_id: str
    role_type: str
    is_preset: bool
    position: int
    usage_count: int
    create_time: Optional[str] = None
    update_time: Optional[str] = None

    class Config:
        from_attributes = True
