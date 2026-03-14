# -*- coding: utf-8 -*-
"""
System module - Pydantic schemas
"""
from typing import Optional, List
from pydantic import BaseModel


class SystemConfig(BaseModel):
    """System configuration model"""
    theme: Optional[str] = "dark"
    language: Optional[str] = "zh"
    minirunontray: Optional[bool] = True
    agent_server: Optional[str] = None
    ai_sns_server: Optional[str] = None
    conversation_timeout_seconds: Optional[int] = None
    contact_cooldown_seconds: Optional[int] = None
    contact_recent_limit: Optional[int] = None
    process_info_compact_every_n: Optional[int] = None
    process_info_plan_summary_every_n: Optional[int] = None
    memory_enabled: Optional[bool] = None
    memory_embedding_enabled: Optional[bool] = None


class WebMngReorderItem(BaseModel):
    """Web management reorder item"""
    id: int
    position: int


class WebMngReorderRequest(BaseModel):
    """Web management reorder request"""
    items: List[WebMngReorderItem]


class Avatar3DItem(BaseModel):
    key: str
    png_url: str
    glb_url: str


class SystemInitDraft(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    profile: Optional[str] = None
    llm: Optional[str] = None
    llm_server: Optional[str] = None
    api_key: Optional[str] = None
    avatar3d: Optional[str] = None
    account: Optional[str] = None
    account_password: Optional[str] = None
    sns_url: Optional[str] = None
    map: Optional[str] = None
    map_api_key: Optional[str] = None
    map_id: Optional[str] = None


class SystemInitSubmit(SystemInitDraft):
    captcha_id: str
    captcha_code: str

    longitude: Optional[float] = None
    latitude: Optional[float] = None


class SystemInitTestLLM(BaseModel):
    llm: Optional[str] = None
    llm_server: Optional[str] = None
    api_key: Optional[str] = None


class SystemInitTestXMPP(BaseModel):
    account: Optional[str] = None
    account_password: Optional[str] = None


class SystemInitTestMap(BaseModel):
    map: Optional[str] = None
    map_api_key: Optional[str] = None
    map_id: Optional[str] = None
