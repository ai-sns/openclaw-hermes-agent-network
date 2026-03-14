"""SNS Module - API Router - Async version."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend.config.database import get_db
from backend.apps.sns.service_async import SNSService
from backend.apps.sns.schemas import (
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
    SocialRoleItem,
    SocialRoleUpdateRequest,
    HumanControlStateRequest,
    HumanMessageRequest,
    AgentInstructionRequest,
    EndActiveConversationRequest,
    PromptByTitleUpdateRequest
)

from backend.apps.sns.memory.router import router as memory_router

router = APIRouter()

router.include_router(memory_router, tags=["Memory"])


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
    from backend.apps.sns.ai_service import SNSAIService

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



@router.post("/pause-engine")
async def pause_social_engine(db: AsyncSession = Depends(get_db)):
    """Pause the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.pause_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to pause social engine: {str(e)}"
        }


@router.post("/resume-engine")
async def resume_social_engine(db: AsyncSession = Depends(get_db)):
    """Resume the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.resume_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to resume social engine: {str(e)}"
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


@router.post("/restart-engine")
async def restart_social_engine(db: AsyncSession = Depends(get_db)):
    """Restart the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.restart_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to restart social engine: {str(e)}"
        }


@router.get("/engine-status")
async def get_social_engine_status(db: AsyncSession = Depends(get_db)):
    """Get the current AI social engine status"""
    try:
        service = SNSService(db)
        result = await service.get_social_engine_status()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get social engine status: {str(e)}",
            "running": False,
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


@router.post("/avatar-dialog/upload-avatar")
async def upload_avatar_dialog(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload avatar for SNS avatar dialog and generate composed avatar map image."""
    service = SNSService(db)
    return await service.upload_avatar_dialog(file)


@router.post("/avatar-dialog/submit")
async def submit_avatar_dialog(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Submit avatar/profile updates and forward to remote server."""
    service = SNSService(db)
    return await service.submit_avatar_dialog(request)


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
        ProfessionItem(
            name="Doctor",
            cost=800,
            description="Setup fee: 800",
            service_description="Remote medical consultation",
            service_price="200",
        ),
        ProfessionItem(
            name="Restaurateur",
            cost=800,
            description="Setup fee: 800",
            service_description="Meal delivery service",
            service_price="20",
        ),
        ProfessionItem(name="Singer", cost=None, description=""),
        ProfessionItem(name="Painter", cost=None, description=""),
        ProfessionItem(name="Designer", cost=None, description=""),
        ProfessionItem(name="Programmer", cost=None, description=""),
        ProfessionItem(name="Teacher", cost=None, description=""),
        ProfessionItem(name="Other", cost=None, description=""),
    ]
    return professions


@router.get("/social-roles", response_model=List[SocialRoleItem])
async def get_social_roles(db: AsyncSession = Depends(get_db)):
    """Get social roles (prompts with SNS tag)"""
    service = SNSService(db)
    return await service.get_social_roles()


@router.get("/social-roles/{role_id}", response_model=SocialRoleItem)
async def get_social_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific social role by ID"""
    service = SNSService(db)
    role = await service.get_social_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Social role not found")
    return role


@router.put("/social-roles/{role_id}")
async def update_social_role(
    role_id: int,
    request: SocialRoleUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a social role"""
    service = SNSService(db)
    result = await service.update_social_role(role_id, request.dict(exclude_unset=True))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/prompts/by-title/{title}")
async def get_prompt_by_title(
    title: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a prompt record by its title."""
    service = SNSService(db)
    result = await service.get_prompt_by_title(title)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or "Prompt not found")
    return result


@router.put("/prompts/by-title/{title}")
async def upsert_prompt_by_title(
    title: str,
    request: PromptByTitleUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a prompt content by its title."""
    service = SNSService(db)
    result = await service.upsert_prompt_content_by_title(title, request.content)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.delete("/social-roles/{role_id}")
async def delete_social_role(
    role_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a social role"""
    service = SNSService(db)
    result = await service.delete_social_role(role_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


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


@router.post("/change-nationpassword")
async def change_nationpassword(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.change_nationpassword(request)


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


@router.get("/model-info")
async def get_model_info(db: AsyncSession = Depends(get_db)):
    """
    Get AI model information from aichat_cfg, agent_cfg, and llm_config

    Returns:
        Model information including provider, model name, and agent name
    """
    service = SNSService(db)
    return await service.get_model_info()


@router.get("/resource-overview")
async def get_resource_overview(db: AsyncSession = Depends(get_db)):
    """Get Resource tab overview content"""
    service = SNSService(db)
    return await service.get_resource_overview()


@router.get("/current-status-overview")
async def get_current_status_overview(db: AsyncSession = Depends(get_db)):
    """Get Current Status overview content"""
    service = SNSService(db)
    return await service.get_current_status_overview()


@router.post("/human-control-state")
async def set_human_control_state(
    request: HumanControlStateRequest,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.set_human_control_state(
        human_take_over=request.human_take_over,
        human_talk_type=request.human_talk_type
    )


@router.post("/human-message")
async def send_human_message(
    request: HumanMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.send_human_message(request.message)


@router.post("/agent-instruction")
async def submit_agent_instruction(
    request: AgentInstructionRequest,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.submit_agent_instruction(request.instruction)


@router.post("/end-active-conversation")
async def end_active_conversation(
    request: EndActiveConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    service = SNSService(db)
    return await service.end_active_conversation(
        reason=request.reason,
        message=request.message or "",
        resume_activity=bool(request.resume_activity),
    )

