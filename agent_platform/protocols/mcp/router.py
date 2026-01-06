"""
MCP Protocol Router

API routes for Model Context Protocol (MCP) endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from agent_platform.protocols.mcp.tool_connector import (
    MCPTool,
    MCPToolParameter,
    MCPToolCategory,
    MCPToolStatus,
    MCPToolResult,
    get_mcp_tool_connector
)
from agent_platform.protocols.mcp.resource_manager import (
    MCPResource,
    MCPResourceType,
    MCPResourceStatus,
    ResourceQuery,
    get_mcp_resource_manager
)
from agent_platform.protocols.mcp.context_injector import (
    ContextItem,
    ContextType,
    ContextPriority,
    get_mcp_context_injector
)
from agent_platform.gateway.middleware.auth import get_current_api_key
from agent_platform.security.api_key import APIKeyInfo


# Router
mcp_router = APIRouter(prefix="/mcp", tags=["MCP Protocol"])


# Request/Response Models
class ToolRegistrationRequest(BaseModel):
    """Tool registration request"""
    name: str
    description: str
    category: str = "utility"
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)


class ToolInvocationRequest(BaseModel):
    """Tool invocation request"""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    use_cache: bool = True


class ToolResponse(BaseModel):
    """Tool response model"""
    name: str
    description: str
    category: str
    parameters: List[Dict[str, Any]]
    status: str
    version: str


class ToolResultResponse(BaseModel):
    """Tool result response"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0


class ResourceRegistrationRequest(BaseModel):
    """Resource registration request"""
    name: str
    resource_type: str
    uri: str
    description: str = ""
    mime_type: str = "application/octet-stream"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    load_content: bool = False


class ResourceResponse(BaseModel):
    """Resource response model"""
    resource_id: str
    name: str
    resource_type: str
    uri: str
    description: str
    mime_type: str
    size_bytes: int
    status: str
    tags: List[str]


class ContextInjectionRequest(BaseModel):
    """Context injection request"""
    base_prompt: str = ""
    include_types: Optional[List[str]] = None
    exclude_types: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    history: Optional[List[Dict[str, str]]] = None
    custom_instructions: str = ""


class ContextItemRequest(BaseModel):
    """Context item request"""
    context_id: str
    context_type: str
    content: str
    priority: str = "normal"
    source: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Tool Endpoints
@mcp_router.get("/tools", response_model=List[ToolResponse])
async def list_tools(
    category: Optional[str] = None,
    status: str = "active"
):
    """List all registered tools"""
    connector = get_mcp_tool_connector()

    # Map string to enum
    category_enum = None
    if category:
        try:
            category_enum = MCPToolCategory(category)
        except ValueError:
            pass

    status_enum = MCPToolStatus.ACTIVE
    try:
        status_enum = MCPToolStatus(status)
    except ValueError:
        pass

    tools = connector.list_tools(category=category_enum, status=status_enum)

    return [
        ToolResponse(
            name=tool.name,
            description=tool.description,
            category=tool.category.value,
            parameters=[
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required
                }
                for p in tool.parameters
            ],
            status=tool.status.value,
            version=tool.version
        )
        for tool in tools
    ]


@mcp_router.get("/tools/schemas")
async def get_tool_schemas():
    """Get all tool schemas for LLM function calling"""
    connector = get_mcp_tool_connector()
    return connector.get_tool_schemas()


@mcp_router.get("/tools/{tool_name}", response_model=ToolResponse)
async def get_tool(tool_name: str):
    """Get tool by name"""
    connector = get_mcp_tool_connector()
    tool = connector.get_tool(tool_name)

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    return ToolResponse(
        name=tool.name,
        description=tool.description,
        category=tool.category.value,
        parameters=[
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required
            }
            for p in tool.parameters
        ],
        status=tool.status.value,
        version=tool.version
    )


