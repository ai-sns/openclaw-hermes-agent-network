"""
A2A Protocol Module

Implements Google's Agent-to-Agent (A2A) protocol for inter-agent communication.

Components:
- AgentCard: Agent discovery and capability advertisement
- TaskManager: Async task lifecycle management
- Handshake: Authentication and capability negotiation
- Router: API endpoints
"""

from agent_platform.protocols.a2a.agent_card import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    AuthenticationType,
    AuthenticationConfig,
    RateLimitConfig,
    EndpointConfig,
    SecurityScheme,
    ProviderInfo,
    AgentCardManager,
    get_agent_card_manager
)

from agent_platform.protocols.a2a.task_manager import (
    A2ATask,
    A2ATaskType,
    A2ATaskStatus,
    A2AMessage,
    A2ATaskManager,
    get_a2a_task_manager
)

from agent_platform.protocols.a2a.handshake import (
    HandshakeRequest,
    HandshakeResponse,
    HandshakeStatus,
    A2ASession,
    A2AHandshakeManager,
    get_handshake_manager
)

from agent_platform.protocols.a2a.router import a2a_router


__all__ = [
    # Agent Card
    "AgentCard",
    "AgentCapabilities",
    "AgentSkill",
    "AuthenticationType",
    "AuthenticationConfig",
    "RateLimitConfig",
    "EndpointConfig",
    "SecurityScheme",
    "ProviderInfo",
    "AgentCardManager",
    "get_agent_card_manager",

    # Task Manager
    "A2ATask",
    "A2ATaskType",
    "A2ATaskStatus",
    "A2AMessage",
    "A2ATaskManager",
    "get_a2a_task_manager",

    # Handshake
    "HandshakeRequest",
    "HandshakeResponse",
    "HandshakeStatus",
    "A2ASession",
    "A2AHandshakeManager",
    "get_handshake_manager",

    # Router
    "a2a_router"
]
