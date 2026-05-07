# -*- coding: utf-8 -*-
"""LLM configuration API router."""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from .llm_schemas import (
    LLMConfigCreate, LLMConfigUpdate, LLMConfigResponse, LlmTestRequest
)
from .llm_service import LLMConfigService
from .agent_manager import AgentManager
from db.DBFactory import Session
from db.models.agent import AgentCfg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-configs", tags=["LLM Configuration"])


def _reload_agents_using_llm(config_id: str) -> None:
    """Invalidate cached agents that reference the given LLM config_id.

    Only invalidates agents already present in the AgentManager cache to avoid
    eagerly loading agents that are not in use. Subsequent access will reload
    them lazily from the database with the updated LLM config.
    """
    try:
        agent_manager = AgentManager()
        cached_ids = set(getattr(agent_manager, "_agents_cache", {}).keys())
        if not cached_ids:
            return

        session = Session()
        try:
            agents = session.query(AgentCfg).filter(
                AgentCfg.id.in_(cached_ids),
                AgentCfg.is_delete == False,
            ).all()

            affected_ids = []
            for agent in agents:
                match = False
                # Check defaultmodel field
                if agent.defaultmodel and str(agent.defaultmodel).strip() == config_id:
                    match = True

                # Check model_config_id in memo JSON
                if not match and agent.memo:
                    try:
                        memo = json.loads(agent.memo)
                        if isinstance(memo, dict) and memo.get('model_config_id') == config_id:
                            match = True
                    except Exception:
                        pass

                if match:
                    affected_ids.append(agent.id)
        finally:
            session.close()

        # Evict affected agents from cache; next get_agent_by_id will reload.
        for aid in affected_ids:
            try:
                cache = getattr(agent_manager, "_agents_cache", None)
                name_to_id = getattr(agent_manager, "_name_to_id", None)
                if cache is not None and aid in cache:
                    name = cache[aid].name
                    del cache[aid]
                    if name_to_id is not None:
                        name_to_id.pop(name, None)
            except Exception as _re:
                logger.warning("Failed to evict cached agent %s after LLM config change: %s", aid, _re)

        if affected_ids:
            logger.info("Evicted cached agents %s after LLM config %s update", affected_ids, config_id)

            # Clear SNS engine cached agent if any evicted agent is the active one
            try:
                from runtime.apps.sns.service_async import _social_engine_instance
                if _social_engine_instance is not None:
                    eng_agent_id = getattr(
                        getattr(_social_engine_instance, "aisns_cfg", None),
                        "agent_id", None,
                    )
                    if eng_agent_id is not None and int(eng_agent_id) in affected_ids:
                        _social_engine_instance.agent = None
                        logger.info("Cleared SNS engine cached agent after LLM config update")
            except Exception:
                pass
    except Exception as e:
        logger.warning("_reload_agents_using_llm error: %s", e)


@router.get("", response_model=dict)
async def get_llm_configs(
    active_only: Optional[bool] = Query(None, description="Only return active configurations")
):
    """Get all LLM configurations."""
    try:
        service = LLMConfigService()
        # If active_only is not specified, default to returning all active configs
        configs = service.get_all(active_only=active_only if active_only is not None else True)
        return {"success": True, "data": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{config_id}", response_model=dict)
async def get_llm_config(config_id: str):
    """Get LLM configuration by ID."""
    try:
        service = LLMConfigService()
        config = service.get_by_config_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return {"success": True, "data": config}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict)
async def create_llm_config(config: LLMConfigCreate):
    """Create new LLM configuration."""
    try:
        service = LLMConfigService()
        config_id = service.create(config)
        return {"success": True, "data": {"config_id": config_id}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{config_id}", response_model=dict)
async def update_llm_config(config_id: str, config: LLMConfigUpdate):
    """Update LLM configuration."""
    try:
        service = LLMConfigService()
        service.update(config_id, config)

        # Reload all agents that use this LLM config so changes take effect immediately
        _reload_agents_using_llm(config_id)

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{config_id}", response_model=dict)
async def delete_llm_config(config_id: str):
    """Delete LLM configuration (soft delete)."""
    try:
        service = LLMConfigService()
        service.delete(config_id)

        # Evict agents that were using the deleted LLM config
        _reload_agents_using_llm(config_id)

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=dict)
async def test_llm_connection(test_data: LlmTestRequest):
    """Test LLM connection."""
    try:
        service = LLMConfigService()
        result = await service.test_connection(test_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/import", response_model=dict)
async def import_llm_configs(configs: List[LLMConfigCreate]):
    """Import multiple LLM configurations."""
    try:
        service = LLMConfigService()
        result = service.import_configs(configs)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/all", response_model=dict)
async def export_llm_configs():
    """Export all LLM configurations."""
    try:
        service = LLMConfigService()
        configs = service.export_all()
        return {"success": True, "data": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