@mcp_router.post("/tools/{tool_name}/invoke", response_model=ToolResultResponse)
async def invoke_tool(
    tool_name: str,
    request: ToolInvocationRequest,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Invoke a tool"""
    connector = get_mcp_tool_connector()

    result = await connector.invoke_tool(
        name=tool_name,
        params=request.parameters,
        use_cache=request.use_cache
    )

    return ToolResultResponse(
        tool_name=result.tool_name,
        success=result.success,
        result=result.result,
        error=result.error,
        execution_time_ms=result.execution_time_ms
    )


@mcp_router.post("/tools/register", response_model=ToolResponse)
async def register_tool(
    request: ToolRegistrationRequest,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Register a new tool (requires handler to be set separately)"""
    connector = get_mcp_tool_connector()

    # Map category
    try:
        category = MCPToolCategory(request.category)
    except ValueError:
        category = MCPToolCategory.CUSTOM

    # Create parameters
    parameters = [
        MCPToolParameter(
            name=p.get("name", ""),
            type=p.get("type", "string"),
            description=p.get("description", ""),
            required=p.get("required", False),
            default=p.get("default")
        )
        for p in request.parameters
    ]

    tool = MCPTool(
        name=request.name,
        description=request.description,
        category=category,
        parameters=parameters,
        version=request.version,
        tags=request.tags
    )

    # Register with a placeholder handler
    def placeholder_handler(**kwargs):
        return {"message": "Handler not implemented"}

    connector.register_tool(tool, placeholder_handler)

    return ToolResponse(
        name=tool.name,
        description=tool.description,
        category=tool.category.value,
        parameters=[
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required
            }
            for p in tool.parameters
        ],
        status=tool.status.value,
        version=tool.version
    )


