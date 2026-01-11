# -*- coding: utf-8 -*-
"""LLM configuration API router."""
from typing import List
from fastapi import APIRouter, HTTPException, Query
from .llm_schemas import (
    LlmConfigCreate, LlmConfigUpdate, LlmConfigResponse, LlmTestRequest
)
from .llm_service import LlmConfigService

router = APIRouter(prefix="/llm-configs", tags=["LLM Configuration"])


@router.get("", response_model=dict)
async def get_llm_configs(
    active_only: bool = Query(True, description="Only return active configurations")
):
    """Get all LLM configurations."""
    try:
        service = LlmConfigService()
        configs = service.get_all(active_only=active_only)
        return {"success": True, "data": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{config_id}", response_model=dict)
async def get_llm_config(config_id: str):
    """Get LLM configuration by ID."""
    try:
        service = LlmConfigService()
        config = service.get_by_config_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return {"success": True, "data": config}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict)
async def create_llm_config(config: LlmConfigCreate):
    """Create new LLM configuration."""
    try:
        service = LlmConfigService()
        config_id = service.create(config)
        return {"success": True, "data": {"config_id": config_id}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{config_id}", response_model=dict)
async def update_llm_config(config_id: str, config: LlmConfigUpdate):
    """Update LLM configuration."""
    try:
        service = LlmConfigService()
        service.update(config_id, config)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{config_id}", response_model=dict)
async def delete_llm_config(config_id: str):
    """Delete LLM configuration (soft delete)."""
    try:
        service = LlmConfigService()
        service.delete(config_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=dict)
async def test_llm_connection(test_data: LlmTestRequest):
    """Test LLM connection."""
    try:
        service = LlmConfigService()
        result = await service.test_connection(test_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/import", response_model=dict)
async def import_llm_configs(configs: List[LlmConfigCreate]):
    """Import multiple LLM configurations."""
    try:
        service = LlmConfigService()
        result = service.import_configs(configs)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/all", response_model=dict)
async def export_llm_configs():
    """Export all LLM configurations."""
    try:
        service = LlmConfigService()
        configs = service.export_all()
        return {"success": True, "data": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
