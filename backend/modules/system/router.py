# -*- coding: utf-8 -*-
"""
System module - API router
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import Response
from typing import List

from .schemas import SystemConfig, WebMngReorderItem, SystemInitDraft, SystemInitSubmit, SystemInitTestLLM, SystemInitTestXMPP, SystemInitTestMap
from .service import SystemService, SystemInitWizardService
from .dependencies import get_system_service, get_system_init_wizard_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config", response_model=dict)
async def get_system_config(service: SystemService = Depends(get_system_service)):
    """
    Get system configuration

    Returns:
        System configuration
    """
    try:
        config = service.get_system_config()
        return {"success": True, "data": config}
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=dict)
async def update_system_config(
    config: SystemConfig,
    service: SystemService = Depends(get_system_service)
):
    """
    Update system configuration

    Args:
        config: Updated system configuration

    Returns:
        Success status
    """
    try:
        service.update_system_config(**config.dict(exclude_unset=True))
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/web-mng", response_model=dict)
async def get_web_mng(service: SystemService = Depends(get_system_service)):
    """
    Get web management data (LLM and Tools)

    Returns:
        List of web management items
    """
    try:
        data = service.get_web_mng()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error getting web-mng data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-mng", response_model=dict)
async def create_web_mng(
    item: dict,
    service: SystemService = Depends(get_system_service)
):
    """
    Create new web management item

    Args:
        item: Web management item data

    Returns:
        Created item
    """
    try:
        result = service.create_web_mng(item)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error creating web-mng item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/web-mng/reorder", response_model=dict)
async def reorder_web_mng(
    request: Request,
    service: SystemService = Depends(get_system_service)
):
    """
    Reorder web management items
    
    IMPORTANT: This route must be defined BEFORE /web-mng/{item_id}
    to avoid FastAPI matching 'reorder' as an item_id

    Args:
        request: Request body containing list of items with id and position

    Returns:
        Success status
    """
    try:
        items = await request.json()
        logger.info(f"Received reorder request: {items}")
        logger.info(f"Items type: {type(items)}")
        
        # Validate items
        if not isinstance(items, list):
            error_msg = f"Expected a list of items, got {type(items).__name__}"
            logger.error(error_msg)
            raise HTTPException(status_code=422, detail=error_msg)
        
        if len(items) == 0:
            logger.warning("Empty items list received")
            return {"success": True}
        
        for idx, item in enumerate(items):
            logger.info(f"Item {idx}: {item} (type: {type(item).__name__})")
            if not isinstance(item, dict):
                error_msg = f"Item {idx} is not a dict, got {type(item).__name__}"
                logger.error(error_msg)
                raise HTTPException(status_code=422, detail=error_msg)
            if 'id' not in item:
                error_msg = f"Item {idx} missing 'id' field. Keys: {list(item.keys())}"
                logger.error(error_msg)
                raise HTTPException(status_code=422, detail=error_msg)
            if 'position' not in item:
                error_msg = f"Item {idx} missing 'position' field. Keys: {list(item.keys())}"
                logger.error(error_msg)
                raise HTTPException(status_code=422, detail=error_msg)
        
        service.reorder_web_mng(items)
        logger.info("Reorder completed successfully")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering web-mng items: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/web-mng/{item_id}", response_model=dict)
async def update_web_mng(
    item_id: int,
    item: dict,
    service: SystemService = Depends(get_system_service)
):
    """
    Update web management item

    Args:
        item_id: Item ID
        item: Updated item data

    Returns:
        Updated item
    """
    try:
        result = service.update_web_mng(item_id, item)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error updating web-mng item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/web-mng/{item_id}", response_model=dict)
async def delete_web_mng(
    item_id: int,
    service: SystemService = Depends(get_system_service)
):
    """
    Delete web management item (soft delete)

    Args:
        item_id: Item ID

    Returns:
        Success status
    """
    try:
        service.delete_web_mng(item_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting web-mng item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/init-wizard/draft", response_model=dict)
async def get_system_init_draft(service: SystemInitWizardService = Depends(get_system_init_wizard_service)):
    try:
        data = service.get_draft()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error getting system init draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/init-wizard/draft", response_model=dict)
async def save_system_init_draft(
    payload: SystemInitDraft,
    service: SystemInitWizardService = Depends(get_system_init_wizard_service)
):
    try:
        res = service.save_draft(payload.dict(exclude_unset=True))
        return {"success": True, "data": res}
    except Exception as e:
        logger.error(f"Error saving system init draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/init-wizard/avatar3d", response_model=dict)
async def list_avatar3d(
    request: Request,
    service: SystemInitWizardService = Depends(get_system_init_wizard_service)
):
    try:
        items = service.list_avatar3d(str(request.base_url))
        return {"success": True, "data": items}
    except Exception as e:
        logger.error(f"Error listing avatar3d: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-wizard/avatar", response_model=dict)
async def upload_avatar(
    avatar_file: UploadFile = File(...),
    service: SystemInitWizardService = Depends(get_system_init_wizard_service)
):
    try:
        content = await avatar_file.read()
        ext = ""
        if avatar_file.filename and "." in avatar_file.filename:
            ext = "." + avatar_file.filename.split(".")[-1]

        res = service.upload_avatar(content, ext)
        return {"success": True, "data": res}
    except Exception as e:
        logger.error(f"Error uploading avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/init-wizard/captcha")
async def get_captcha_proxy(service: SystemInitWizardService = Depends(get_system_init_wizard_service)):
    try:
        data = await service.fetch_captcha()
        headers = {"X-Captcha-ID": data.get("captcha_id", "")}
        return Response(content=data.get("content", b""), media_type=data.get("content_type", "image/png"), headers=headers)
    except Exception as e:
        logger.error(f"Error fetching captcha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-wizard/submit", response_model=dict)
async def submit_system_init(
    payload: SystemInitSubmit,
    service: SystemInitWizardService = Depends(get_system_init_wizard_service)
):
    try:
        draft = payload.dict(exclude_unset=True)
        service.save_draft(draft)

        record = service.get_draft()
        if not record or not record.get("avatar"):
            raise HTTPException(status_code=400, detail="Avatar not set")

        avatar_map_filename = service._generate_avatar_map(record["avatar"])

        register_data = {
            "nation_id": "",
            "password": record.get("password", ""),
            "account": record.get("account", ""),
            "longitude": payload.longitude if payload.longitude is not None else 116.27882,
            "latitude": payload.latitude if payload.latitude is not None else 39.71164,
            "captcha_id": payload.captcha_id,
            "captcha_code": payload.captcha_code,
            "nick_name": record.get("name", ""),
            "avatar": record.get("avatar", ""),
            "avatar_3d": record.get("avatar3d", ""),
            "profile": record.get("profile", ""),
            "sns_url": record.get("sns_url", ""),
            "status": 1,
        }

        remote_res = await service.register_remote(register_data, avatar_map_filename)
        nation_id = remote_res.get("nation_id") or remote_res.get("nationId") or remote_res.get("nationid") or ""
        service.submit(draft, nation_id)
        return {"success": True, "data": remote_res}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting system init: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-wizard/test-llm", response_model=dict)
async def test_llm_config(
    payload: SystemInitTestLLM,
    service: SystemInitWizardService = Depends(get_system_init_wizard_service)
):
    try:
        res = await service.test_llm(payload.llm or "", payload.llm_server or "", payload.api_key or "")
        return res
    except Exception as e:
        logger.error(f"Error testing llm config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-wizard/test-xmpp", response_model=dict)
async def test_xmpp_config(
    payload: SystemInitTestXMPP,
    service: SystemInitWizardService = Depends(get_system_init_wizard_service)
):
    try:
        res = await service.test_xmpp(payload.account or "", payload.account_password or "")
        return res
    except Exception as e:
        logger.error(f"Error testing xmpp config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-wizard/test-map", response_model=dict)
async def test_map_config(
    payload: SystemInitTestMap,
    service: SystemInitWizardService = Depends(get_system_init_wizard_service)
):
    try:
        res = await service.test_map(payload.map or "", payload.map_api_key or "", payload.map_id or "")
        return res
    except Exception as e:
        logger.error(f"Error testing map config: {e}")
        raise HTTPException(status_code=500, detail=str(e))