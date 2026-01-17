"""SNS Module - API Router"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from backend.config.database import get_db
from backend.modules.sns.service import SNSService
from backend.modules.sns.schemas import (
    UserStatsResponse,
    ContactResponse,
    ChatMessageResponse,
    SendMessageRequest,
    SendMessageResponse
)

router = APIRouter()


@router.get("/user-stats", response_model=UserStatsResponse)
async def get_user_stats(db: Session = Depends(get_db)):
    """Get user statistics"""
    service = SNSService(db)
    return service.get_user_stats()


@router.get("/contacts", response_model=List[ContactResponse])
async def get_contacts(db: Session = Depends(get_db)):
    """Get contact list from ai_friend table"""
    service = SNSService(db)
    return service.get_contacts()


@router.get("/chat-history/{account}", response_model=List[ChatMessageResponse])
async def get_chat_history(account: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get chat history with a specific contact"""
    service = SNSService(db)
    return service.get_chat_history(account, limit)


@router.post("/send-message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest, db: Session = Depends(get_db)):
    """Send a message via XMPP"""
    service = SNSService(db)
    return await service.send_message(request.to_account, request.content)


@router.post("/send-file")
async def send_file(
    to_account: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Send a file via XMPP"""
    service = SNSService(db)
    return await service.send_file(to_account, file)
