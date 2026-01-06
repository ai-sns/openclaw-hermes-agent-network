"""
MCP Context Injector

Injects context (resources, tools, history) into LLM prompts.
Implements the context management aspect of MCP.
"""

import json
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context that can be injected"""
    SYSTEM = "system"
    RESOURCE = "resource"
    TOOL = "tool"
    HISTORY = "history"
    MEMORY = "memory"
    INSTRUCTION = "instruction"
    EXAMPLE = "example"


class ContextPriority(str, Enum):
    """Context priority levels"""
    CRITICAL = "critical"  # Always include
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class ContextItem:
    """A single context item"""
    context_id: str
    context_type: ContextType
    content: str
    priority: ContextPriority = ContextPriority.NORMAL
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "context_id": self.context_id,
            "context_type": self.context_type.value,
            "content": self.content,
            "priority": self.priority.value,
            "token_estimate": self.token_estimate,
            "metadata": self.metadata,
            "source": self.source,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class InjectionResult:
    """Result of context injection"""
    system_prompt: str
    context_items: List[ContextItem]
    total_tokens: int
    truncated: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPContextInjector:
    """
    MCP Context Injector

    Manages context injection for LLM prompts:
    - System prompts
    - Resource context
    - Tool descriptions
    - Conversation history
    - Memory/knowledge retrieval
    """

    def __init__(
        self,
        max_context_tokens: int = 8000,
        token_estimator: Optional[callable] = None
    ):
        """
        Initialize context injector.

        Args:
            max_context_tokens: Maximum tokens for context
            token_estimator: Custom token estimation function
        """
        self.max_context_tokens = max_context_tokens
        self.token_estimator = token_estimator or self._default_token_estimator

        self._context_items: Dict[str, ContextItem] = {}
        self._templates: Dict[str, str] = {}

        # Initialize default templates
        self._init_default_templates()

    def _init_default_templates(self):
        """Initialize default context templates"""
        self._templates = {
            "system_default": """You are a helpful AI assistant with access to various tools and resources.
{tool_context}
{resource_context}
{custom_instructions}""",

            "tool_list": """Available Tools:
{tools}

To use a tool, respond with a tool call in the following format:
```tool
{{"name": "tool_name", "parameters": {{"param1": "value1"}}}}
```""",

            "resource_context": """Available Resources:
{resources}

