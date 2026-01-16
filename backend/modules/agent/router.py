# -*- coding: utf-8 -*-
"""
Agent module - API router
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from .schemas import AgentConfig, AgentResponse, AgentUpdateConfig
from .service import AgentService
from .dependencies import get_agent_service
from .agent_manager import AgentManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=dict)
async def get_agents(service: AgentService = Depends(get_agent_service)):
    """
    Get all agent configurations

    Returns:
        List of agent configurations
    """
    try:
        agents = service.get_all_agents()
        return {"success": True, "data": agents}
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=dict)
async def get_agent(
    agent_id: int,
    service: AgentService = Depends(get_agent_service)
):
    """
    Get a single agent by ID

    Args:
        agent_id: Agent ID

    Returns:
        Agent configuration
    """
    try:
        agent = service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"success": True, "data": agent}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict)
async def create_agent(
    config: AgentConfig,
    service: AgentService = Depends(get_agent_service)
):
    """
    Create a new agent

    Args:
        config: Agent configuration

    Returns:
        Created agent ID
    """
    try:
        # 将 Pydantic 模型转换为字典，排除未设置的字段
        agent_data = config.dict(exclude_unset=True)
        agent_id = service.create_agent(**agent_data)
        return {"success": True, "data": {"id": agent_id}}
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}", response_model=dict)
async def update_agent(
    agent_id: int,
    config: AgentUpdateConfig,
    service: AgentService = Depends(get_agent_service)
):
    """
    Update agent configuration

    Args:
        agent_id: Agent ID
        config: Updated agent configuration (all fields optional)

    Returns:
        Success status
    """
    try:
        # 只传递非None的字段
        agent_data = config.dict(exclude_unset=True, exclude_none=True)
        service.update_agent(agent_id, **agent_data)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}", response_model=dict)
async def delete_agent(
    agent_id: int,
    service: AgentService = Depends(get_agent_service)
):
    """
    Delete an agent

    Args:
        agent_id: Agent ID

    Returns:
        Success status
    """
    try:
        service.delete_agent(agent_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Tools Management ====================

@router.get("/{agent_id}/tools", response_model=dict)
async def get_agent_tools(
    agent_id: int,
    service: AgentService = Depends(get_agent_service)
):
    """
    Get all tools associated with an agent

    Args:
        agent_id: Agent ID

    Returns:
        List of tools with full details
    """
    try:
        tools = service.get_agent_tools(agent_id)
        return {
            "success": True,
            "data": {
                "agent_id": agent_id,
                "tools": tools
            }
        }
    except Exception as e:
        logger.error(f"Error getting agent tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/tools", response_model=dict)
async def update_agent_tools(
    agent_id: int,
    request_body: dict,
    service: AgentService = Depends(get_agent_service)
):
    """
    Update agent's associated tools

    Args:
        agent_id: Agent ID
        request_body: {"tools": [...]} where tools is a list of:
            [
                {"tool_type": "plugin", "tool_id": "PL...", "enabled": true, "priority": 10},
                {"tool_type": "mcp", "tool_id": "MC...", "enabled": true, "priority": 5}
            ]

    Returns:
        Success status
    """
    try:
        tools = request_body.get("tools", [])
        service.update_agent_tools(agent_id, tools)

        # 重新加载Agent实例以应用新的工具配置
        agent_manager = AgentManager()
        agent_manager.reload_agent(agent_id)
        logger.info(f"Agent {agent_id} 工具配置已更新并重新加载")

        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating agent tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/available-tools", response_model=dict)
async def get_available_tools(
    agent_id: int,
    service: AgentService = Depends(get_agent_service)
):
    """
    Get all available tools (for tool selection UI)

    Args:
        agent_id: Agent ID (to mark which tools are already associated)

    Returns:
        All tools grouped by type, with association status
    """
    try:
        tools = service.get_available_tools(agent_id)
        return {"success": True, "data": tools}
    except Exception as e:
        logger.error(f"Error getting available tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

