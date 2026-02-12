"""Database models package."""
from .agent import AgentCfg, AgentDocSkill, AgentTask, AgentTaskMulti, MutiAgentCfg
from .chat import AIChatMessages, AIFriend, AIChatInform, AiChatCfg, HumanChatCfg
from .km import KMCfg, KMData, NoteMng
from .map import (
    MapCfg, MapTask, MapTool, MapTrade, MapVisit,
    MapActivity, MapPresetMsg, ChatPresetMsg
)
from .system import (
    SystemCfg, LogsMng, SysConfig, SystemInit, KeyValue,
    PluginMng, FunctionMng, McpMng, SkillMng, WebMng, WorkflowMng,
    TaskSchedule, Prompt, PromptFrequent, LlmFrequent,
    Question, ModelMetrics, ToolList
)

__all__ = [
    # Agent models
    'AgentCfg', 'AgentDocSkill', 'AgentTask', 'AgentTaskMulti', 'MutiAgentCfg',

    # Chat models
    'AIChatMessages', 'AIFriend', 'AIChatInform', 'AiChatCfg', 'HumanChatCfg',

    # KM models
    'KMCfg', 'KMData', 'NoteMng',

    # Map models
    'MapCfg', 'MapTask', 'MapTool', 'MapTrade', 'MapVisit',
    'MapActivity', 'MapPresetMsg', 'ChatPresetMsg',

    # System models
    'SystemCfg', 'LogsMng', 'SysConfig', 'SystemInit', 'KeyValue',
    'PluginMng', 'FunctionMng', 'McpMng', 'SkillMng', 'WebMng', 'WorkflowMng',
    'TaskSchedule', 'Prompt', 'PromptFrequent', 'LlmFrequent',
    'Question', 'ModelMetrics', 'ToolList'
]
