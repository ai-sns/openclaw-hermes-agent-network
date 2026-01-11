# -*- coding: utf-8 -*-
"""Role configuration API router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from .role_schemas import RoleConfigCreate, RoleConfigUpdate, RoleConfigResponse
from .role_service import RoleConfigService

router = APIRouter(prefix="/role-configs", tags=["Role Configuration"])


@router.get("", response_model=dict)
async def get_role_configs(
    active_only: bool = Query(True, description="Only return active configurations"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Get all role configurations."""
    try:
        service = RoleConfigService()
        configs = service.get_all(active_only=active_only, category=category)
        return {"success": True, "data": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets", response_model=dict)
async def get_preset_roles():
    """Get preset role templates."""
    try:
        service = RoleConfigService()
        presets = service.get_presets()
        return {"success": True, "data": presets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{role_id}", response_model=dict)
async def get_role_config(role_id: str):
    """Get role configuration by ID."""
    try:
        service = RoleConfigService()
        config = service.get_by_role_id(role_id)
        if not config:
            raise HTTPException(status_code=404, detail="Role not found")
        return {"success": True, "data": config}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict)
async def create_role_config(config: RoleConfigCreate):
    """Create new role configuration."""
    try:
        service = RoleConfigService()
        role_id = service.create(config)
        return {"success": True, "data": {"role_id": role_id}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{role_id}", response_model=dict)
async def update_role_config(role_id: str, config: RoleConfigUpdate):
    """Update role configuration."""
    try:
        service = RoleConfigService()
        service.update(role_id, config)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{role_id}", response_model=dict)
async def delete_role_config(role_id: str):
    """Delete role configuration (soft delete)."""
    try:
        service = RoleConfigService()
        service.delete(role_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=dict)
async def import_role_configs(configs: List[RoleConfigCreate]):
    """Import multiple role configurations."""
    try:
        service = RoleConfigService()
        result = service.import_configs(configs)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/all", response_model=dict)
async def export_role_configs():
    """Export all role configurations."""
    try:
        service = RoleConfigService()
        configs = service.export_all()
        return {"success": True, "data": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
