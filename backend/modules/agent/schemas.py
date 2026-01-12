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

    # Blockchain Wallet
    wallet_address: Optional[str] = ""  # Ethereum wallet address

    # Status
    is_active: Optional[bool] = True


class AgentResponse(BaseModel):
    """Agent response model"""
    id: int
    name: str
    description: Optional[str] = ""
    model: Optional[str] = "gpt-4"
    model_config_id: Optional[str] = None
    role_id: Optional[str] = None
    url: Optional[str] = ""
    wallet_address: Optional[str] = ""
    is_active: Optional[bool] = True


class AgentUpdateConfig(BaseModel):
    """Agent update configuration model - all fields are optional"""
    name: Optional[str] = None
    description: Optional[str] = None

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

    # Blockchain Wallet
    wallet_address: Optional[str] = None

    # Status
    is_active: Optional[bool] = None


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
