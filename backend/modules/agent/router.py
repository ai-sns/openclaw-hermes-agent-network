# -*- coding: utf-8 -*-
"""
Agent module - API router
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from .schemas import AgentConfig, AgentResponse, AgentUpdateConfig, AgentModelParamsUpdate
from .service import AgentService
from .dependencies import get_agent_service
from .agent_manager import AgentManager
from .code_executor import CodeExecutor
from db.DBFactory import Session, AgentCfg

logger = logging.getLogger(__name__)

router = APIRouter()


class ExecutePythonRequest(BaseModel):
    code: str


@router.put("/reorder", response_model=dict)
async def reorder_agents(request: Request):
    try:
        items = await request.json()

        if not isinstance(items, list):
            raise HTTPException(status_code=422, detail="Expected a list of items")

        if len(items) == 0:
            return {"success": True}

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise HTTPException(status_code=422, detail=f"Item {idx} is not a dict")
            if "id" not in item:
                raise HTTPException(status_code=422, detail=f"Item {idx} missing 'id'")
            if "position" not in item:
                raise HTTPException(status_code=422, detail=f"Item {idx} missing 'position'")

        from db.write_queue import db_write
        _items = [(int(item["id"]), int(item["position"])) for item in items]
        def _do(session):
            for aid, pos in _items:
                session.query(AgentCfg).filter_by(id=aid).update({"position": pos})
        db_write(_do, description="agent_router_reorder")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-python", response_model=dict)
async def execute_python(payload: ExecutePythonRequest):
    try:
        code = (payload.code or "").strip()
        if not code:
            raise HTTPException(status_code=422, detail="Code is required")

        executor = CodeExecutor(timeout=30, max_output_size=20000)
        result = executor.execute_python(code)

        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing python: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=dict)
async def get_agent_list(service: AgentService = Depends(get_agent_service)):
    """
    Get simplified agent list (id and name only)

    Returns:
        List of agents with id and name
    """
    try:
        agents = service.get_all_agents()
        # Return simplified list with only id and name
        agent_list = [{"id": agent["id"], "name": agent["name"]} for agent in agents]
        return {"success": True, "data": agent_list}
    except Exception as e:
        logger.error(f"Error getting agent list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        agent_type = (config.agent_type or "local").lower()
        if agent_type == "remote":
            framework = (config.framework or "").strip()
            framework_other = (config.framework_other or "").strip()
            llm_provider = (config.llm_provider or "").strip()
            model_description = (config.model_description or "").strip()

            if not framework:
                raise HTTPException(status_code=422, detail="Framework is required for remote agents")
            if framework == "Other" and not framework_other:
                raise HTTPException(status_code=422, detail="Other framework name is required when Framework is 'Other'")
            if not llm_provider:
                raise HTTPException(status_code=422, detail="LLM provider is required for remote agents")
            if not model_description:
                raise HTTPException(status_code=422, detail="Model description is required for remote agents")

        # Convert Pydantic model to dict, excluding unset fields
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
        existing_agent = service.get_agent(agent_id)
        if not existing_agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent_type = (config.agent_type if config.agent_type is not None else existing_agent.get("agent_type") or "local")
        agent_type = str(agent_type).lower()
        if agent_type == "remote":
            framework = (config.framework if config.framework is not None else existing_agent.get("framework") or "").strip()
            framework_other = (config.framework_other if config.framework_other is not None else existing_agent.get("framework_other") or "").strip()
            llm_provider = (config.llm_provider if config.llm_provider is not None else existing_agent.get("llm_provider") or "").strip()
            model_description = (config.model_description if config.model_description is not None else existing_agent.get("model_description") or "").strip()

            if not framework:
                raise HTTPException(status_code=422, detail="Framework is required for remote agents")
            if framework == "Other" and not framework_other:
                raise HTTPException(status_code=422, detail="Other framework name is required when Framework is 'Other'")
            if not llm_provider:
                raise HTTPException(status_code=422, detail="LLM provider is required for remote agents")
            if not model_description:
                raise HTTPException(status_code=422, detail="Model description is required for remote agents")

        # Only pass fields that are not None
        agent_data = config.dict(exclude_unset=True, exclude_none=True)
        service.update_agent(agent_id, **agent_data)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/model-params", response_model=dict)
async def get_agent_model_params(agent_id: int):
    try:
        session = Session()
        try:
            agent = session.query(AgentCfg).filter_by(id=agent_id).first()
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            extra_data = {}
            try:
                if agent.memo:
                    import json
                    extra_data = json.loads(agent.memo)
            except Exception:
                extra_data = {}

            model_params = extra_data.get('model_params')
            if not isinstance(model_params, dict):
                model_params = {}

            return {"success": True, "data": model_params}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent model params: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}/model-params", response_model=dict)
async def update_agent_model_params(agent_id: int, params: AgentModelParamsUpdate):
    try:
        update_data = params.dict(exclude_unset=True, exclude_none=True)

        session = Session()
        try:
            agent = session.query(AgentCfg).filter_by(id=agent_id).first()
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            extra_data = {}
            try:
                if agent.memo:
                    import json
                    extra_data = json.loads(agent.memo)
            except Exception:
                extra_data = {}

            existing = extra_data.get('model_params')
            if not isinstance(existing, dict):
                existing = {}

            merged = {**existing, **update_data}
            extra_data['model_params'] = merged

            import json
            from db.write_queue import db_write
            _aid = agent_id
            _memo = json.dumps(extra_data, ensure_ascii=False)
            def _do(sess):
                rec = sess.query(AgentCfg).filter_by(id=_aid).first()
                if rec:
                    rec.memo = _memo
            db_write(_do, description="agent_router_update_model_params")
        finally:
            session.close()

        agent_manager = AgentManager()
        agent_manager.reload_agent(agent_id)

        return {"success": True, "data": merged}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent model params: {e}")
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

        # Reload agent instance to apply the new tool configuration
        agent_manager = AgentManager()
        agent_manager.reload_agent(agent_id)
        logger.info(f"Agent {agent_id} tool configuration updated and reloaded")

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


@router.get("/{agent_id}/knowledge-bases", response_model=dict)
async def get_agent_knowledge_bases(agent_id: int):
    """Get agent's configured knowledge bases (km_id list)"""
    session = Session()
    try:
        agent = session.query(AgentCfg).filter_by(id=agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        kms_str = getattr(agent, 'kms', '') or ''
        km_ids = [k.strip() for k in kms_str.split(',') if k.strip()]
        return {
            "success": True,
            "data": {
                "agent_id": agent_id,
                "km_ids": km_ids
            }
        }
    finally:
        session.close()


@router.post("/{agent_id}/knowledge-bases", response_model=dict)
async def update_agent_knowledge_bases(agent_id: int, request_body: dict):
    """Update agent's knowledge base list and reload agent instance"""
    km_ids = request_body.get('km_ids', [])
    if km_ids is None:
        km_ids = []

    if not isinstance(km_ids, list):
        raise HTTPException(status_code=400, detail="km_ids must be a list")

    normalized = []
    for item in km_ids:
        s = str(item).strip()
        if s and s not in normalized:
            normalized.append(s)

    session = Session()
    try:
        agent = session.query(AgentCfg).filter_by(id=agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        from db.write_queue import db_write
        _aid = agent_id
        _kms = ','.join(normalized)
        def _do(sess):
            rec = sess.query(AgentCfg).filter_by(id=_aid).first()
            if rec:
                rec.kms = _kms
        db_write(_do, description="agent_router_update_kms")

        agent_manager = AgentManager()
        agent_manager.reload_agent(agent_id)

        return {"success": True, "data": {"agent_id": agent_id, "km_ids": normalized}}
    finally:
        session.close()

