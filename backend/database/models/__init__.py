"""Database models package."""
from .agent import AgentCfg, AgentDocSkill
from .chat import AIChatMessages, AIFriend, AiChatCfg
from .km import KMCfg, KMData, NoteMng
from .map import (
    MapTrade, MapVisit,
    MapActivity, MapPresetMsg
)
from .system import (
    SystemCfg, SystemInit, KeyValue,
    PluginMng, FunctionMng, McpMng, SkillMng, WebMng,
    Prompt, LlmConfig, RoleConfig
)

__all__ = [
    # Agent models
    'AgentCfg', 'AgentDocSkill',

    # Chat models
    'AIChatMessages', 'AIFriend', 'AiChatCfg',

    # KM models
    'KMCfg', 'KMData', 'NoteMng',

    # Map models
    'MapTrade', 'MapVisit',
    'MapActivity', 'MapPresetMsg',

    # System models
    'SystemCfg', 'SystemInit', 'KeyValue',
    'PluginMng', 'FunctionMng', 'McpMng', 'SkillMng', 'WebMng',
    'Prompt', 'LlmConfig', 'RoleConfig'
]
