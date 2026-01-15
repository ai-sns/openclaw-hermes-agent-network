#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Router

Routes tool calls to appropriate executors based on tool type.
Handles plugin, MCP, function, and skill tool execution.
"""

import logging
from typing import Dict, Any, Optional
from .tool_converter import ToolConverter

logger = logging.getLogger(__name__)


class ToolRouter:
    """
    Route tool calls to appropriate executors

    Function name format:
    - plugin_{plugin_id}
    - mcp_{mcp_id}_{tool_name}
    - function_{function_id}
    - skill_{skill_id}
    """

    def __init__(self, tool_executor):
        """
        Args:
            tool_executor: ToolExecutor instance from backend.modules.tools
        """
        self.tool_executor = tool_executor

    async def execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool based on function name

        Args:
            function_name: OpenAI function name (e.g., "plugin_PL123")
            arguments: Function arguments from LLM

        Returns:
            {
                "success": True/False,
                "result": "...",  # On success
                "error": "...",    # On failure
                "tool_type": "...",
                "tool_id": "...",
                "tool_name": "..." # For MCP only
            }
        """
        # Parse function name
        tool_type, tool_id, tool_name = ToolConverter.parse_function_name(function_name)

        logger.info(f"[ToolRouter] Executing {tool_type} tool: {tool_id} (tool_name={tool_name})")
        logger.info(f"[ToolRouter] Arguments: {arguments}")

        try:
            if tool_type == "plugin":
                result = await self._execute_plugin(tool_id, arguments)

            elif tool_type == "mcp":
                result = await self._execute_mcp(tool_id, tool_name, arguments)

            elif tool_type == "function":
                result = await self._execute_function(tool_id, arguments)

            elif tool_type == "skill":
                result = await self._execute_skill(tool_id, arguments)

            else:
                result = {
                    "success": False,
                    "error": f"Unknown tool type: {tool_type}"
                }

            # Add metadata
            result["tool_type"] = tool_type
            result["tool_id"] = tool_id
            if tool_name:
                result["tool_name"] = tool_name

            return result

        except Exception as e:
            logger.error(f"[ToolRouter] Tool execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_type": tool_type,
                "tool_id": tool_id,
                "tool_name": tool_name
            }

    async def _execute_plugin(self, plugin_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute plugin

        Args:
            plugin_id: Plugin ID (e.g., "PL2026011510474128484")
            arguments: Plugin arguments

        Returns:
            Execution result dict
        """
        logger.info(f"[ToolRouter] Executing plugin: {plugin_id}")

        try:
            # 1. Get plugin data from database
            from backend.database.repositories.system_repository import PluginMngRepository

            plugin_repo = PluginMngRepository()
            plugin_obj = plugin_repo.get_one(plugin_id=plugin_id)

            if not plugin_obj:
                return {
                    "success": False,
                    "error": f"Plugin {plugin_id} not found in database"
                }

            plugin_data = {c.name: getattr(plugin_obj, c.name) for c in plugin_obj.__table__.columns}

            # 2. Call ToolExecutor.execute_plugin(plugin_id, plugin_data, params)
            result = await self.tool_executor.execute_plugin(plugin_id, plugin_data, arguments)

            # ToolExecutor returns: {"success": bool, "result": dict}
            # Extract the actual result if nested
            if result.get("success") and "result" in result:
                actual_result = result["result"]
                if isinstance(actual_result, dict) and "result" in actual_result:
                    return {
                        "success": True,
                        "result": actual_result["result"]
                    }
                else:
                    return {
                        "success": True,
                        "result": str(actual_result)
                    }
            elif result.get("success") is False:
                return {
                    "success": False,
                    "error": result.get("error", "Plugin execution failed")
                }
            else:
                return result

        except Exception as e:
            logger.error(f"[ToolRouter] Plugin {plugin_id} execution failed: {e}")
            return {
                "success": False,
                "error": f"Plugin execution failed: {str(e)}"
            }

    async def _execute_mcp(self, mcp_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP tool

        Args:
            mcp_id: MCP ID (e.g., "MC2026011511561554068")
            tool_name: Tool name within MCP (e.g., "get_weather")
            arguments: Tool arguments

        Returns:
            Execution result dict
        """
        logger.info(f"[ToolRouter] Executing MCP tool: {mcp_id}/{tool_name}")

        try:
            # Call ToolExecutor.execute_mcp_tool()
            result = await self.tool_executor.execute_mcp_tool(mcp_id, tool_name, arguments)

            # Result format: {"success": bool, "result": str}
            if result.get("success"):
                return {
                    "success": True,
                    "result": result.get("result", "")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "MCP tool execution failed")
                }

        except Exception as e:
            logger.error(f"[ToolRouter] MCP {mcp_id}/{tool_name} execution failed: {e}")
            return {
                "success": False,
                "error": f"MCP tool execution failed: {str(e)}"
            }

    async def _execute_function(self, function_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute function

        Args:
            function_id: Function ID (e.g., "FN2026011512345678901")
            arguments: Function arguments

        Returns:
            Execution result dict
        """
        logger.info(f"[ToolRouter] Executing function: {function_id}")

        try:
            # 1. Get function data from database
            from backend.database.repositories.system_repository import FunctionMngRepository

            function_repo = FunctionMngRepository()
            function_obj = function_repo.get_one(function_id=function_id)

            if not function_obj:
                return {
                    "success": False,
                    "error": f"Function {function_id} not found in database"
                }

            function_data = {c.name: getattr(function_obj, c.name) for c in function_obj.__table__.columns}

            # 2. Call ToolExecutor.execute_function(function_id, function_data, params)
            result = await self.tool_executor.execute_function(function_id, function_data, arguments)

            # Extract result
            if result.get("success") and "result" in result:
                actual_result = result["result"]
                if isinstance(actual_result, dict) and "result" in actual_result:
                    return {
                        "success": True,
                        "result": actual_result["result"]
                    }
                else:
                    return {
                        "success": True,
                        "result": str(actual_result)
                    }
            elif result.get("success") is False:
                return {
                    "success": False,
                    "error": result.get("error", "Function execution failed")
                }
            else:
                return result

        except Exception as e:
            logger.error(f"[ToolRouter] Function {function_id} execution failed: {e}")
            return {
                "success": False,
                "error": f"Function execution failed: {str(e)}"
            }

    async def _execute_skill(self, skill_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute skill

        Args:
            skill_id: Skill ID (e.g., "SK2026011512345678901")
            arguments: Skill arguments

        Returns:
            Execution result dict
        """
        logger.info(f"[ToolRouter] Executing skill: {skill_id}")

        try:
            # 1. Get skill data from database
            from backend.database.repositories.system_repository import SkillMngRepository

            skill_repo = SkillMngRepository()
            skill_obj = skill_repo.get_one(skill_id=skill_id)

            if not skill_obj:
                return {
                    "success": False,
                    "error": f"Skill {skill_id} not found in database"
                }

            skill_data = {c.name: getattr(skill_obj, c.name) for c in skill_obj.__table__.columns}

            # 2. Call ToolExecutor.execute_skill(skill_id, skill_data, params)
            result = await self.tool_executor.execute_skill(skill_id, skill_data, arguments)

            # Extract result
            if result.get("success") and "result" in result:
                actual_result = result["result"]
                if isinstance(actual_result, dict) and "result" in actual_result:
                    return {
                        "success": True,
                        "result": actual_result["result"]
                    }
                else:
                    return {
                        "success": True,
                        "result": str(actual_result)
                    }
            elif result.get("success") is False:
                return {
                    "success": False,
                    "error": result.get("error", "Skill execution failed")
                }
            else:
                return result

        except Exception as e:
            logger.error(f"[ToolRouter] Skill {skill_id} execution failed: {e}")
            return {
                "success": False,
                "error": f"Skill execution failed: {str(e)}"
            }
