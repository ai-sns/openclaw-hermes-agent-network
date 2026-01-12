# -*- coding: utf-8 -*-
"""
Tool Executor - 工具执行器
负责加载和执行Agent的工具函数
"""
import logging
import importlib
import inspect
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    工具执行器

    负责:
    1. 从agent/tools.py加载工具函数
    2. 从插件加载工具
    3. 执行工具函数
    """

    def __init__(self):
        """初始化工具执行器"""
        self._tool_functions: Dict[str, callable] = {}
        self._load_builtin_tools()

    def _load_builtin_tools(self):
        """加载内置工具（从agent/tools.py）"""
        try:
            # 动态导入agent.tools模块
            tools_module = importlib.import_module('agent.tools')

            # 获取所有函数
            for name, obj in inspect.getmembers(tools_module):
                if inspect.isfunction(obj) and not name.startswith('_'):
                    self._tool_functions[name] = obj
                    logger.info(f"加载内置工具: {name}")

        except Exception as e:
            logger.error(f"加载内置工具失败: {e}")

    def load_plugin_tool(self, plugin_id: str, tool_function: callable):
        """
        加载插件工具

        Args:
            plugin_id: 插件ID
            tool_function: 工具函数
        """
        tool_name = f"plugin_{plugin_id}_{tool_function.__name__}"
        self._tool_functions[tool_name] = tool_function
        logger.info(f"加载插件工具: {tool_name}")

    def load_custom_tool(self, tool_name: str, tool_function: callable):
        """
        加载自定义工具

        Args:
            tool_name: 工具名称
            tool_function: 工具函数
        """
        self._tool_functions[tool_name] = tool_function
        logger.info(f"加载自定义工具: {tool_name}")

    def get_tool_function(self, tool_name: str) -> Optional[callable]:
        """
        获取工具函数

        Args:
            tool_name: 工具名称

        Returns:
            工具函数，不存在返回None
        """
        return self._tool_functions.get(tool_name)

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        执行工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        try:
            tool_func = self.get_tool_function(tool_name)
            if not tool_func:
                return f"Error: Tool '{tool_name}' not found"

            # 执行工具
            result = tool_func(**kwargs)
            logger.info(f"工具 {tool_name} 执行成功")
            return result

        except Exception as e:
            logger.error(f"工具执行失败: {e}", exc_info=True)
            return f"Error executing tool '{tool_name}': {str(e)}"

    def get_tool_signature(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具的签名信息（用于生成OpenAI function calling schema）

        Args:
            tool_name: 工具名称

        Returns:
            工具签名字典
        """
        try:
            tool_func = self.get_tool_function(tool_name)
            if not tool_func:
                return None

            sig = inspect.signature(tool_func)
            params = {}
            required = []

            for param_name, param in sig.parameters.items():
                # 获取类型注解
                param_type = "string"  # 默认类型
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"

                params[param_name] = {
                    "type": param_type,
                    "description": ""  # 可以从docstring解析
                }

                # 如果没有默认值，则为必需参数
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            # 获取函数文档字符串作为描述
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
            logger.error(f"获取工具签名失败: {e}")
            return None

    def list_tools(self) -> List[str]:
        """
        列出所有可用工具

        Returns:
            工具名称列表
        """
        return list(self._tool_functions.keys())


# 创建全局单例
tool_executor = ToolExecutor()
