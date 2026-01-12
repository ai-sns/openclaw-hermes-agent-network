# -*- coding: utf-8 -*-
"""
Agent Manager - Agent实例管理器
负责创建、缓存和管理Agent实例
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
    Agent管理器 - 单例模式

    负责:
    1. 从数据库加载Agent配置
    2. 实例化Agent对象
    3. 缓存Agent实例
    4. 提供按ID或名称获取Agent的方法
    """

    _instance = None
    _agents_cache: Dict[int, AgentInstance] = {}
    _name_to_id: Dict[str, int] = {}

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化管理器"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("AgentManager 已初始化")

    def _load_llm_config(self, config_id: str, db: Session) -> Optional[Dict]:
        """
        加载LLM配置

        Args:
            config_id: LLM配置ID
            db: 数据库session

        Returns:
            LLM配置字典
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
            logger.error(f"加载LLM配置失败: {e}")
            return None

    def _load_role_config(self, role_id: str, db: Session) -> Optional[Dict]:
        """
        加载角色配置

        Args:
            role_id: 角色ID
            db: 数据库session

        Returns:
            角色配置字典
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
            logger.error(f"加载角色配置失败: {e}")
            return None

    def _load_tools(self, agent_cfg: AgentCfg) -> list:
        """
        加载Agent的工具列表

        Args:
            agent_cfg: Agent配置对象

        Returns:
            工具列表
        """
        tools = []
        try:
            # 从plugins字段解析工具ID
            plugins_str = agent_cfg.plugins or ""
            if plugins_str:
                plugin_ids = [p.strip() for p in plugins_str.split(',') if p.strip()]

                # 查询工具配置
                from db.DBFactory import Session
                session = Session()
                try:
                    for plugin_id in plugin_ids:
                        # 查询function_mng表获取工具定义
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
            logger.error(f"加载工具列表失败: {e}")

        return tools

    def _parse_tool_parameters(self, tool_func) -> Dict:
        """
        解析工具参数定义

        Args:
            tool_func: 工具函数对象

        Returns:
            OpenAI function calling格式的parameters
        """
        try:
            # TODO: 从tool_func解析参数定义
            # 这里需要根据实际的工具存储格式来解析
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        except Exception as e:
            logger.error(f"解析工具参数失败: {e}")
            return {"type": "object", "properties": {}, "required": []}

    def _load_knowledge_bases(self, agent_cfg: AgentCfg) -> list:
        """
        加载Agent的知识库列表

        Args:
            agent_cfg: Agent配置对象

        Returns:
            知识库列表
        """
        kbs = []
        try:
            # 从kms字段解析知识库ID
            kms_str = agent_cfg.kms or ""
            if kms_str:
                kb_ids = [k.strip() for k in kms_str.split(',') if k.strip()]

                # 查询知识库配置
                for kb_id in kb_ids:
                    kb = query_KMCfg(kb_id)
                    if kb:
                        kbs.append({
                            'id': kb_id,
                            'name': getattr(kb, 'name', kb_id),
                            'description': getattr(kb, 'description', ''),
                            'km_type': getattr(kb, 'km_type', 'vector'),
                            'path': getattr(kb, 'path', '')
                        })

        except Exception as e:
            logger.error(f"加载知识库列表失败: {e}")

        return kbs

    def load_agent(self, agent_id: int, force_reload: bool = False) -> Optional[AgentInstance]:
        """
        从数据库加载Agent并创建实例

        Args:
            agent_id: Agent ID
            force_reload: 是否强制重新加载（忽略缓存）

        Returns:
            AgentInstance对象，失败返回None
        """
        # 检查缓存
        if not force_reload and agent_id in self._agents_cache:
            logger.info(f"从缓存获取Agent: {agent_id}")
            return self._agents_cache[agent_id]

        try:
            # 查询数据库
            db = get_session()
            agent_cfg = db.query(AgentCfg).filter(
                AgentCfg.id == agent_id,
                AgentCfg.is_delete == False
            ).first()

            if not agent_cfg:
                logger.error(f"Agent {agent_id} 不存在")
                return None

            # 解析memo中的额外数据
            extra_data = {}
            try:
                if agent_cfg.memo:
                    import json
                    extra_data = json.loads(agent_cfg.memo)
            except:
                pass

            # 加载LLM配置
            model_config_id = extra_data.get('model_config_id') or agent_cfg.defaultmodel
            llm_config = None
            if model_config_id:
                llm_config = self._load_llm_config(model_config_id, db)

            # 如果没有找到配置，记录警告并使用默认值
            if not llm_config:
                logger.warning(f"Agent {agent_id} 没有配置LLM模型，将使用默认配置。"
                             f"请在前端为该Agent选择一个模型配置。")
                llm_config = {
                    'config_id': model_config_id or 'default',
                    'api_endpoint': 'https://api.openai.com/v1',
                    'api_key': '',
                    'model_name': agent_cfg.defaultmodel or 'gpt-4o-mini',
                    'temperature': 0.7,
                    'max_tokens': 2048
                }
                # 设置一个标志，表示这是默认配置
                llm_config['_is_default'] = True

            # 加载角色配置
            role_config_id = extra_data.get('role_id') or agent_cfg.defaultrole
            role_config = None
            if role_config_id:
                role_config = self._load_role_config(role_config_id, db)

            # 如果没有找到配置，使用默认值
            if not role_config:
                role_config = {
                    'system_prompt': agent_cfg.prompt or 'You are a helpful AI assistant.',
                    'greeting_message': 'Hello! How can I help you today?'
                }

            # 加载工具
            tools = self._load_tools(agent_cfg)

            # 加载知识库
            knowledge_bases = self._load_knowledge_bases(agent_cfg)

            # 解析plugins
            plugins = []
            if agent_cfg.plugins:
                plugins = [p.strip() for p in agent_cfg.plugins.split(',') if p.strip()]

            # 创建Agent实例
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

            # 缓存
            self._agents_cache[agent_id] = agent_instance
            self._name_to_id[agent_cfg.name] = agent_id

            logger.info(f"Agent {agent_cfg.name} (ID: {agent_id}) 已加载")
            return agent_instance

        except Exception as e:
            logger.error(f"加载Agent失败: {e}", exc_info=True)
            return None

    def get_agent_by_id(self, agent_id: int) -> Optional[AgentInstance]:
        """
        按ID获取Agent实例

        Args:
            agent_id: Agent ID

        Returns:
            AgentInstance对象，失败返回None
        """
        return self.load_agent(agent_id)

    def get_agent_by_name(self, name: str) -> Optional[AgentInstance]:
        """
        按名称获取Agent实例

        Args:
            name: Agent名称

        Returns:
            AgentInstance对象，失败返回None
        """
        # 先查缓存
        if name in self._name_to_id:
            agent_id = self._name_to_id[name]
            return self.get_agent_by_id(agent_id)

        # 查数据库
        try:
            db = get_session()
            agent_cfg = db.query(AgentCfg).filter(
                AgentCfg.name == name,
                AgentCfg.is_delete == False
            ).first()

            if not agent_cfg:
                logger.error(f"Agent {name} 不存在")
                return None

            return self.load_agent(agent_cfg.id)

        except Exception as e:
            logger.error(f"按名称获取Agent失败: {e}")
            return None

    def reload_agent(self, agent_id: int) -> Optional[AgentInstance]:
        """
        重新加载Agent（刷新配置）

        Args:
            agent_id: Agent ID

        Returns:
            AgentInstance对象
        """
        # 清除缓存
        if agent_id in self._agents_cache:
            agent_name = self._agents_cache[agent_id].name
            del self._agents_cache[agent_id]
            self._name_to_id.pop(agent_name, None)

        # 重新加载
        return self.load_agent(agent_id, force_reload=True)

    def clear_cache(self):
        """清除所有缓存"""
        self._agents_cache.clear()
        self._name_to_id.clear()
        logger.info("Agent缓存已清除")

    def get_all_cached_agents(self) -> list:
        """获取所有已缓存的Agent"""
        return list(self._agents_cache.values())


# 创建全局单例
agent_manager = AgentManager()
