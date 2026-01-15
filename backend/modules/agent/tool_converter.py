#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Format Converter

Converts different tool types (Plugin, MCP, Function, Skill) to OpenAI Function Calling format.
This allows agents to use any tool type through a unified interface.
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ToolConverter:
    """
    Convert different tool types to OpenAI Function Calling format

    OpenAI Function Calling Format:
    {
        "type": "function",
        "function": {
            "name": "function_name",
            "description": "What this function does",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "..."},
                    "param2": {"type": "number", "description": "..."}
                },
                "required": ["param1"]
            }
        }
    }
    """

    @staticmethod
    def plugin_to_openai(plugin: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Plugin to OpenAI Function format

        Args:
            plugin: {
                "plugin_id": "PL2026011510474128484",
                "name": "Real Calculator",
                "description": "Perform arithmetic calculations",
                "instruction": "Use this for math operations",
                "parameter": "{...}"  # JSON string or None
            }

        Returns:
            OpenAI function format dict
        """
        plugin_id = plugin.get("plugin_id", "unknown")
        name = plugin.get("name", "Unknown Plugin")
        description = plugin.get("description", "No description")
        instruction = plugin.get("instruction", "")
        parameter_json = plugin.get("parameter", "{}")

        # Build full description
        full_description = f"{name}: {description}"
        if instruction:
            full_description += f". {instruction}"

        # Parse parameters
        try:
            if isinstance(parameter_json, str):
                parameters = json.loads(parameter_json) if parameter_json else {}
            else:
                parameters = parameter_json or {}

            # Ensure it's valid OpenAI parameters format
            if not isinstance(parameters, dict):
                parameters = {}
            if "type" not in parameters:
                parameters["type"] = "object"
            if "properties" not in parameters:
                parameters["properties"] = {}

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse plugin {plugin_id} parameters, using empty object")
            parameters = {
                "type": "object",
                "properties": {}
            }

        return {
            "type": "function",
            "function": {
                "name": f"plugin_{plugin_id}",
                "description": full_description[:1024],  # OpenAI limit
                "parameters": parameters
            }
        }

    @staticmethod
    def mcp_to_openai(mcp: Dict[str, Any], tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert MCP tool to OpenAI Function format

        Args:
            mcp: {
                "mcp_id": "MC2026011511561554068",
                "name": "✓ Real Weather MCP Server",
                "description": "..."
            }
            tool: {
                "name": "get_weather",
                "description": "Get current weather information",
                "inputSchema": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }

        Returns:
            OpenAI function format dict
        """
        mcp_id = mcp.get("mcp_id", "unknown")
        mcp_name = mcp.get("name", "Unknown MCP")
        tool_name = tool.get("name", "unknown_tool")
        tool_description = tool.get("description", "No description")
        input_schema = tool.get("inputSchema", {})

        # Build full description
        full_description = f"{tool_description} (from {mcp_name})"

        # MCP's inputSchema is already in OpenAI format
        parameters = input_schema if input_schema else {
            "type": "object",
            "properties": {}
        }

        return {
            "type": "function",
            "function": {
                "name": f"mcp_{mcp_id}_{tool_name}",
                "description": full_description[:1024],
                "parameters": parameters
            }
        }

    @staticmethod
    def function_to_openai(function: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Function to OpenAI Function format

        Args:
            function: {
                "function_id": "FN2026011512345678901",
                "name": "greeting",
                "description": "Send greeting message",
                "instruction": "Use this to greet users",
                "parameter": "{...}"  # JSON string or None
            }

        Returns:
            OpenAI function format dict
        """
        function_id = function.get("function_id", "unknown")
        name = function.get("name", "Unknown Function")
        description = function.get("description", "No description")
        instruction = function.get("instruction", "")
        parameter_json = function.get("parameter", "{}")

        # Build full description
        full_description = f"{name}: {description}"
        if instruction:
            full_description += f". {instruction}"

        # Parse parameters
        try:
            if isinstance(parameter_json, str):
                parameters = json.loads(parameter_json) if parameter_json else {}
            else:
                parameters = parameter_json or {}

            if not isinstance(parameters, dict):
                parameters = {}
            if "type" not in parameters:
                parameters["type"] = "object"
            if "properties" not in parameters:
                parameters["properties"] = {}

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse function {function_id} parameters, using empty object")
            parameters = {
                "type": "object",
                "properties": {}
            }

        return {
            "type": "function",
            "function": {
                "name": f"function_{function_id}",
                "description": full_description[:1024],
                "parameters": parameters
            }
        }

    @staticmethod
    def skill_to_openai(skill: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Skill to OpenAI Function format

        Args:
            skill: {
                "skill_id": "SK2026011512345678901",
                "name": "screenshot",
                "description": "Take a screenshot",
                "instruction": "Use this to capture screen",
                "parameter": "{...}"  # JSON string or None
            }

        Returns:
            OpenAI function format dict
        """
        skill_id = skill.get("skill_id", "unknown")
        name = skill.get("name", "Unknown Skill")
        description = skill.get("description", "No description")
        instruction = skill.get("instruction", "")
        parameter_json = skill.get("parameter", "{}")

        # Build full description
        full_description = f"{name}: {description}"
        if instruction:
            full_description += f". {instruction}"

        # Parse parameters
        try:
            if isinstance(parameter_json, str):
                parameters = json.loads(parameter_json) if parameter_json else {}
            else:
                parameters = parameter_json or {}

            if not isinstance(parameters, dict):
                parameters = {}
            if "type" not in parameters:
                parameters["type"] = "object"
            if "properties" not in parameters:
                parameters["properties"] = {}

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse skill {skill_id} parameters, using empty object")
            parameters = {
                "type": "object",
                "properties": {}
            }

        return {
            "type": "function",
            "function": {
                "name": f"skill_{skill_id}",
                "description": full_description[:1024],
                "parameters": parameters
            }
        }

    @classmethod
    def convert_tools(cls, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert a list of mixed tool types to OpenAI format

        Args:
            tools: List of tool dicts with 'tool_type' field

        Returns:
            List of OpenAI function format dicts
        """
        openai_tools = []

        for tool in tools:
            tool_type = tool.get("tool_type")

            try:
                if tool_type == "plugin":
                    openai_tools.append(cls.plugin_to_openai(tool))

                elif tool_type == "mcp":
                    # MCP may have multiple tools
                    mcp_tools = tool.get("tools", [])
                    if isinstance(mcp_tools, list) and len(mcp_tools) > 0:
                        for mcp_tool in mcp_tools:
                            openai_tools.append(cls.mcp_to_openai(tool, mcp_tool))
                    else:
                        # If no tools list, create a generic tool entry
                        # The actual tools will be queried when the MCP is used
                        mcp_id = tool.get('mcp_id', 'unknown')
                        mcp_name = tool.get('name', 'Unknown MCP')
                        generic_tool = {
                            "name": "execute",
                            "description": f"Execute {mcp_name} MCP tool",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "tool_name": {
                                        "type": "string",
                                        "description": "The tool to execute"
                                    },
                                    "arguments": {
                                        "type": "object",
                                        "description": "Arguments for the tool"
                                    }
                                },
                                "required": ["tool_name"]
                            }
                        }
                        openai_tools.append(cls.mcp_to_openai(tool, generic_tool))

                elif tool_type == "function":
                    openai_tools.append(cls.function_to_openai(tool))

                elif tool_type == "skill":
                    openai_tools.append(cls.skill_to_openai(tool))

                else:
                    logger.warning(f"Unknown tool type: {tool_type}")

            except Exception as e:
                logger.error(f"Failed to convert tool {tool.get('name', 'unknown')}: {e}")

        return openai_tools

    @staticmethod
    def parse_function_name(function_name: str) -> tuple[str, str, Optional[str]]:
        """
        Parse OpenAI function name back to tool info

        Args:
            function_name: "plugin_{id}", "mcp_{id}_{tool}", "function_{id}", "skill_{id}"

        Returns:
            (tool_type, tool_id, tool_name)  # tool_name only for MCP
        """
        parts = function_name.split('_', 2)

        if len(parts) < 2:
            return ("unknown", "unknown", None)

        tool_type = parts[0]
        tool_id = parts[1]
        tool_name = parts[2] if len(parts) > 2 and tool_type == "mcp" else None

        return (tool_type, tool_id, tool_name)


# Example usage
if __name__ == "__main__":
    # Test plugin conversion
    plugin = {
        "plugin_id": "PL2026011510474128484",
        "name": "Real Calculator",
        "description": "Perform arithmetic calculations",
        "instruction": "Use this for math operations like 1+2, 10*5, etc.",
        "parameter": json.dumps({
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        })
    }

    result = ToolConverter.plugin_to_openai(plugin)
    print("Plugin conversion:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Test function name parsing
    print("\nFunction name parsing:")
    print(ToolConverter.parse_function_name("plugin_PL2026011510474128484"))
    print(ToolConverter.parse_function_name("mcp_MC2026011511561554068_get_weather"))
    print(ToolConverter.parse_function_name("function_FN123"))
    print(ToolConverter.parse_function_name("skill_SK456"))
