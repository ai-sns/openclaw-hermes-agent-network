"""SNS Module - Pydantic Schemas"""
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class UserStatsResponse(BaseModel):
    level: int
    credit: int
    money: float
    life: int
    iq: int
    energy: int
    move: float
    exp: int


class ContactResponse(BaseModel):
    id: int
    account: str
    nick_name: str
    groups: Optional[str] = None
    subscription: Optional[str] = None
    new_message_flag: bool = False
    last_message_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: Optional[str] = None
    flag: int  # 0=send, 1=receive
    content: str
    create_time: datetime
    owner_account: Optional[str] = None
    friend_account: Optional[str] = None

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    to_account: str
    content: str


class SendMessageResponse(BaseModel):
    success: bool
    message: str = "Message sent successfully"


class AIChatRequest(BaseModel):
    agent_identifier: str
    message: str
    mode: str = "ai"  # "ai" or "friends"


class AIChatResponse(BaseModel):
    success: bool
    reply: str
    error: Optional[str] = None


class AIChatConfigResponse(BaseModel):
    id: int
    user_id: Optional[str] = None
    account: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    avatar3d: Optional[str] = None
    profession: Optional[str] = None

    class Config:
        from_attributes = True


class AIChatConfigUpdateRequest(BaseModel):
    user_id: Optional[str] = None
    account: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    avatar3d: Optional[str] = None
    profession: Optional[str] = None


class Avatar3DItem(BaseModel):
    name: str
    preview_url: str
    model_url: str


class ProfessionItem(BaseModel):
    name: str
    cost: Optional[int] = None
    description: Optional[str] = None


class SocialRoleItem(BaseModel):
    id: int
    title: str
    content: str
    tags: Optional[str] = None

    class Config:
        from_attributes = True
