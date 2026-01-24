"""SNS Module - API Router - 异步版本"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend.config.database import get_db
from backend.modules.sns.service_async import SNSService
from backend.modules.sns.schemas import (
    UserStatsResponse,
    ContactResponse,
    ChatMessageResponse,
    SendMessageRequest,
    SendMessageResponse,
    AIChatRequest,
    AIChatResponse,
    AIChatConfigResponse,
    AIChatConfigUpdateRequest,
    Avatar3DItem,
    ProfessionItem,
    SocialRoleItem
)

router = APIRouter()


@router.get("/user-stats", response_model=UserStatsResponse)
async def get_user_stats(db: AsyncSession = Depends(get_db)):
    """Get user statistics"""
    service = SNSService(db)
    return await service.get_user_stats()


@router.get("/contacts", response_model=List[ContactResponse])
async def get_contacts(db: AsyncSession = Depends(get_db)):
    """Get contact list from ai_friend table"""
    service = SNSService(db)
    return await service.get_contacts()


@router.get("/chat-history/{account}", response_model=List[ChatMessageResponse])
async def get_chat_history(account: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get chat history with a specific contact"""
    service = SNSService(db)
    return await service.get_chat_history(account, limit)


@router.post("/send-message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """Send a message via XMPP"""
    service = SNSService(db)
    return await service.send_message(request.to_account, request.content)


@router.post("/send-file")
async def send_file(
    to_account: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Send a file via XMPP"""
    service = SNSService(db)
    return await service.send_file(to_account, file)


@router.post("/ai-chat", response_model=AIChatResponse)
async def ai_chat(request: AIChatRequest):
    """Chat with AI agent"""
    from backend.modules.sns.ai_service import SNSAIService

    try:
        reply = await SNSAIService.chat_with_agent(
            agent_identifier=request.agent_identifier,
            message=request.message,
            mode=request.mode
        )

        if reply.startswith("Error:"):
            return AIChatResponse(success=False, reply="", error=reply)

        return AIChatResponse(success=True, reply=reply)
    except Exception as e:
        return AIChatResponse(success=False, reply="", error=str(e))


@router.post("/start-engine")
async def start_social_engine(db: AsyncSession = Depends(get_db)):
    """Start the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.start_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to start social engine: {str(e)}"
        }


@router.post("/stop-engine")
async def stop_social_engine(db: AsyncSession = Depends(get_db)):
    """Stop the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.stop_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to stop social engine: {str(e)}"
        }


@router.get("/config", response_model=AIChatConfigResponse)
async def get_ai_chat_config(user_id: str = None, db: AsyncSession = Depends(get_db)):
    """Get AI chat configuration"""
    service = SNSService(db)
    return await service.get_ai_chat_config(user_id)


@router.put("/config")
async def update_ai_chat_config(
    request: AIChatConfigUpdateRequest,
    user_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Update AI chat configuration"""
    service = SNSService(db)
    return await service.update_ai_chat_config(user_id, request.dict(exclude_unset=True))


@router.post("/config/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload avatar image"""
    service = SNSService(db)
    return await service.upload_avatar(user_id, file)


@router.get("/avatars3d", response_model=List[Avatar3DItem])
async def get_avatars_3d():
    """Get list of available 3D avatars"""
    import os
    import glob

    avatar_dir = "scripts/avatar3d"
    avatars = []

    png_files = glob.glob(os.path.join(avatar_dir, "*.png"))
    for png_file in sorted(png_files):
        basename = os.path.basename(png_file)
        name = os.path.splitext(basename)[0]
        glb_file = os.path.join(avatar_dir, f"{name}.glb")

        if os.path.exists(glb_file):
            avatars.append(Avatar3DItem(
                name=name,
                preview_url=f"/scripts/avatar3d/{basename}",
                model_url=f"/scripts/avatar3d/{name}.glb"
            ))

    return avatars


@router.get("/professions", response_model=List[ProfessionItem])
async def get_professions():
    """Get list of available professions"""
    professions = [
        ProfessionItem(name="医生", cost=800, description="需要800元开办费"),
        ProfessionItem(name="出租车司机", cost=1000, description="需要1000元开办费"),
        ProfessionItem(name="食品商贩", cost=800, description="需要800元开办费"),
        ProfessionItem(name="歌手", cost=None, description=""),
        ProfessionItem(name="国家公务员", cost=None, description=""),
        ProfessionItem(name="美工设计", cost=None, description=""),
        ProfessionItem(name="程序员", cost=None, description=""),
        ProfessionItem(name="教师", cost=None, description=""),
    ]
    return professions


@router.get("/social-roles", response_model=List[SocialRoleItem])
async def get_social_roles(db: AsyncSession = Depends(get_db)):
    """Get social roles (prompts with SNS tag)"""
    service = SNSService(db)
    return await service.get_social_roles()


@router.get("/user-info")
async def get_user_info(db: AsyncSession = Depends(get_db)):
    """Get user information from aichat_cfg"""
    service = SNSService(db)
    return await service.get_user_info()


@router.put("/user-info")
async def update_user_info(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update user information in aichat_cfg"""
    service = SNSService(db)
    return await service.update_user_info(request)


@router.get("/map-config")
async def get_map_config(db: AsyncSession = Depends(get_db)):
    """Get map configuration"""
    service = SNSService(db)
    return await service.get_map_config()


@router.put("/map-config")
async def update_map_config(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update map configuration"""
    service = SNSService(db)
    return await service.update_map_config(request)

