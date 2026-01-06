"""
A2A Agent Card

Implements Google's Agent-to-Agent (A2A) protocol Agent Card specification (v0.3).
Agent Cards provide standardized agent discovery and capability advertisement.

Fully compatible with Google A2A Protocol:
- https://github.com/google/A2A
- Protocol Version: 0.3
"""

import json
import os
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


# ============== Enums ==============

class AuthenticationType(str, Enum):
    """Supported authentication types"""
    API_KEY = "apiKey"
    OAUTH2 = "oauth2"
    HTTP = "http"
    NONE = "none"


class AgentCapabilityType(str, Enum):
    """Standard agent capability types (legacy)"""
    CHAT = "chat"
    STREAMING = "streaming"
    ASYNC_TASK = "async_task"
    FILE_UPLOAD = "file_upload"
    TOOL_USE = "tool_use"
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"
    IMAGE_GENERATION = "image_generation"
    VOICE = "voice"
    VISION = "vision"


class InputMode(str, Enum):
    """Supported input modes (Google A2A spec)"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"


class OutputMode(str, Enum):
    """Supported output modes (Google A2A spec)"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"


# ============== Google A2A Spec Models ==============

class AgentSkill(BaseModel):
    """
    Agent Skill definition (Google A2A spec).

    Represents a specific capability or function the agent can perform.
    """
    id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    description: Optional[str] = Field(None, description="Skill description")
    tags: List[str] = Field(default_factory=list, description="Skill tags for categorization")
    examples: List[str] = Field(default_factory=list, description="Example prompts")
    inputModes: List[str] = Field(
        default_factory=lambda: [InputMode.TEXT.value],
        description="Supported input modes"
    )
    outputModes: List[str] = Field(
        default_factory=lambda: [OutputMode.TEXT.value],
        description="Supported output modes"
    )

    model_config = ConfigDict(populate_by_name=True)


class AgentCapabilities(BaseModel):
    """
    Agent Capabilities (Google A2A spec).

    Structured capabilities object instead of simple list.
    """
    streaming: bool = Field(default=True, description="Supports streaming responses")
    pushNotifications: bool = Field(default=True, description="Supports webhook notifications")
    stateTransitionHistory: bool = Field(default=False, description="Records state transitions")

    model_config = ConfigDict(populate_by_name=True)


class OAuthFlows(BaseModel):
    """OAuth2 flows configuration"""
    authorizationCode: Optional[Dict[str, Any]] = None
    clientCredentials: Optional[Dict[str, Any]] = None
    implicit: Optional[Dict[str, Any]] = None
    password: Optional[Dict[str, Any]] = None


class SecurityScheme(BaseModel):
    """
    Security Scheme (OpenAPI 3.0 compatible, Google A2A spec).
    """
    type: str = Field(..., description="Security scheme type: apiKey, oauth2, http")
    in_location: str = Field(
        default="header",
        alias="in",
        description="Location: header, query, cookie"
    )
    name: Optional[str] = Field(None, description="Name of the header/query parameter")
    scheme: Optional[str] = Field(None, description="HTTP auth scheme: bearer, basic")
    bearerFormat: Optional[str] = Field(None, description="Bearer token format hint")
    flows: Optional[OAuthFlows] = Field(None, description="OAuth2 flows")
    description: Optional[str] = Field(None, description="Security scheme description")

    model_config = ConfigDict(populate_by_name=True)


class ProviderInfo(BaseModel):
    """
    Provider Information (Google A2A spec).
    """
    organization: str = Field(..., description="Organization name")
    url: Optional[str] = Field(None, description="Organization URL")

    model_config = ConfigDict(populate_by_name=True)


# ============== Legacy Models (backward compatibility) ==============

class AuthenticationConfig(BaseModel):
    """Authentication configuration (legacy format)"""
    type: AuthenticationType = AuthenticationType.API_KEY
    header_name: str = "X-API-Key"
    token_url: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_day: int = 10000
    tokens_per_minute: int = 100000


class EndpointConfig(BaseModel):
    """API endpoint configuration (legacy format)"""
    base_url: str
    chat_path: str = "/api/v1/chat"
    stream_path: str = "/api/v1/chat/stream"
    task_path: str = "/api/v1/tasks"
    websocket_path: str = "/ws"
    a2a_path: str = "/a2a"


# ============== Agent Card (Google A2A v0.3 Compatible) ==============

