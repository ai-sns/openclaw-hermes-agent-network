# -*- coding: utf-8 -*-
"""
Agent module - Service layer
"""
import logging
import json
from typing import List, Dict, Any, Optional
from db.DBFactory import (
    add_AgentCfg,
    query_AgentCfg_All,
    update_AgentCfg,
    delete_AgentCfg,
    Session,
    AgentCfg
)
from backend.database.repositories.agent_tools_repository import AgentToolsRepository
from backend.database.repositories.system_repository import (
    PluginMngRepository,
    FunctionMngRepository,
    McpMngRepository,
    SkillMngRepository
)
from backend.config.database import get_db_session

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agents"""

    @staticmethod
    def get_all_agents() -> List[Dict[str, Any]]:
        """Get all agent configurations"""
        agents = query_AgentCfg_All()
        result = []
        for agent in agents:
            # 尝试从 memo 字段解析 JSON 存储的额外数据
            extra_data = {}
            try:
                if agent.memo:
                    extra_data = json.loads(agent.memo)
            except:
                pass

            result.append({
                "id": agent.id,
                "name": agent.name,
                "description": extra_data.get('description', ''),
                "model": getattr(agent, 'defaultmodel', 'gpt-4'),
                "model_config_id": extra_data.get('model_config_id', ''),
                "role_id": extra_data.get('role_id', ''),
                "url": extra_data.get('url', ''),
                "wallet_address": extra_data.get('wallet_address', ''),
                "is_active": getattr(agent, 'is_show', True)
            })
        return result

    @staticmethod
    def create_agent(**kwargs) -> int:
        """
        Create a new agent

        Supports both old and new field names.
        New fields (A2A protocol, wallet, etc.) are stored in memo field as JSON.
        """
        # 提取必需的旧字段
        name = kwargs.get('name', 'New Agent')

        # 将新字段打包到 memo 中
        extra_data = {
            'description': kwargs.get('description', ''),
            'model_config_id': kwargs.get('model_config_id', ''),
            'role_id': kwargs.get('role_id', ''),
            'url': kwargs.get('url', ''),
            'version': kwargs.get('version', '1.0.0'),
            'protocol_version': kwargs.get('protocol_version', '0.3'),
            'capabilities': kwargs.get('capabilities', {}),
            'skills': kwargs.get('skills', []),
            'default_input_modes': kwargs.get('default_input_modes', ['text']),
            'default_output_modes': kwargs.get('default_output_modes', ['text']),
            'security_schemes': kwargs.get('security_schemes', {}),
            'provider_organization': kwargs.get('provider_organization', ''),
            'provider_url': kwargs.get('provider_url', ''),
            'documentation_url': kwargs.get('documentation_url', ''),
            'icon_url': kwargs.get('icon_url', ''),
            'wallet_address': kwargs.get('wallet_address', ''),
        }
        memo = json.dumps(extra_data, ensure_ascii=False)

        # 准备旧字段参数
        user_id = kwargs.get('user_id', 'default_user')
        defaultmodel = kwargs.get('model_config_id', kwargs.get('model', 'gpt-4'))
        defaultrole = kwargs.get('role_id', '')
        prompt = kwargs.get('system_prompt', '')

        # 使用默认值调用旧的 add_AgentCfg
        try:
            session = Session()
            agent = AgentCfg(
                user_id=user_id,
                name=name,
                memo=memo,
                borndate=None,  # Use None instead of empty string for DateTime
                borncontry='',
                language='',
                gender='',
                joinfederation=False,  # Boolean, not empty string
                syncfederation=False,  # Boolean, not empty string
                federationid='',
                defaultmodel=defaultmodel,
                defaultrole=defaultrole,
                lastmodel='',
                lastrole='',
                specialization='',
                plugins='',
                kms='',
                last_plugins='',
                last_kms='',
                prompt=prompt,
                snsaccount='',
                snsnickname='',
                islimittotalmessage=False,
                islimitmessagepp=False,
                totalmessages=0,
                ppmessages=0,
                readfile=True,
                writefile=True,
                deletefile=False,
                execfile=False,
                uselastmodel=False,
                uselastrole=False,
                uselastplugins=False,
                uselastkms=False,
                callpluginbyinstruct=False,
                modelfrequent=False,  # Boolean, not empty string
                rolefrequent=False,  # Boolean, not empty string
                multimodelfrequent=False,  # Boolean, not empty string
                autorunrounds=0,
                is_show=kwargs.get('is_active', True)
            )
            session.add(agent)
            session.commit()
            agent_id = agent.id
            session.close()
            return agent_id
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise

    @staticmethod
    def get_agent(agent_id: int) -> Optional[Dict[str, Any]]:
        """Get a single agent by ID"""
        session = Session()
        agent = session.query(AgentCfg).filter_by(id=agent_id).first()
        session.close()

        if not agent:
            return None

        # 解析 memo 中的额外数据
        extra_data = {}
        try:
            if agent.memo:
                extra_data = json.loads(agent.memo)
        except:
            pass

        return {
            "id": agent.id,
            "name": agent.name,
            "description": extra_data.get('description', ''),
            "model": getattr(agent, 'defaultmodel', 'gpt-4'),
            "model_config_id": extra_data.get('model_config_id', ''),
            "role_id": extra_data.get('role_id', ''),
            "system_prompt": getattr(agent, 'prompt', ''),
            "url": extra_data.get('url', ''),
            "version": extra_data.get('version', '1.0.0'),
            "protocol_version": extra_data.get('protocol_version', '0.3'),
            "capabilities": extra_data.get('capabilities', {}),
            "skills": extra_data.get('skills', []),
            "default_input_modes": extra_data.get('default_input_modes', ['text']),
            "default_output_modes": extra_data.get('default_output_modes', ['text']),
            "security_schemes": extra_data.get('security_schemes', {}),
            "provider_organization": extra_data.get('provider_organization', ''),
            "provider_url": extra_data.get('provider_url', ''),
            "documentation_url": extra_data.get('documentation_url', ''),
            "icon_url": extra_data.get('icon_url', ''),
            "wallet_address": extra_data.get('wallet_address', ''),
            "is_active": getattr(agent, 'is_show', True)
        }

    @staticmethod
    def update_agent(agent_id: int, **kwargs) -> None:
        """Update agent configuration"""
        session = Session()
        agent = session.query(AgentCfg).filter_by(id=agent_id).first()

        if not agent:
            session.close()
            raise ValueError(f"Agent {agent_id} not found")

        # 解析现有的 memo
        extra_data = {}
        try:
            if agent.memo:
                extra_data = json.loads(agent.memo)
        except:
            pass

        # 更新基本字段
        if 'name' in kwargs:
            agent.name = kwargs['name']
        if 'model_config_id' in kwargs or 'model' in kwargs:
            agent.defaultmodel = kwargs.get('model_config_id', kwargs.get('model', agent.defaultmodel))
        if 'role_id' in kwargs:
            agent.defaultrole = kwargs['role_id']
        if 'system_prompt' in kwargs:
            agent.prompt = kwargs['system_prompt']
        if 'is_active' in kwargs:
            agent.is_show = kwargs['is_active']

        # 更新 memo 中的额外字段
        for key in ['description', 'url', 'version', 'protocol_version', 'capabilities',
                    'skills', 'default_input_modes', 'default_output_modes', 'security_schemes',
                    'provider_organization', 'provider_url', 'documentation_url',
                    'icon_url', 'wallet_address', 'model_config_id', 'role_id']:
            if key in kwargs:
                extra_data[key] = kwargs[key]

        agent.memo = json.dumps(extra_data, ensure_ascii=False)

        session.commit()
        session.close()

    @staticmethod
    def delete_agent(agent_id: int) -> None:
        """Delete an agent (soft delete)"""
        session = Session()
        agent = session.query(AgentCfg).filter_by(id=agent_id).first()
        if agent:
            agent.is_delete = True
            agent.is_show = False
            session.commit()
        session.close()

    # ==================== Agent Tools Management ====================

    @staticmethod
    def get_agent_tools(agent_id: int) -> List[Dict[str, Any]]:
        """
        Get all tools associated with an agent (with full details)

        Args:
            agent_id: Agent ID

        Returns:
            List of tools with details from respective tables
        """
        db = get_db_session()
        try:
            agent_tools_repo = AgentToolsRepository(db)

            # Get tool associations
            associations = agent_tools_repo.get_agent_tools(agent_id)

            # Enrich with tool details
            tools = []
            for assoc in associations:
                tool_type = assoc["tool_type"]
                tool_id = assoc["tool_id"]

                tool_detail = None

                if tool_type == "plugin":
                    plugin_repo = PluginMngRepository()
                    tool_obj = plugin_repo.get_one(plugin_id=tool_id)
                    if tool_obj:
                        tool_detail = {c.name: getattr(tool_obj, c.name) for c in tool_obj.__table__.columns}
                        tool_detail["tool_type"] = "plugin"

                elif tool_type == "mcp":
                    mcp_repo = McpMngRepository()
                    tool_obj = mcp_repo.get_one(mcp_id=tool_id)
                    if tool_obj:
                        tool_detail = {c.name: getattr(tool_obj, c.name) for c in tool_obj.__table__.columns}
                        tool_detail["tool_type"] = "mcp"

                elif tool_type == "function":
                    function_repo = FunctionMngRepository()
                    tool_obj = function_repo.get_one(function_id=tool_id)
                    if tool_obj:
                        tool_detail = {c.name: getattr(tool_obj, c.name) for c in tool_obj.__table__.columns}
                        tool_detail["tool_type"] = "function"

                elif tool_type == "skill":
                    skill_repo = SkillMngRepository()
                    tool_obj = skill_repo.get_one(skill_id=tool_id)
                    if tool_obj:
                        tool_detail = {c.name: getattr(tool_obj, c.name) for c in tool_obj.__table__.columns}
                        tool_detail["tool_type"] = "skill"

                if tool_detail:
                    tool_detail["enabled"] = assoc["enabled"]
                    tool_detail["priority"] = assoc["priority"]
                    tools.append(tool_detail)

            return tools

        finally:
            db.close()

    @staticmethod
    def update_agent_tools(agent_id: int, tools: List[Dict[str, Any]]) -> None:
        """
        Update agent's associated tools

        Args:
            agent_id: Agent ID
            tools: List of tool associations
                [
                    {"tool_type": "plugin", "tool_id": "PL...", "priority": 10},
                    {"tool_type": "mcp", "tool_id": "MC...", "priority": 5}
                ]
        """
        db = get_db_session()
        try:
            repo = AgentToolsRepository(db)

            # Clear existing tools
            repo.clear_agent_tools(agent_id)

            # Add new tools
            for tool in tools:
                tool_type = tool.get("tool_type")
                tool_id = tool.get("tool_id")
                priority = tool.get("priority", 0)
                enabled = tool.get("enabled", 1)

                if tool_type and tool_id:
                    repo.add_agent_tool(agent_id, tool_type, tool_id, enabled, priority)

            logger.info(f"Updated tools for agent {agent_id}: {len(tools)} tools")

        finally:
            db.close()

    @staticmethod
    def get_available_tools(agent_id: int) -> Dict[str, Any]:
        """
        Get all available tools (for tool selection UI)

        Args:
            agent_id: Agent ID (to mark which tools are already associated)

        Returns:
            Dict with all tools grouped by type, with association status
        """
        db = get_db_session()
        try:
            agent_tools_repo = AgentToolsRepository(db)

            # Get current agent tool associations
            associations = agent_tools_repo.get_agent_tools(agent_id)
            associated_tools = {
                (assoc["tool_type"], assoc["tool_id"])
                for assoc in associations
            }

            # Get all plugins
            plugin_repo = PluginMngRepository()
            plugins_objs = plugin_repo.get_all()
            plugins = [plugin_repo.to_dict(p) for p in plugins_objs]
            for plugin in plugins:
                plugin["associated"] = ("plugin", plugin.get("plugin_id")) in associated_tools

            # Get all MCPs
            mcp_repo = McpMngRepository()
            mcps_objs = mcp_repo.get_all()
            mcps = [mcp_repo.to_dict(m) for m in mcps_objs]
            for mcp in mcps:
                mcp["associated"] = ("mcp", mcp.get("mcp_id")) in associated_tools

            # Get all functions
            function_repo = FunctionMngRepository()
            functions_objs = function_repo.get_all()
            functions = [function_repo.to_dict(f) for f in functions_objs]
            for func in functions:
                func["associated"] = ("function", func.get("function_id")) in associated_tools

            # Get all skills
            skill_repo = SkillMngRepository()
            skills_objs = skill_repo.get_all()
            skills = [skill_repo.to_dict(s) for s in skills_objs]
            for skill in skills:
                skill["associated"] = ("skill", skill.get("skill_id")) in associated_tools

            return {
                "plugins": plugins,
                "mcps": mcps,
                "functions": functions,
                "skills": skills
            }

        finally:
            db.close()


