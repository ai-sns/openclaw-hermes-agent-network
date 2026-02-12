import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.modules.skills_registry.service import DocSkillsService, get_docskills_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/list")
async def list_docskills(
    agent_id: Optional[int] = Query(None),
    eligible_only: bool = Query(False),
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        return {"success": True, "data": service.list_skills(agent_id=agent_id, eligible_only=eligible_only)}
    except Exception as e:
        logger.error(f"Error listing docskills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_docskill_info(
    skill_key: str,
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        info = service.get_skill(skill_key)
        if not info:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {"success": True, "data": info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting docskill info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read")
async def read_docskill_markdown(
    skill_key: str,
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        md = service.read_skill_markdown(skill_key)
        if md is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {"success": True, "data": {"skill_key": skill_key, "markdown": md}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading docskill markdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/edit")
async def update_docskill_markdown(
    payload: Dict[str, Any],
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        skill_key = payload.get("skill_key")
        markdown = payload.get("markdown")
        if not isinstance(skill_key, str) or not skill_key.strip():
            raise HTTPException(status_code=422, detail="skill_key is required")
        if not isinstance(markdown, str):
            raise HTTPException(status_code=422, detail="markdown must be a string")

        service.write_skill_markdown(skill_key.strip(), markdown)
        return {"success": True}
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating docskill markdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_docskill(
    skill_key: str,
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        service.delete_skill(skill_key)
        return {"success": True}
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting docskill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{skill_key}/run")
async def run_docskill(
    skill_key: str,
    params: Dict[str, Any] = {},
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        res = await service.run_skill(skill_key, params)
        return res
    except Exception as e:
        logger.error(f"Error running docskill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/{agent_id}/skills")
async def get_agent_docskills(
    agent_id: int,
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        return {"success": True, "data": service.get_agent_skill_keys(agent_id)}
    except Exception as e:
        logger.error(f"Error getting agent docskills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agent/{agent_id}/skills")
async def set_agent_docskills(
    agent_id: int,
    payload: Dict[str, Any],
    service: DocSkillsService = Depends(get_docskills_service),
):
    try:
        skill_keys = payload.get("skill_keys")
        if not isinstance(skill_keys, list):
            raise HTTPException(status_code=422, detail="skill_keys must be a list")
        service.set_agent_skill_keys(agent_id, skill_keys)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting agent docskills: {e}")
        raise HTTPException(status_code=500, detail=str(e))
