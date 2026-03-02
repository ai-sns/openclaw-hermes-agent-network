# -*- coding: utf-8 -*-
"""
Tools module - API router
Provides REST API for managing plugins, MCP, functions, and computer use tools
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session

from backend.config.database import get_db_sync_depends
from .schemas import (
    PluginCreate, PluginUpdate, PluginResponse,
    MCPCreate, MCPUpdate, MCPResponse,
    FunctionCreate, FunctionUpdate, FunctionResponse,
    SkillCreate, SkillUpdate, SkillResponse
)
from .service import ToolsService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tools_service(db: Session = Depends(get_db_sync_depends)) -> ToolsService:
    """Dependency to get tools service with database session"""
    return ToolsService(db)


# ==================== Plugin Endpoints ====================

@router.get("/plugins", response_model=List[PluginResponse])
async def get_all_plugins(
    used_in_sns: Optional[bool] = None,
    service: ToolsService = Depends(get_tools_service)
):
    """Get all plugins"""
    try:
        return service.get_all_plugins(used_in_sns=used_in_sns)
    except Exception as e:
        logger.error(f"Error getting plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str, service: ToolsService = Depends(get_tools_service)):
    """Get plugin by ID"""
    plugin = service.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin


@router.post("/plugins", response_model=PluginResponse)
async def create_plugin(plugin: PluginCreate, service: ToolsService = Depends(get_tools_service)):
    """Create a new plugin"""
    try:
        return service.create_plugin(plugin)
    except Exception as e:
        logger.error(f"Error creating plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/import", response_model=PluginResponse)
async def import_plugin(
    file: UploadFile = File(...),
    used_in_sns: bool = True,
    service: ToolsService = Depends(get_tools_service)
):
    """Import a renderer plugin from a zip file"""
    try:
        return service.import_renderer_plugin_zip(file, used_in_sns=used_in_sns)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plugins/{plugin_id}", response_model=PluginResponse)
async def update_plugin(
    plugin_id: str,
    plugin: PluginUpdate,
    service: ToolsService = Depends(get_tools_service)
):
    """Update plugin"""
    result = service.update_plugin(plugin_id, plugin)
    if not result:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return result


@router.delete("/plugins/{plugin_id}")
async def delete_plugin(plugin_id: str, service: ToolsService = Depends(get_tools_service)):
    """Delete plugin"""
    success = service.delete_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"success": True, "message": "Plugin deleted successfully"}


# ==================== MCP Endpoints ====================

@router.get("/mcp", response_model=List[MCPResponse])
async def get_all_mcps(service: ToolsService = Depends(get_tools_service)):
    """Get all MCPs"""
    try:
        return service.get_all_mcps()
    except Exception as e:
        logger.error(f"Error getting MCPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/{mcp_id}", response_model=MCPResponse)
async def get_mcp(mcp_id: str, service: ToolsService = Depends(get_tools_service)):
    """Get MCP by ID"""
    mcp = service.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    return mcp


@router.post("/mcp", response_model=MCPResponse)
async def create_mcp(mcp: MCPCreate, service: ToolsService = Depends(get_tools_service)):
    """Create a new MCP"""
    try:
        return service.create_mcp(mcp)
    except Exception as e:
        logger.error(f"Error creating MCP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mcp/{mcp_id}", response_model=MCPResponse)
async def update_mcp(
    mcp_id: str,
    mcp: MCPUpdate,
    service: ToolsService = Depends(get_tools_service)
):
    """Update MCP"""
    result = service.update_mcp(mcp_id, mcp)
    if not result:
        raise HTTPException(status_code=404, detail="MCP not found")
    return result


@router.delete("/mcp/{mcp_id}")
async def delete_mcp(mcp_id: str, service: ToolsService = Depends(get_tools_service)):
    """Delete MCP"""
    success = service.delete_mcp(mcp_id)
    if not success:
        raise HTTPException(status_code=404, detail="MCP not found")
    return {"success": True, "message": "MCP deleted successfully"}


# ==================== Function Endpoints ====================

@router.get("/functions", response_model=List[FunctionResponse])
async def get_all_functions(service: ToolsService = Depends(get_tools_service)):
    """Get all functions"""
    try:
        return service.get_all_functions()
    except Exception as e:
        logger.error(f"Error getting functions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/functions/{function_id}", response_model=FunctionResponse)
async def get_function(function_id: str, service: ToolsService = Depends(get_tools_service)):
    """Get function by ID"""
    function = service.get_function(function_id)
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    return function


@router.post("/functions", response_model=FunctionResponse)
async def create_function(function: FunctionCreate, service: ToolsService = Depends(get_tools_service)):
    """Create a new function"""
    try:
        return service.create_function(function)
    except Exception as e:
        logger.error(f"Error creating function: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/functions/{function_id}", response_model=FunctionResponse)
async def update_function(
    function_id: str,
    function: FunctionUpdate,
    service: ToolsService = Depends(get_tools_service)
):
    """Update function"""
    result = service.update_function(function_id, function)
    if not result:
        raise HTTPException(status_code=404, detail="Function not found")
    return result


@router.delete("/functions/{function_id}")
async def delete_function(function_id: str, service: ToolsService = Depends(get_tools_service)):
    """Delete function"""
    success = service.delete_function(function_id)
    if not success:
        raise HTTPException(status_code=404, detail="Function not found")
    return {"success": True, "message": "Function deleted successfully"}


# ==================== Skill (Computer Use) Endpoints ====================

@router.get("/skills", response_model=List[SkillResponse])
async def get_all_skills(service: ToolsService = Depends(get_tools_service)):
    """Get all skills (computer use tools)"""

    try:
        return service.get_all_skills()
    except Exception as e:
        logger.error(f"Error getting skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str, service: ToolsService = Depends(get_tools_service)):
    """Get skill by ID"""
    skill = service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("/skills", response_model=SkillResponse)
async def create_skill(skill: SkillCreate, service: ToolsService = Depends(get_tools_service)):
    """Create a new skill"""
    try:
        return service.create_skill(skill)
    except Exception as e:
        logger.error(f"Error creating skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    skill: SkillUpdate,
    service: ToolsService = Depends(get_tools_service)
):
    """Update skill"""
    result = service.update_skill(skill_id, skill)
    if not result:
        raise HTTPException(status_code=404, detail="Skill not found")
    return result


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str, service: ToolsService = Depends(get_tools_service)):
    """Delete skill"""
    success = service.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"success": True, "message": "Skill deleted successfully"}


# ==================== Tool Execution Endpoints ====================

@router.post("/plugins/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, params: dict = {}, service: ToolsService = Depends(get_tools_service)):
    """Execute a plugin"""
    try:
        result = await service.execute_plugin(plugin_id, params)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error executing plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/{mcp_id}/execute")
async def execute_mcp(mcp_id: str, params: dict = {}, service: ToolsService = Depends(get_tools_service)):
    """Execute/test MCP connection"""
    try:
        result = await service.execute_mcp(mcp_id, params)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error executing MCP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/functions/{function_id}/execute")
async def execute_function(function_id: str, params: dict = {}, service: ToolsService = Depends(get_tools_service)):
    """Execute a function"""
    try:
        result = await service.execute_function(function_id, params)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error executing function: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skills/{skill_id}/execute")
async def execute_skill(skill_id: str, params: dict = {}, service: ToolsService = Depends(get_tools_service)):
    """Execute a computer use skill"""
    try:
        result = await service.execute_skill(skill_id, params)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error executing skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))