@mcp_router.delete("/tools/{tool_name}")
async def unregister_tool(
    tool_name: str,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Unregister a tool"""
    connector = get_mcp_tool_connector()

    if connector.unregister_tool(tool_name):
        return {"success": True, "message": f"Tool {tool_name} unregistered"}
    else:
        raise HTTPException(status_code=404, detail="Tool not found")


# Resource Endpoints
@mcp_router.get("/resources", response_model=List[ResourceResponse])
async def list_resources(
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
    name_contains: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0
):
    """List resources"""
    manager = get_mcp_resource_manager()

    # Build query
    query = ResourceQuery(
        limit=limit,
        offset=offset,
        name_contains=name_contains
    )

    if resource_type:
        try:
            query.resource_type = MCPResourceType(resource_type)
        except ValueError:
            pass

    if status:
        try:
            query.status = MCPResourceStatus(status)
        except ValueError:
            pass

    if tags:
        query.tags = tags.split(",")

    resources = await manager.query_resources(query)

    return [
        ResourceResponse(
            resource_id=r.resource_id,
            name=r.name,
            resource_type=r.resource_type.value,
            uri=r.uri,
            description=r.description,
            mime_type=r.mime_type,
            size_bytes=r.size_bytes,
            status=r.status.value,
            tags=r.tags
        )
        for r in resources
    ]


@mcp_router.get("/resources/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str):
    """Get resource by ID"""
    manager = get_mcp_resource_manager()
    resource = await manager.get_resource(resource_id)

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    return ResourceResponse(
        resource_id=resource.resource_id,
        name=resource.name,
        resource_type=resource.resource_type.value,
        uri=resource.uri,
        description=resource.description,
        mime_type=resource.mime_type,
        size_bytes=resource.size_bytes,
        status=resource.status.value,
        tags=resource.tags
    )


@mcp_router.get("/resources/{resource_id}/content")
async def get_resource_content(resource_id: str, force_reload: bool = False):
    """Get resource content"""
    manager = get_mcp_resource_manager()
    resource = await manager.get_resource(resource_id)

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    content = await manager.load_resource_content(resource, force=force_reload)

    return {
        "resource_id": resource_id,
        "content": content,
        "mime_type": resource.mime_type,
        "size_bytes": resource.size_bytes
    }


@mcp_router.post("/resources", response_model=ResourceResponse)
async def register_resource(
    request: ResourceRegistrationRequest,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Register a new resource"""
    manager = get_mcp_resource_manager()

    try:
        resource_type = MCPResourceType(request.resource_type)
    except ValueError:
        resource_type = MCPResourceType.CUSTOM

    resource = await manager.register_resource(
        name=request.name,
        resource_type=resource_type,
        uri=request.uri,
        description=request.description,
        mime_type=request.mime_type,
        metadata=request.metadata,
        tags=request.tags,
        load_content=request.load_content
    )

    return ResourceResponse(
        resource_id=resource.resource_id,
        name=resource.name,
        resource_type=resource.resource_type.value,
        uri=resource.uri,
        description=resource.description,
        mime_type=resource.mime_type,
        size_bytes=resource.size_bytes,
        status=resource.status.value,
        tags=resource.tags
    )


@mcp_router.delete("/resources/{resource_id}")
async def delete_resource(
    resource_id: str,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Delete a resource"""
    manager = get_mcp_resource_manager()

    if await manager.delete_resource(resource_id):
        return {"success": True, "message": "Resource deleted"}
    else:
        raise HTTPException(status_code=404, detail="Resource not found")


# Context Endpoints
@mcp_router.post("/context/inject")
async def inject_context(request: ContextInjectionRequest):
    """Inject context into a prompt"""
    injector = get_mcp_context_injector()

    # Map include/exclude types
    include_types = None
    if request.include_types:
        include_types = []
        for t in request.include_types:
            try:
                include_types.append(ContextType(t))
            except ValueError:
                pass

    exclude_types = None
    if request.exclude_types:
        exclude_types = []
        for t in request.exclude_types:
            try:
                exclude_types.append(ContextType(t))
            except ValueError:
                pass

    result = injector.inject_context(
        base_prompt=request.base_prompt,
        include_types=include_types,
        exclude_types=exclude_types,
        max_tokens=request.max_tokens,
        tools=request.tools,
        resources=request.resources,
        history=request.history,
        custom_instructions=request.custom_instructions
    )

    return {
        "system_prompt": result.system_prompt,
        "total_tokens": result.total_tokens,
        "truncated": result.truncated,
        "context_items": [item.to_dict() for item in result.context_items],
        "metadata": result.metadata
    }


@mcp_router.post("/context/add")
async def add_context_item(
    request: ContextItemRequest,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Add a context item"""
    injector = get_mcp_context_injector()

    try:
        context_type = ContextType(request.context_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid context type")

    try:
        priority = ContextPriority(request.priority)
    except ValueError:
        priority = ContextPriority.NORMAL

    item = injector.add_context(
        context_id=request.context_id,
        context_type=context_type,
        content=request.content,
        priority=priority,
        source=request.source,
        metadata=request.metadata
    )

    return item.to_dict()


@mcp_router.delete("/context/{context_id}")
async def remove_context_item(
    context_id: str,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Remove a context item"""
    injector = get_mcp_context_injector()

    if injector.remove_context(context_id):
        return {"success": True, "message": "Context item removed"}
    else:
        raise HTTPException(status_code=404, detail="Context item not found")


@mcp_router.delete("/context")
async def clear_context(
    context_type: Optional[str] = None,
    key_info: APIKeyInfo = Depends(get_current_api_key)
):
    """Clear context items"""
    injector = get_mcp_context_injector()

    type_enum = None
    if context_type:
        try:
            type_enum = ContextType(context_type)
        except ValueError:
            pass

    injector.clear_context(type_enum)
    return {"success": True, "message": "Context cleared"}


# Stats endpoint
@mcp_router.get("/stats")
async def get_mcp_stats():
    """Get MCP protocol statistics"""
    tool_connector = get_mcp_tool_connector()
    resource_manager = get_mcp_resource_manager()
    context_injector = get_mcp_context_injector()

    return {
        "tools": tool_connector.get_stats(),
        "resources": resource_manager.get_stats(),
        "context": context_injector.get_stats()
    }
