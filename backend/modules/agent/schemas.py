# -*- coding: utf-8 -*-
"""
Agent module - Pydantic schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent configuration model with A2A protocol support"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = ""

    # Agent type
    agent_type: Optional[str] = "local"  # local|remote

    # Remote agent configuration
    framework: Optional[str] = ""  # Openclaw|Langchain|Autogen|Autogpt|Other
    framework_other: Optional[str] = ""  # When framework == 'Other'
    llm_provider: Optional[str] = ""
    model_description: Optional[str] = ""

    # LLM Configuration
    model_config_id: Optional[str] = None  # Reference to LLM config
    model: Optional[str] = "gpt-4"
    api_key: Optional[str] = ""
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048

    # Role Configuration
    role_id: Optional[str] = None  # Reference to role config
    system_prompt: Optional[str] = ""

    # A2A Protocol Fields (Google A2A v0.3)
    url: Optional[str] = ""  # Agent's A2A endpoint URL
    version: Optional[str] = "1.0.0"
    protocol_version: Optional[str] = "0.3"

    # Capabilities
    capabilities: Optional[Dict[str, Any]] = Field(default_factory=lambda: {
        "streaming": True,
        "pushNotifications": True,
        "stateTransitionHistory": False
    })

    # Skills
    skills: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    # Input/Output modes
    default_input_modes: Optional[List[str]] = Field(default_factory=lambda: ["text"])
    default_output_modes: Optional[List[str]] = Field(default_factory=lambda: ["text"])

    # Security
    security_schemes: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Provider information
    provider_organization: Optional[str] = "AI-SNS Platform"
    provider_url: Optional[str] = "https://ai-sns.com"

    # Documentation
    documentation_url: Optional[str] = ""
    icon_url: Optional[str] = ""

    # Status
    is_active: Optional[bool] = True


class AgentResponse(BaseModel):
    """Agent response model"""
    id: int
    name: str
    description: Optional[str] = ""
    agent_type: Optional[str] = "local"
    framework: Optional[str] = ""
    framework_other: Optional[str] = ""
    llm_provider: Optional[str] = ""
    model_description: Optional[str] = ""
    model: Optional[str] = "gpt-4"
    model_config_id: Optional[str] = None
    role_id: Optional[str] = None
    url: Optional[str] = ""
    is_active: Optional[bool] = True


class AgentUpdateConfig(BaseModel):
    """Agent update configuration model - all fields are optional"""
    name: Optional[str] = None
    description: Optional[str] = None

    # Agent type
    agent_type: Optional[str] = None

    # Remote agent configuration
    framework: Optional[str] = None
    framework_other: Optional[str] = None
    llm_provider: Optional[str] = None
    model_description: Optional[str] = None

    # LLM Configuration
    model_config_id: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # Role Configuration
    role_id: Optional[str] = None
    system_prompt: Optional[str] = None

    # A2A Protocol Fields
    url: Optional[str] = None
    version: Optional[str] = None
    protocol_version: Optional[str] = None

    # Capabilities
    capabilities: Optional[Dict[str, Any]] = None

    # Skills
    skills: Optional[List[Dict[str, Any]]] = None

    # Input/Output modes
    default_input_modes: Optional[List[str]] = None
    default_output_modes: Optional[List[str]] = None

    # Security
    security_schemes: Optional[Dict[str, Any]] = None

    # Provider information
    provider_organization: Optional[str] = None
    provider_url: Optional[str] = None

    # Documentation
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None

    # Status
    is_active: Optional[bool] = None


class AgentModelParamsUpdate(BaseModel):
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stream: Optional[bool] = None
    thinking_effort_enabled: Optional[bool] = None
    thinking_effort_level: Optional[str] = None
    custom_params: Optional[Dict[str, Any]] = None


class AgentA2ACard(BaseModel):
    """Agent A2A Card export model"""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocolVersion: str = "0.3"
    capabilities: Dict[str, Any]
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    securitySchemes: Dict[str, Any] = Field(default_factory=dict)
    security: List[Dict[str, List[str]]] = Field(default_factory=list)
    provider: Dict[str, str] = Field(default_factory=dict)
    documentationUrl: Optional[str] = None
    iconUrl: Optional[str] = None
