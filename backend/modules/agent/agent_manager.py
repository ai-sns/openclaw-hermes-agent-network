# -*- coding: utf-8 -*-
"""
Agent Manager - Agent instance manager
Responsible for creating, caching, and managing agent instances
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from .agent_instance import AgentInstance
from backend.database.base import get_session
from backend.database.models.agent import AgentCfg
from backend.database.models.system import LlmConfig, RoleConfig
from db.DBFactory import query_KMCfg, query_function_mng, query_PluginMng_All_Tool

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Agent manager - singleton

    Responsibilities:
    1. Load agent configuration from the database
    2. Instantiate agent objects
    3. Cache agent instances
    4. Provide methods to get agents by ID or name
    """

    _instance = None
    _agents_cache: Dict[int, AgentInstance] = {}
    _name_to_id: Dict[str, int] = {}

    def __new__(cls):
        """Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the manager."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("AgentManager initialized")

    def _load_llm_config(self, config_id: str, db: Session) -> Optional[Dict]:
        """
        Load LLM configuration.

        Args:
            config_id: LLM config ID
            db: Database session

        Returns:
            LLM config dict
        """
        try:
            llm_config = db.query(LlmConfig).filter(
                LlmConfig.config_id == config_id,
                LlmConfig.is_delete == False,
                LlmConfig.is_active == True
            ).first()

            if not llm_config:
                return None

            return {
                'config_id': llm_config.config_id,
                'name': llm_config.name,
                'provider': llm_config.provider,
                'api_endpoint': llm_config.api_endpoint,
                'api_key': llm_config.api_key,
                'model_name': llm_config.model_name,
                'temperature': llm_config.temperature,
                'max_tokens': llm_config.max_tokens,
                'top_p': llm_config.top_p,
                'frequency_penalty': llm_config.frequency_penalty,
                'presence_penalty': llm_config.presence_penalty,
                'stream': llm_config.stream
            }
        except Exception as e:
            logger.error(f"Failed to load LLM config: {e}")
            return None

    def _load_role_config(self, role_id: str, db: Session) -> Optional[Dict]:
        """
        Load role configuration.

        Args:
            role_id: Role ID
            db: Database session

        Returns:
            Role config dict
        """
        try:
            role_config = db.query(RoleConfig).filter(
                RoleConfig.role_id == role_id,
                RoleConfig.is_delete == False,
                RoleConfig.is_active == True
            ).first()

            if not role_config:
                return None

            return {
                'role_id': role_config.role_id,
                'name': role_config.name,
                'display_name': role_config.display_name,
                'system_prompt': role_config.system_prompt,
                'greeting_message': role_config.greeting_message,
                'category': role_config.category,
                'avatar': role_config.avatar,
                'description': role_config.description
            }
        except Exception as e:
            logger.error(f"Failed to load role config: {e}")
            return None

    def _load_tools(self, agent_cfg: AgentCfg) -> list:
        """
        Load the agent's tool list.

        Args:
            agent_cfg: Agent config object

        Returns:
            Tool list
        """
        tools = []
        try:
            # Parse tool IDs from plugins field
            plugins_str = agent_cfg.plugins or ""
            if plugins_str:
                plugin_ids = [p.strip() for p in plugins_str.split(',') if p.strip()]

                # Query tool configuration
                from db.DBFactory import Session
                session = Session()
                try:
                    for plugin_id in plugin_ids:
                        # Query function_mng table to get tool definition
                        tool_func = query_function_mng(plugin_id)
                        if tool_func:
                            tools.append({
                                'id': plugin_id,
                                'name': getattr(tool_func, 'name', plugin_id),
                                'description': getattr(tool_func, 'description', ''),
                                'parameters': self._parse_tool_parameters(tool_func)
                            })
                finally:
                    session.close()

        except Exception as e:
            logger.error(f"Failed to load tools list: {e}")

        return tools

    def _parse_tool_parameters(self, tool_func) -> Dict:
        """
        Parse tool parameter definition.

        Args:
            tool_func: Tool function object

        Returns:
            Parameters in OpenAI function-calling format
        """
        try:
            # TODO: Parse parameter definitions from tool_func
            # This should be parsed based on the actual tool storage format
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        except Exception as e:
            logger.error(f"Failed to parse tool parameters: {e}")
            return {"type": "object", "properties": {}, "required": []}

    def _load_knowledge_bases(self, agent_cfg: AgentCfg) -> list:
        """
        Load the agent's knowledge base list.

        Args:
            agent_cfg: Agent config object

        Returns:
            Knowledge base list
        """
        kbs = []
        try:
            # Parse KB IDs from kms field
            kms_str = agent_cfg.kms or ""
            if kms_str:
                kb_ids = [k.strip() for k in kms_str.split(',') if k.strip()]

                # Query knowledge base configuration
                for kb_id in kb_ids:
                    kb = query_KMCfg(km_id=kb_id)
                    if kb:
                        kbs.append({
                            'id': getattr(kb, 'id', None),
                            'km_id': getattr(kb, 'km_id', kb_id),
                            'name': getattr(kb, 'name', kb_id),
                            'memo': getattr(kb, 'memo', ''),
                            'kmtype': getattr(kb, 'kmtype', ''),
                            'kmpath': getattr(kb, 'kmpath', '')
                        })

        except Exception as e:
            logger.error(f"Failed to load knowledge base list: {e}")

        return kbs

    def load_agent(self, agent_id: int, force_reload: bool = False) -> Optional[AgentInstance]:
        """
        Load an agent from the database and create an instance.

        Args:
            agent_id: Agent ID
            force_reload: Whether to force reload (ignore cache)

        Returns:
            AgentInstance; returns None on failure
        """
        # Check cache
        if not force_reload and agent_id in self._agents_cache:
            logger.info(f"Get agent from cache: {agent_id}")
            return self._agents_cache[agent_id]

        try:
            # Query database
            db = get_session()
            agent_cfg = db.query(AgentCfg).filter(
                AgentCfg.id == agent_id,
                AgentCfg.is_delete == False
            ).first()

            if not agent_cfg:
                logger.error(f"Agent {agent_id} does not exist")
                return None

            # Parse extra data from memo
            extra_data = {}
            try:
                if agent_cfg.memo:
                    import json
                    extra_data = json.loads(agent_cfg.memo)
            except:
                pass

            # Load LLM config
            model_config_id = extra_data.get('model_config_id') or agent_cfg.defaultmodel
            llm_config = None
            if model_config_id:
                llm_config = self._load_llm_config(model_config_id, db)

            # If no config is found, log a warning and use defaults
            if not llm_config:
                logger.warning(
                    f"Agent {agent_id} has no LLM config; default settings will be used."
                    f" Please select a model configuration for this agent in the frontend."
                )
                llm_config = {
                    'config_id': model_config_id or 'default',
                    'api_endpoint': 'https://api.openai.com/v1',
                    'api_key': '',
                    'model_name': agent_cfg.defaultmodel or 'gpt-4o-mini',
                    'temperature': 0.7,
                    'max_tokens': 2048
                }
                # Flag indicating this is a default config
                llm_config['_is_default'] = True

            # Load role config
            role_config_id = extra_data.get('role_id') or agent_cfg.defaultrole
            role_config = None
            if role_config_id:
                role_config = self._load_role_config(role_config_id, db)

            # If no config is found, use defaults
            if not role_config:
                role_config = {
                    'system_prompt': agent_cfg.prompt or 'You are a helpful AI assistant.',
                    'greeting_message': 'Hello! How can I help you today?'
                }

            # Load tools
            tools = self._load_tools(agent_cfg)

            # Load knowledge bases
            knowledge_bases = self._load_knowledge_bases(agent_cfg)

            # Parse plugins
            plugins = []
            if agent_cfg.plugins:
                plugins = [p.strip() for p in agent_cfg.plugins.split(',') if p.strip()]

            # Create agent instance
            agent_instance = AgentInstance(
                agent_id=agent_cfg.id,
                name=agent_cfg.name,
                description=extra_data.get('description', ''),
                llm_config=llm_config,
                role_config=role_config,
                tools=tools,
                knowledge_bases=knowledge_bases,
                plugins=plugins,
                enable_code_execution=agent_cfg.execfile or False
            )

            # Cache
            self._agents_cache[agent_id] = agent_instance
            self._name_to_id[agent_cfg.name] = agent_id

            logger.info(f"Agent {agent_cfg.name} (ID: {agent_id}) loaded")
            return agent_instance

        except Exception as e:
            logger.error(f"Failed to load agent: {e}", exc_info=True)
            return None

    def get_agent_by_id(self, agent_id: int) -> Optional[AgentInstance]:
        """
        Get an agent instance by ID.

        Args:
            agent_id: Agent ID

        Returns:
            AgentInstance; returns None on failure
        """
        return self.load_agent(agent_id)

    def get_agent_by_name(self, name: str) -> Optional[AgentInstance]:
        """
        Get an agent instance by name.

        Args:
            name: Agent name

        Returns:
            AgentInstance; returns None on failure
        """
        # Check cache first
        if name in self._name_to_id:
            agent_id = self._name_to_id[name]
            return self.get_agent_by_id(agent_id)

        # Query database
        try:
            db = get_session()
            agent_cfg = db.query(AgentCfg).filter(
                AgentCfg.name == name,
                AgentCfg.is_delete == False
            ).first()

            if not agent_cfg:
                logger.error(f"Agent {name} does not exist")
                return None

            return self.load_agent(agent_cfg.id)

        except Exception as e:
            logger.error(f"Failed to get agent by name: {e}")
            return None

    def reload_agent(self, agent_id: int) -> Optional[AgentInstance]:
        """
        Reload an agent (refresh config).

        Args:
            agent_id: Agent ID

        Returns:
            AgentInstance object
        """
        # Clear cache
        if agent_id in self._agents_cache:
            agent_name = self._agents_cache[agent_id].name
            del self._agents_cache[agent_id]
            self._name_to_id.pop(agent_name, None)

        # Reload
        return self.load_agent(agent_id, force_reload=True)

    def clear_cache(self):
        """Clear all caches."""
        self._agents_cache.clear()
        self._name_to_id.clear()
        logger.info("Agent cache cleared")

    def get_all_cached_agents(self) -> list:
        """Get all cached agents."""
        return list(self._agents_cache.values())


# Create global singleton
agent_manager = AgentManager()