class AgentCard(BaseModel):
    """
    A2A Agent Card (Google A2A Protocol v0.3 compatible)

    Standardized agent discovery format based on Google's A2A protocol.
    Provides all information needed for agent-to-agent communication.

    Reference: https://github.com/google/A2A/blob/main/specification/json/a2a.json
    """
    # Required fields (Google A2A spec)
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(default="", description="Agent description")
    url: str = Field(..., description="Agent's A2A endpoint URL")

    # Protocol version
    version: str = Field(default="1.0.0", description="Agent version")
    protocolVersion: str = Field(default="0.3", description="A2A protocol version")

    # Capabilities (Google A2A spec - structured object)
    capabilities: AgentCapabilities = Field(
        default_factory=AgentCapabilities,
        description="Agent capabilities"
    )

    # Skills (Google A2A spec - structured list)
    skills: List[AgentSkill] = Field(
        default_factory=list,
        description="List of skills this agent can perform"
    )

    # Input/Output modes (Google A2A spec)
    defaultInputModes: List[str] = Field(
        default_factory=lambda: [InputMode.TEXT.value],
        description="Default input modes"
    )
    defaultOutputModes: List[str] = Field(
        default_factory=lambda: [OutputMode.TEXT.value],
        description="Default output modes"
    )

    # Security (OpenAPI 3.0 compatible, Google A2A spec)
    securitySchemes: Dict[str, SecurityScheme] = Field(
        default_factory=dict,
        description="Security schemes"
    )
    security: List[Dict[str, List[str]]] = Field(
        default_factory=list,
        description="Security requirements"
    )

    # Provider info (Google A2A spec)
    provider: Optional[ProviderInfo] = Field(
        None,
        description="Provider information"
    )

    # Documentation URLs
    documentationUrl: Optional[str] = Field(None, description="Documentation URL")
    iconUrl: Optional[str] = Field(None, description="Agent icon URL")

    # Legacy fields (for backward compatibility)
    id: Optional[str] = Field(None, description="Unique agent identifier (legacy)")
    endpoint: Optional[EndpointConfig] = Field(None, description="Endpoint config (legacy)")
    authentication: Optional[AuthenticationConfig] = Field(None, description="Auth config (legacy)")
    rate_limits: Optional[RateLimitConfig] = Field(None, description="Rate limits (legacy)")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="Model information")

    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(indent=2, exclude_none=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_google_a2a_format(self) -> Dict[str, Any]:
        """
        Convert to Google A2A spec format.

        Returns a dictionary that conforms to the official Google A2A specification.
        """
        result = {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "protocolVersion": self.protocolVersion,
            "capabilities": self.capabilities.model_dump(),
            "defaultInputModes": self.defaultInputModes,
            "defaultOutputModes": self.defaultOutputModes,
        }

        # Add skills
        if self.skills:
            result["skills"] = [skill.model_dump() for skill in self.skills]

        # Add security schemes
        if self.securitySchemes:
            result["securitySchemes"] = {
                k: v.model_dump(by_alias=True, exclude_none=True)
                for k, v in self.securitySchemes.items()
            }

        # Add security requirements
        if self.security:
            result["security"] = self.security

        # Add provider
        if self.provider:
            result["provider"] = self.provider.model_dump()

        # Add optional fields
        if self.documentationUrl:
            result["documentationUrl"] = self.documentationUrl
        if self.iconUrl:
            result["iconUrl"] = self.iconUrl

        return result

    @classmethod
    def from_agent(
        cls,
        agent,
        base_url: str,
        agent_id: Optional[str] = None
    ) -> "AgentCard":
        """
        Create AgentCard from an Agent instance.

        Args:
            agent: Agent instance
            base_url: Base URL for the API
            agent_id: Optional agent ID override

        Returns:
            AgentCard instance
        """
        # Get agent config
        config = getattr(agent, 'cfg', {})
        if isinstance(config, dict):
            agent_name = config.get('name', 'AI Agent')
            agent_desc = config.get('description', '')
            model_name = config.get('llm_model', 'unknown')
        else:
            agent_name = getattr(config, 'name', 'AI Agent')
            agent_desc = getattr(config, 'description', '')
            model_name = getattr(config, 'llm_model', 'unknown')

        # Build capabilities
        capabilities = AgentCapabilities(
            streaming=True,
            pushNotifications=True,
            stateTransitionHistory=False
        )

        # Build skills from tools
        skills = []
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                tool_name = getattr(tool, 'name', str(tool))
                skill = AgentSkill(
                    id=tool_name.lower().replace(' ', '-'),
                    name=tool_name,
                    description=getattr(tool, 'description', ''),
                    tags=["tool"],
                    inputModes=[InputMode.TEXT.value],
                    outputModes=[OutputMode.TEXT.value]
                )
                skills.append(skill)

        # Default chat skill
        if not skills:
            skills.append(AgentSkill(
                id="chat",
                name="General Chat",
                description="General conversation and Q&A",
                tags=["conversation", "qa"],
                examples=["Hello!", "What can you do?"],
                inputModes=[InputMode.TEXT.value],
                outputModes=[OutputMode.TEXT.value]
            ))

        # Check for code execution and add skill
        if hasattr(agent, 'code_executor') or hasattr(agent, 'enable_code_execution'):
            skills.append(AgentSkill(
                id="code-execution",
                name="Code Execution",
                description="Execute Python code safely",
                tags=["code", "python"],
                inputModes=[InputMode.TEXT.value, InputMode.FILE.value],
                outputModes=[OutputMode.TEXT.value, OutputMode.FILE.value]
            ))

        # Build security schemes
        security_schemes = {
            "apiKey": SecurityScheme(
                type="apiKey",
                in_location="header",
                name="X-API-Key",
                description="API Key authentication"
            )
        }

        return cls(
            id=agent_id or getattr(agent, 'agent_id', 'default'),
            name=agent_name,
            description=agent_desc,
            url=f"{base_url}/a2a",
            capabilities=capabilities,
            skills=skills,
            defaultInputModes=[InputMode.TEXT.value],
            defaultOutputModes=[OutputMode.TEXT.value],
            securitySchemes=security_schemes,
            security=[{"apiKey": []}],
            provider=ProviderInfo(
                organization="AI-SNS Platform",
                url="https://ai-sns.com"
            ),
            endpoint=EndpointConfig(base_url=base_url),
            model_info={
                "model": model_name,
                "provider": "AI-SNS Platform"
            }
        )

    @classmethod
    def from_legacy_format(
        cls,
        legacy_data: Dict[str, Any]
    ) -> "AgentCard":
        """
        Create AgentCard from legacy format.

        Converts old-style Agent Card to new Google A2A compatible format.
        """
        # Extract base URL
        endpoint = legacy_data.get("endpoint", {})
        base_url = endpoint.get("base_url", "http://localhost:8000")

        # Convert capabilities list to object
        cap_list = legacy_data.get("capabilities", [])
        capabilities = AgentCapabilities(
            streaming="streaming" in cap_list,
            pushNotifications="async_task" in cap_list or "webhook" in cap_list,
            stateTransitionHistory=False
        )

        # Convert skills
        old_skills = legacy_data.get("skills", [])
        skills = []
        for old_skill in old_skills:
            skills.append(AgentSkill(
                id=old_skill.get("name", "unknown").lower().replace(" ", "-"),
                name=old_skill.get("name", "Unknown"),
                description=old_skill.get("description", ""),
                tags=[],
                inputModes=[InputMode.TEXT.value],
                outputModes=[OutputMode.TEXT.value]
            ))

        # Convert authentication to security schemes
        auth = legacy_data.get("authentication", {})
        security_schemes = {}
        if auth.get("type") == "api_key":
            security_schemes["apiKey"] = SecurityScheme(
                type="apiKey",
                in_location="header",
                name=auth.get("header_name", "X-API-Key")
            )

        return cls(
            name=legacy_data.get("name", "AI Agent"),
            description=legacy_data.get("description", ""),
            url=f"{base_url}/a2a",
            version=legacy_data.get("version", "1.0.0"),
            capabilities=capabilities,
            skills=skills,
            securitySchemes=security_schemes,
            security=[{"apiKey": []}] if security_schemes else [],
            id=legacy_data.get("id"),
            model_info=legacy_data.get("model_info", {})
        )


class AgentCardManager:
    """
    Agent Card Manager

    Manages agent cards for discovery and registration.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize manager.

        Args:
            base_url: Base URL for the platform
        """
        self.base_url = base_url
        self._cards: Dict[str, AgentCard] = {}

    def register_card(self, card: AgentCard) -> None:
        """Register an agent card"""
        self._cards[card.id] = card
        card.updated_at = datetime.now()

    def get_card(self, agent_id: str) -> Optional[AgentCard]:
        """Get an agent card by ID"""
        return self._cards.get(agent_id)

    def list_cards(self) -> List[AgentCard]:
        """List all registered agent cards"""
        return list(self._cards.values())

    def remove_card(self, agent_id: str) -> bool:
        """Remove an agent card"""
        if agent_id in self._cards:
            del self._cards[agent_id]
            return True
        return False

    def register_from_agent(
        self,
        agent,
        agent_id: Optional[str] = None
    ) -> AgentCard:
        """
        Register an agent card from an Agent instance.

        Args:
            agent: Agent instance
            agent_id: Optional agent ID override

        Returns:
            Created AgentCard
        """
        card = AgentCard.from_agent(agent, self.base_url, agent_id)
        self.register_card(card)
        return card

    def generate_well_known_json(self, agent_id: str = "default") -> str:
        """
        Generate .well-known/agent.json content.

        Args:
            agent_id: Agent ID to export

        Returns:
            JSON string for agent.json
        """
        card = self._cards.get(agent_id)
        if not card:
            # Return default card
            card = AgentCard(
                id="default",
                name="AI-SNS Agent",
                description="AI Agent Open Platform",
                endpoint=EndpointConfig(base_url=self.base_url),
                capabilities=[
                    AgentCapability.CHAT.value,
                    AgentCapability.STREAMING.value,
                    AgentCapability.ASYNC_TASK.value,
                    AgentCapability.FILE_UPLOAD.value
                ]
            )

        return card.to_json()

    def save_agent_json(
        self,
        output_path: str,
        agent_id: str = "default"
    ) -> str:
        """
        Save agent.json to file.

        Args:
            output_path: Output file path
            agent_id: Agent ID to export

        Returns:
            Path to saved file
        """
        json_content = self.generate_well_known_json(agent_id)

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_content)

        return output_path


# Singleton instance
_card_manager: Optional[AgentCardManager] = None


def get_agent_card_manager(base_url: str = "http://localhost:8000") -> AgentCardManager:
    """Get the agent card manager instance"""
    global _card_manager
    if _card_manager is None:
        _card_manager = AgentCardManager(base_url)
    return _card_manager
