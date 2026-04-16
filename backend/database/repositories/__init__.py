"""Database repositories package."""
from .base import BaseRepository
from .agent_repository import (
    AgentCfgRepository,
)
from .chat_repository import (
    AIChatMessagesRepository,
    AIFriendRepository,
    AiChatCfgRepository
)
from .km_repository import (
    KMCfgRepository,
    KMDataRepository,
    NoteMngRepository
)
from .map_repository import (
    MapTradeRepository,
    MapVisitRepository,
    MapActivityRepository,
    MapPresetMsgRepository
)
from .system_repository import (
    SystemCfgRepository,
    SystemInitRepository,
    KeyValueRepository,
    PluginMngRepository,
    FunctionMngRepository,
    McpMngRepository,
    SkillMngRepository,
    WebMngRepository,
    PromptRepository,
    LlmConfigRepository,
    RoleConfigRepository
)

__all__ = [
    # Base
    'BaseRepository',

    # Agent repositories
    'AgentCfgRepository',

    # Chat repositories
    'AIChatMessagesRepository',
    'AIFriendRepository',
    'AiChatCfgRepository',

    # KM repositories
    'KMCfgRepository',
    'KMDataRepository',
    'NoteMngRepository',

    # Map repositories
    'MapTradeRepository',
    'MapVisitRepository',
    'MapActivityRepository',
    'MapPresetMsgRepository',

    # System repositories
    'SystemCfgRepository',
    'SystemInitRepository',
    'KeyValueRepository',
    'PluginMngRepository',
    'FunctionMngRepository',
    'McpMngRepository',
    'SkillMngRepository',
    'WebMngRepository',
    'PromptRepository',
    'LlmConfigRepository',
    'RoleConfigRepository'
]
