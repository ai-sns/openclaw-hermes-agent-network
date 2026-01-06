"""
MCP Tool Connector

Implements Anthropic's Model Context Protocol (MCP) tool integration.
Provides tool registration, discovery, and invocation.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Callable, Awaitable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import inspect

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


logger = logging.getLogger(__name__)


class MCPToolCategory(str, Enum):
    """Tool categories"""
    UTILITY = "utility"
    DATA = "data"
    API = "api"
    FILE = "file"
    WEB = "web"
    CODE = "code"
    CUSTOM = "custom"


class MCPToolStatus(str, Enum):
    """Tool status"""
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


@dataclass
class MCPToolParameter:
    """Tool parameter definition"""
    name: str
    type: str  # string, number, boolean, object, array
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    category: MCPToolCategory = MCPToolCategory.UTILITY
    parameters: List[MCPToolParameter] = field(default_factory=list)
    returns: Dict[str, Any] = field(default_factory=dict)
    status: MCPToolStatus = MCPToolStatus.ACTIVE
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format"""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum
                }
                for p in self.parameters
            ],
            "returns": self.returns,
            "status": self.status.value,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "examples": self.examples
        }


@dataclass
class MCPToolResult:
    """Result of tool invocation"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


# Type for tool handlers
ToolHandler = Union[
    Callable[..., Any],
    Callable[..., Awaitable[Any]]
]


class MCPToolConnector:
    """
    MCP Tool Connector

    Central hub for tool management:
    - Tool registration and discovery
    - Parameter validation
    - Async/sync execution
    - Result caching
    """

    def __init__(self, enable_cache: bool = True, cache_ttl: int = 300):
        """
        Initialize tool connector.

        Args:
            enable_cache: Enable result caching
            cache_ttl: Cache TTL in seconds
        """
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl

        self._tools: Dict[str, MCPTool] = {}
        self._handlers: Dict[str, ToolHandler] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._invocation_count: Dict[str, int] = {}

    def register_tool(
        self,
        tool: MCPTool,
        handler: ToolHandler
    ) -> None:
        """
        Register a tool with its handler.

        Args:
            tool: Tool definition
            handler: Tool handler function (sync or async)
        """
        self._tools[tool.name] = tool
        self._handlers[tool.name] = handler
        self._invocation_count[tool.name] = 0

        logger.info(f"Registered MCP tool: {tool.name}")

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: MCPToolCategory = MCPToolCategory.UTILITY
    ) -> MCPTool:
        """
        Register a function as a tool.

        Automatically extracts parameters from function signature.

        Args:
            func: Function to register
            name: Tool name (default: function name)
            description: Tool description (default: docstring)
            category: Tool category

        Returns:
            Created MCPTool
        """
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip()

        # Extract parameters from signature
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'cls']:
                continue

            # Determine type
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "number",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                param_type = type_map.get(param.annotation, "string")

            # Determine if required
            required = param.default == inspect.Parameter.empty
            default = None if required else param.default

            parameters.append(MCPToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter: {param_name}",
                required=required,
                default=default
            ))

        tool = MCPTool(
            name=tool_name,
            description=tool_desc,
            category=category,
            parameters=parameters
        )

        self.register_tool(tool, func)
        return tool

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]
            del self._handlers[name]
            self._cache.pop(name, None)
            return True
        return False

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get tool by name"""
        return self._tools.get(name)

    def list_tools(
        self,
        category: Optional[MCPToolCategory] = None,
        status: Optional[MCPToolStatus] = None
    ) -> List[MCPTool]:
        """
        List all registered tools.

        Args:
            category: Filter by category
            status: Filter by status

        Returns:
            List of tools
        """
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if status:
            tools = [t for t in tools if t.status == status]

        return tools

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM function calling"""
        return [
            tool.to_schema()
            for tool in self._tools.values()
            if tool.status == MCPToolStatus.ACTIVE
        ]

    async def invoke_tool(
        self,
        name: str,
        params: Dict[str, Any],
        use_cache: bool = True
    ) -> MCPToolResult:
        """
        Invoke a tool.

        Args:
            name: Tool name
            params: Tool parameters
            use_cache: Use cached result if available

        Returns:
            MCPToolResult
        """
        if name not in self._tools:
            return MCPToolResult(
                tool_name=name,
                success=False,
                error=f"Tool not found: {name}"
            )

        tool = self._tools[name]
        handler = self._handlers[name]

        # Check cache
        if use_cache and self.enable_cache:
            cache_key = json.dumps(params, sort_keys=True)
            if name in self._cache and cache_key in self._cache[name]:
                cached = self._cache[name][cache_key]
                if (datetime.now() - cached["timestamp"]).seconds < self.cache_ttl:
                    return MCPToolResult(
                        tool_name=name,
                        success=True,
                        result=cached["result"],
                        execution_time_ms=0
                    )

        # Validate parameters
        validation_error = self._validate_params(tool, params)
        if validation_error:
            return MCPToolResult(
                tool_name=name,
                success=False,
                error=validation_error
            )

        # Execute
        start_time = datetime.now()
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Cache result
            if self.enable_cache:
                if name not in self._cache:
                    self._cache[name] = {}
                cache_key = json.dumps(params, sort_keys=True)
                self._cache[name][cache_key] = {
                    "result": result,
                    "timestamp": datetime.now()
                }

            self._invocation_count[name] += 1

            return MCPToolResult(
                tool_name=name,
                success=True,
                result=result,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Tool invocation failed: {name} - {e}")

            return MCPToolResult(
                tool_name=name,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )

    def invoke_tool_sync(
        self,
        name: str,
        params: Dict[str, Any],
        use_cache: bool = True
    ) -> MCPToolResult:
        """Synchronous tool invocation"""
        return asyncio.get_event_loop().run_until_complete(
            self.invoke_tool(name, params, use_cache)
        )

    def _validate_params(
        self,
        tool: MCPTool,
        params: Dict[str, Any]
    ) -> Optional[str]:
        """Validate tool parameters"""
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in params:
                return f"Missing required parameter: {param.name}"

        # Type validation (basic)
        type_validators = {
            "string": lambda x: isinstance(x, str),
            "number": lambda x: isinstance(x, (int, float)),
            "boolean": lambda x: isinstance(x, bool),
            "array": lambda x: isinstance(x, list),
            "object": lambda x: isinstance(x, dict)
        }

        for param in tool.parameters:
            if param.name in params:
                value = params[param.name]
                validator = type_validators.get(param.type)
                if validator and not validator(value):
                    return f"Invalid type for {param.name}: expected {param.type}"

                # Enum validation
                if param.enum and value not in param.enum:
                    return f"Invalid value for {param.name}: must be one of {param.enum}"

        return None

    def clear_cache(self, tool_name: Optional[str] = None):
        """Clear tool cache"""
        if tool_name:
            self._cache.pop(tool_name, None)
        else:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get connector statistics"""
        return {
            "total_tools": len(self._tools),
            "active_tools": len([t for t in self._tools.values() if t.status == MCPToolStatus.ACTIVE]),
            "cache_entries": sum(len(v) for v in self._cache.values()),
            "invocation_counts": self._invocation_count.copy()
        }


# Singleton instance
_tool_connector: Optional[MCPToolConnector] = None


def get_mcp_tool_connector() -> MCPToolConnector:
    """Get the MCP tool connector instance"""
    global _tool_connector
    if _tool_connector is None:
        _tool_connector = MCPToolConnector()
    return _tool_connector


# Decorator for registering tools
def mcp_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: MCPToolCategory = MCPToolCategory.UTILITY
):
    """
    Decorator to register a function as an MCP tool.

    Usage:
        @mcp_tool(name="my_tool", description="Does something useful")
        def my_function(param1: str, param2: int = 10):
            return {"result": param1 * param2}
    """
    def decorator(func: Callable) -> Callable:
        connector = get_mcp_tool_connector()
        connector.register_function(func, name, description, category)
        return func
    return decorator
