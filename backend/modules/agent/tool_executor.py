# -*- coding: utf-8 -*-
"""
Tool Executor - Tool executor
Responsible for loading and executing agent tool functions
"""
import logging
import importlib
import inspect
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool executor

    Responsibilities:
    1. Load tool functions from agent/tools.py
    2. Load tools from plugins
    3. Execute tool functions
    """

    def __init__(self):
        """Initialize tool executor."""
        self._tool_functions: Dict[str, callable] = {}
        self._load_builtin_tools()

    def _load_builtin_tools(self):
        """Load built-in tools (from agent/tools.py)."""
        try:
            module_name = f"{__package__}.tools" if __package__ else "backend.modules.agent.tools"
            tools_module = importlib.import_module(module_name)

            # Get all functions
            for name, obj in inspect.getmembers(tools_module):
                if inspect.isfunction(obj) and not name.startswith('_'):
                    self._tool_functions[name] = obj
                    logger.info(f"Loaded built-in tool: {name}")

        except ModuleNotFoundError as e:
            module_name = f"{__package__}.tools" if __package__ else "backend.modules.agent.tools"
            if e.name == module_name or e.name == "agent":
                logger.warning(f"Built-in tools module not found: {module_name}")
                return
            logger.error(f"Failed to load built-in tools: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to load built-in tools: {e}", exc_info=True)

    def load_plugin_tool(self, plugin_id: str, tool_function: callable):
        """
        Load a plugin tool.

        Args:
            plugin_id: Plugin ID
            tool_function: Tool function
        """
        tool_name = f"plugin_{plugin_id}_{tool_function.__name__}"
        self._tool_functions[tool_name] = tool_function
        logger.info(f"Loaded plugin tool: {tool_name}")

    def load_custom_tool(self, tool_name: str, tool_function: callable):
        """
        Load a custom tool.

        Args:
            tool_name: Tool name
            tool_function: Tool function
        """
        self._tool_functions[tool_name] = tool_function
        logger.info(f"Loaded custom tool: {tool_name}")

    def get_tool_function(self, tool_name: str) -> Optional[callable]:
        """
        Get tool function.

        Args:
            tool_name: Tool name

        Returns:
            Tool function; returns None if not found
        """
        return self._tool_functions.get(tool_name)

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute tool.

        Args:
            tool_name: Tool name
            **kwargs: Tool args

        Returns:
            Tool execution result
        """
        try:
            tool_func = self.get_tool_function(tool_name)
            if not tool_func:
                return f"Error: Tool '{tool_name}' not found"

            # Execute tool
            result = tool_func(**kwargs)
            logger.info(f"Tool {tool_name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return f"Error executing tool '{tool_name}': {str(e)}"

    def get_tool_signature(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get tool signature info (for building OpenAI function-calling schema).

        Args:
            tool_name: Tool name

        Returns:
            Tool signature dict
        """
        try:
            tool_func = self.get_tool_function(tool_name)
            if not tool_func:
                return None

            sig = inspect.signature(tool_func)
            params = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Read type annotation
                param_type = "string"  # Default type
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"

                params[param_name] = {
                    "type": param_type,
                    "description": ""  # Can be parsed from docstring
                }

                # If no default value, this is a required param
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            # Use function docstring as description
            description = tool_func.__doc__ or f"Execute {tool_name}"

            return {
                "name": tool_name,
                "description": description.strip(),
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": required
                }
            }

        except Exception as e:
            logger.error(f"Failed to get tool signature: {e}")
            return None

    def list_tools(self) -> List[str]:
        """
        List all available tools.

        Returns:
            Tool name list
        """
        return list(self._tool_functions.keys())


# Create global singleton
tool_executor = ToolExecutor()