You can reference these resources in your responses.""",

            "conversation_history": """Previous conversation:
{history}""",

            "memory_context": """Relevant memories:
{memories}"""
        }

    def _default_token_estimator(self, text: str) -> int:
        """Default token estimation (approx 4 chars per token)"""
        return len(text) // 4

    def add_template(self, name: str, template: str):
        """Add or update a context template"""
        self._templates[name] = template

    def get_template(self, name: str) -> Optional[str]:
        """Get a context template"""
        return self._templates.get(name)

    def add_context(
        self,
        context_id: str,
        context_type: ContextType,
        content: str,
        priority: ContextPriority = ContextPriority.NORMAL,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextItem:
        """
        Add a context item.

        Args:
            context_id: Unique context ID
            context_type: Type of context
            content: Context content
            priority: Priority level
            source: Source of the context
            metadata: Additional metadata

        Returns:
            Created ContextItem
        """
        token_estimate = self.token_estimator(content)

        item = ContextItem(
            context_id=context_id,
            context_type=context_type,
            content=content,
            priority=priority,
            token_estimate=token_estimate,
            source=source,
            metadata=metadata or {}
        )

        self._context_items[context_id] = item
        return item

    def remove_context(self, context_id: str) -> bool:
        """Remove a context item"""
        if context_id in self._context_items:
            del self._context_items[context_id]
            return True
        return False

    def clear_context(self, context_type: Optional[ContextType] = None):
        """Clear context items"""
        if context_type:
            to_remove = [
                cid for cid, item in self._context_items.items()
                if item.context_type == context_type
            ]
            for cid in to_remove:
                del self._context_items[cid]
        else:
            self._context_items.clear()

    def inject_context(
        self,
        base_prompt: str = "",
        include_types: Optional[List[ContextType]] = None,
        exclude_types: Optional[List[ContextType]] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        resources: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        custom_instructions: str = ""
    ) -> InjectionResult:
        """
        Inject context into a prompt.

        Args:
            base_prompt: Base system prompt
            include_types: Context types to include (None = all)
            exclude_types: Context types to exclude
            max_tokens: Override max tokens
            tools: Tool definitions to inject
            resources: Resource definitions to inject
            history: Conversation history
            custom_instructions: Custom instructions

        Returns:
            InjectionResult with assembled prompt
        """
        max_tokens = max_tokens or self.max_context_tokens
        included_items: List[ContextItem] = []
        total_tokens = 0
        truncated = False

        # Filter and sort context items by priority
        items = list(self._context_items.values())

        if include_types:
            items = [i for i in items if i.context_type in include_types]

        if exclude_types:
            items = [i for i in items if i.context_type not in exclude_types]

        # Sort by priority
        priority_order = {
            ContextPriority.CRITICAL: 0,
            ContextPriority.HIGH: 1,
            ContextPriority.NORMAL: 2,
            ContextPriority.LOW: 3
        }
        items.sort(key=lambda x: priority_order.get(x.priority, 2))

        # Add items within token budget
        for item in items:
            if total_tokens + item.token_estimate <= max_tokens:
                included_items.append(item)
                total_tokens += item.token_estimate
            else:
                truncated = True
                # Still include critical items
                if item.priority == ContextPriority.CRITICAL:
                    included_items.append(item)
                    total_tokens += item.token_estimate

        # Build tool context
        tool_context = ""
        if tools:
            tool_lines = []
            for tool in tools:
                tool_lines.append(f"- {tool['name']}: {tool.get('description', '')}")
            tool_context = self._templates["tool_list"].format(
                tools="\n".join(tool_lines)
            )

        # Build resource context
        resource_context = ""
        if resources:
            resource_lines = []
            for res in resources:
                resource_lines.append(f"- {res['name']}: {res.get('description', '')}")
            resource_context = self._templates["resource_context"].format(
                resources="\n".join(resource_lines)
            )

        # Build history context
        history_context = ""
        if history:
            history_lines = []
            for msg in history[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]  # Truncate long messages
                history_lines.append(f"{role}: {content}")
            history_context = self._templates["conversation_history"].format(
                history="\n".join(history_lines)
            )

        # Build custom context from items
        custom_context_parts = []
        for item in included_items:
            custom_context_parts.append(f"[{item.context_type.value}] {item.content}")

        # Assemble system prompt
        if base_prompt:
            system_prompt = base_prompt
        else:
            system_prompt = self._templates["system_default"].format(
                tool_context=tool_context,
                resource_context=resource_context,
                custom_instructions=custom_instructions
            )

        # Add custom context
        if custom_context_parts:
            system_prompt += "\n\n" + "\n".join(custom_context_parts)

        # Add history
        if history_context:
            system_prompt += "\n\n" + history_context

        return InjectionResult(
            system_prompt=system_prompt,
            context_items=included_items,
            total_tokens=total_tokens,
            truncated=truncated,
            metadata={
                "tool_count": len(tools) if tools else 0,
                "resource_count": len(resources) if resources else 0,
                "history_length": len(history) if history else 0
            }
        )

    def inject_for_agent(
        self,
        agent,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> InjectionResult:
        """
        Inject context for an agent.

        Args:
            agent: Agent instance
            message: Current user message
            history: Conversation history

        Returns:
            InjectionResult
        """
        # Get tools from agent
        tools = []
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                tools.append({
                    "name": getattr(tool, 'name', str(tool)),
                    "description": getattr(tool, 'description', '')
                })

        # Get resources from MCP resource manager
        from agent_platform.protocols.mcp.resource_manager import get_mcp_resource_manager
        resource_manager = get_mcp_resource_manager()
        resources = [
            {"name": r.name, "description": r.description}
            for r in resource_manager._resources.values()
            if r.status.value == "available"
        ]

        # Get agent config for custom instructions
        custom_instructions = ""
        if hasattr(agent, 'cfg'):
            cfg = agent.cfg
            if isinstance(cfg, dict):
                custom_instructions = cfg.get('system_prompt', '')
            else:
                custom_instructions = getattr(cfg, 'system_prompt', '')

        return self.inject_context(
            tools=tools,
            resources=resources,
            history=history,
            custom_instructions=custom_instructions
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get injector statistics"""
        type_counts = {}
        priority_counts = {}
        total_tokens = 0

        for item in self._context_items.values():
            type_counts[item.context_type.value] = type_counts.get(
                item.context_type.value, 0
            ) + 1
            priority_counts[item.priority.value] = priority_counts.get(
                item.priority.value, 0
            ) + 1
            total_tokens += item.token_estimate

        return {
            "total_items": len(self._context_items),
            "total_tokens": total_tokens,
            "max_tokens": self.max_context_tokens,
            "type_counts": type_counts,
            "priority_counts": priority_counts,
            "templates": list(self._templates.keys())
        }


# Singleton instance
_context_injector: Optional[MCPContextInjector] = None


def get_mcp_context_injector() -> MCPContextInjector:
    """Get the MCP context injector instance"""
    global _context_injector
    if _context_injector is None:
        _context_injector = MCPContextInjector()
    return _context_injector
