# -*- coding: utf-8 -*-
"""
System module - API router
"""
import asyncio
import logging
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import Response
from typing import List
import httpx

from .schemas import SystemConfig, WebMngReorderItem, SystemInitDraft, SystemInitSubmit, SystemInitTestLLM, SystemInitTestXMPP, SystemInitTestMap
from .service import SystemService, SystemInitWizardService
from .dependencies import get_system_service, get_system_init_wizard_service
from runtime.shared import debug_info

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_backend_logs_root() -> Path:
    return Path(__file__).resolve().parents[2] / 'logs'


def _validate_date_folder(date_str: str) -> str:
    s = str(date_str or '').strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise HTTPException(status_code=400, detail='Invalid date format')
    return s


def _validate_log_filename(name: str) -> str:
    s = str(name or '').strip()
    if not s:
        raise HTTPException(status_code=400, detail='Empty filename')
    if Path(s).name != s:
        raise HTTPException(status_code=400, detail='Invalid filename')
    if '..' in s or '/' in s or '\\' in s:
        raise HTTPException(status_code=400, detail='Invalid filename')
    return s


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


@router.get('/logs/dates', response_model=dict)
async def list_log_dates():
    try:
        root = _get_backend_logs_root()
        if not root.exists() or not root.is_dir():
            return {"success": True, "data": []}

        items = []
        for p in root.iterdir():
            if not p.is_dir():
                continue
            name = p.name
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", name):
                items.append(name)
        items.sort(reverse=True)
        return {"success": True, "data": items}
    except Exception as e:
        logger.error(f"Error listing log dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/logs/files', response_model=dict)
async def list_log_files(date: str):
    date = _validate_date_folder(date)
    root = _get_backend_logs_root()
    day_dir = (root / date).resolve()

    try:
        root_resolved = root.resolve()
        if root_resolved not in day_dir.parents and day_dir != root_resolved:
            raise HTTPException(status_code=400, detail='Invalid path')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid path')

    if not day_dir.exists() or not day_dir.is_dir():
        return {"success": True, "data": []}

    files = []
    for p in day_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() != '.ndjson':
            continue
        files.append(p.name)
    files.sort()
    return {"success": True, "data": files}


@router.get('/logs/file', response_model=dict)
async def read_log_file(date: str, name: str):
    date = _validate_date_folder(date)
    name = _validate_log_filename(name)

    root = _get_backend_logs_root()
    day_dir = (root / date).resolve()
    target = (day_dir / name).resolve()

    try:
        root_resolved = root.resolve()
        if root_resolved not in target.parents:
            raise HTTPException(status_code=400, detail='Invalid path')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid path')

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail='File not found')

    try:
        content = target.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True, "data": {"date": date, "name": name, "content": content}}


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
        record = service.get_draft()
        if not record or not record.get("avatar"):
            raise HTTPException(status_code=400, detail="Avatar not set")

        map_type = record.get("map") or ""
        has_map_api_key = bool(str(record.get("map_api_key") or "").strip())
        has_map_id = bool(str(record.get("map_id") or "").strip())
        logger.info(
            "Init-wizard submit: map_type=%s, has_map_api_key=%s, has_map_id=%s",
            map_type,
            has_map_api_key,
            has_map_id,
        )

        avatar_map_filename = service._generate_avatar_map(record["avatar"])

        register_data = {
            "nation_id": "",
            "password": record.get("password", ""),
            "account": record.get("account", ""),
            "longitude": payload.longitude if payload.longitude is not None else -121.88947550295555,
            "latitude": payload.latitude if payload.latitude is not None else 37.33200027587634,
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
        service.submit(record, nation_id)

        # The XMPP client was skipped at startup because no account/password
        # existed yet. Now that the init wizard has saved credentials to
        # aisns_cfg, schedule a hot restart so SNS features (roster sync,
        # messaging) come up without requiring a full backend restart. This
        # mirrors the hot-reload behaviour in SNSService.update_ai_chat_config.
        try:
            from runtime.apps.sns.xmpp_client import XMPPClientManager
            asyncio.create_task(XMPPClientManager.get_instance().restart())
            logger.info("XMPP restart scheduled after init wizard submit")
        except Exception as _xe:
            logger.warning("Failed to schedule XMPP restart after init wizard submit: %s", _xe)

        return {"success": True, "data": remote_res}
    except httpx.HTTPStatusError as e:
        status_code = getattr(e.response, 'status_code', 502) if getattr(e, 'response', None) is not None else 502
        detail = "Remote register failed"
        try:
            if getattr(e, 'response', None) is not None:
                detail = e.response.text
        except Exception:
            detail = str(e)
        raise HTTPException(status_code=status_code, detail=detail)
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
