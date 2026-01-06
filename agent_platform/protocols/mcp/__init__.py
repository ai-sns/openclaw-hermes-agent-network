"""
MCP Protocol Module

Implements Anthropic's Model Context Protocol (MCP) for tool and resource management.

Components:
- ToolConnector: Tool registration, discovery, and invocation
- ResourceManager: External resource management
- ContextInjector: Context injection for LLM prompts
- Router: API endpoints
"""

from agent_platform.protocols.mcp.tool_connector import (
    MCPTool,
    MCPToolParameter,
    MCPToolCategory,
    MCPToolStatus,
    MCPToolResult,
    MCPToolConnector,
    get_mcp_tool_connector,
    mcp_tool
)

from agent_platform.protocols.mcp.resource_manager import (
    MCPResource,
    MCPResourceType,
    MCPResourceStatus,
    ResourceQuery,
    MCPResourceManager,
    get_mcp_resource_manager
)

from agent_platform.protocols.mcp.context_injector import (
    ContextItem,
    ContextType,
    ContextPriority,
    InjectionResult,
    MCPContextInjector,
    get_mcp_context_injector
)

from agent_platform.protocols.mcp.router import mcp_router


__all__ = [
    # Tool Connector
    "MCPTool",
    "MCPToolParameter",
    "MCPToolCategory",
    "MCPToolStatus",
    "MCPToolResult",
    "MCPToolConnector",
    "get_mcp_tool_connector",
    "mcp_tool",

    # Resource Manager
    "MCPResource",
    "MCPResourceType",
    "MCPResourceStatus",
    "ResourceQuery",
    "MCPResourceManager",
    "get_mcp_resource_manager",

    # Context Injector
    "ContextItem",
    "ContextType",
    "ContextPriority",
    "InjectionResult",
    "MCPContextInjector",
    "get_mcp_context_injector",

    # Router
    "mcp_router"
]
