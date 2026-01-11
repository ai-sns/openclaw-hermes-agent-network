"""System configuration and management ORM models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base


class SystemCfg(Base):
    """System configuration model."""
    __tablename__ = 'system_cfg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    autorun = Column(Boolean, default=False, doc="Auto-run on startup")
    showtaskbar = Column(Boolean, default=False, doc="Show in taskbar")
    updateinfo = Column(Boolean, default=False, doc="Update notification")
    minirunontray = Column(Boolean, default=False, doc="Minimize to tray")
    closebuttontype = Column(String(100), doc="Close button behavior")
    style = Column(String(500), doc="UI style")
    showinfo = Column(Boolean, default=True, doc="Show notifications")
    showinfoicon = Column(Boolean, default=True, doc="Show notification icon")
    infosound = Column(Boolean, default=True, doc="Notification sound")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class LogsMng(Base):
    """Logs management model."""
    __tablename__ = 'logsmng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    logs_id = Column(String(100), doc="Log ID")
    content = Column(Text, doc="Log content")
    type = Column(String(200), doc="Log type")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class SysConfig(Base):
    """System config model."""
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lang = Column(String(20), doc="Language")


class SystemInit(Base):
    """System initialization model."""
    __tablename__ = 'system_init'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), doc="Name")
    avatar = Column(Text, doc="Avatar")
    password = Column(String(128), doc="Password")
    confirm_password = Column(String(128), doc="Confirm password")
    profile = Column(String(500), doc="Profile")
    llm = Column(String(100), doc="LLM")
    llm_server = Column(String(500), doc="LLM server URL")
    api_key = Column(String(200), doc="API key")
    avatar3d = Column(Text, doc="3D avatar")
    account = Column(String(128), doc="Account")
    account_password = Column(String(128), doc="Account password")
    sns_url = Column(Text, doc="SNS URL")
    map = Column(String, doc="Map")
    map_api_key = Column(String(128), doc="Map API key")
    map_id = Column(String(128), doc="Map ID")
    status = Column(Integer, doc="Status")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.utcnow, doc="Create time")


class KeyValue(Base):
    """Key-value storage model."""
    __tablename__ = 'key_value'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False, doc="Key")
    value = Column(String, nullable=False, doc="Value")


class PluginMng(Base):
    """Plugin management model."""
    __tablename__ = 'pluginmng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100), doc="Plugin ID")
    company = Column(String(200), doc="Company")
    company_abbr = Column(String(100), doc="Company abbreviation")
    name = Column(String(100), doc="Name")
    version = Column(String(100), doc="Version")
    alias_name = Column(String(100), doc="Alias name")
    filename = Column(String(200), doc="Filename")
    run_mode = Column(String(100), doc="Run mode")
    run_scope = Column(String(100), doc="Run scope")
    instruction = Column(String(100), doc="Instruction")
    runtime_main = Column(String(200), doc="Runtime main")
    runtime_test = Column(String(200), doc="Runtime test")
    description = Column(Text, doc="Description")
    plugin_directory = Column(String(100), doc="Plugin directory")
    plugin_type = Column(String(100), doc="Plugin type")
    plugin_executed = Column(String(100), doc="Plugin executed")
    plugin_event = Column(String(100), doc="Plugin event")
    plugin_title = Column(Text, doc="Plugin title")
    detail = Column(Text, doc="Detail")
    confirm_needed = Column(Boolean, default=True, doc="Confirm needed")
    can_be_sold = Column(Boolean, default=False, doc="Can be sold")
    used_in_sns = Column(Boolean, default=False, doc="Used in SNS")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class FunctionMng(Base):
    """Function management model."""
    __tablename__ = 'function_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    function_id = Column(String(100), doc="Function ID")
    name = Column(String(100), doc="Name")
    instruction = Column(String(100), doc="Instruction")
    file_path = Column(String(200), doc="File path")
    requirement = Column(Text, doc="Requirement")
    parameter = Column(Text, doc="Parameter")
    description = Column(String(100), doc="Description")
    detail = Column(Text, doc="Detail")
    function_type = Column(String(100), doc="Function type")
    function_event = Column(String(100), doc="Function event")
    confirm_needed = Column(Boolean, default=True, doc="Confirm needed")
    can_be_sold = Column(Boolean, default=False, doc="Can be sold")
    used_in_sns = Column(Boolean, default=False, doc="Used in SNS")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class McpMng(Base):
    """MCP management model."""
    __tablename__ = 'mcp_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    mcp_id = Column(String(100), doc="MCP ID")
    name = Column(String(100), doc="Name")
    instruction = Column(String(100), doc="Instruction")
    file_path = Column(String(200), doc="File path")
    requirement = Column(Text, doc="Requirement")
    parameter = Column(Text, doc="Parameter")
    description = Column(String(100), doc="Description")
    detail = Column(Text, doc="Detail")
    mcp_type = Column(String(100), doc="MCP type")
    mcp_event = Column(String(100), doc="MCP event")
    confirm_needed = Column(Boolean, default=True, doc="Confirm needed")
    can_be_sold = Column(Boolean, default=False, doc="Can be sold")
    used_in_sns = Column(Boolean, default=False, doc="Used in SNS")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class SkillMng(Base):
    """Skill management model."""
    __tablename__ = 'skill_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(String(100), doc="Skill ID")
    name = Column(String(100), doc="Name")
    instruction = Column(String(100), doc="Instruction")
    file_path = Column(String(200), doc="File path")
    requirement = Column(Text, doc="Requirement")
    parameter = Column(Text, doc="Parameter")
    description = Column(String(100), doc="Description")
    detail = Column(Text, doc="Detail")
    skill_type = Column(String(100), doc="Skill type")
    skill_event = Column(String(100), doc="Skill event")
    confirm_needed = Column(Boolean, default=True, doc="Confirm needed")
    can_be_sold = Column(Boolean, default=False, doc="Can be sold")
    used_in_sns = Column(Boolean, default=False, doc="Used in SNS")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class WebMng(Base):
    """Web management model."""
    __tablename__ = 'web_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    web_id = Column(String(100), doc="Web ID")
    name = Column(String(100), doc="Name")
    title = Column(String(100), doc="Title")
    type = Column(String(100), doc="Type")
    description = Column(Text, doc="Description")
    filename = Column(String(200), doc="Filename")
    url = Column(String(500), doc="URL")
    position = Column(Integer, default=999, doc="Position")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class WorkflowMng(Base):
    """Workflow management model."""
    __tablename__ = 'workflow_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(100), doc="Workflow ID")
    title = Column(String(100), doc="Title")
    description = Column(Text, doc="Description")
    instruction = Column(String(100), doc="Instruction")
    workflow_event = Column(String(100), doc="Workflow event")
    detail = Column(Text, doc="Detail")
    timer_desc = Column(String(200), doc="Timer description")
    timer_cron = Column(String(200), doc="Timer cron")
    run_agent_name = Column(String(200), doc="Run agent name")
    run_agent_id = Column(String(200), doc="Run agent ID")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class TaskSchedule(Base):
    """Task schedule model."""
    __tablename__ = 'task_schedule'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), doc="Title")
    description = Column(Text, doc="Description")
    task_type = Column(String(100), doc="Task type")
    task_id = Column(String(100), doc="Task ID")
    org_id = Column(String(100), doc="Original ID")
    parameter = Column(Text, doc="Parameter")
    schedule_time = Column(DateTime, doc="Schedule time")
    run_time = Column(DateTime, doc="Run time")
    run_result = Column(Text, doc="Run result")
    status = Column(String(100), default="0", doc="Status")
    timer_desc = Column(String(200), doc="Timer description")
    timer_cron = Column(String(200), doc="Timer cron")
    run_agent_name = Column(String(200), doc="Run agent name")
    run_agent_id = Column(String(200), doc="Run agent ID")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class Prompt(Base):
    """Prompt model."""
    __tablename__ = 'prompts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, doc="Title")
    content = Column(String, doc="Content")
    question = Column(String, doc="Question")
    tags = Column(String, doc="Tags")
    model_name = Column(String(100), doc="Model name")
    position = Column(Integer, doc="Position")
    prompt_frequents = relationship("PromptFrequent", back_populates="prompt")


class PromptFrequent(Base):
    """Prompt frequent model."""
    __tablename__ = 'prompt_frequent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String(100), ForeignKey('prompts.id'), doc="Prompt ID")
    title = Column(String(100), doc="Title")
    position = Column(Integer, doc="Position")
    belong_to_agent_id = Column(String(100), doc="Belong to agent ID")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=0, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    prompt = relationship("Prompt", back_populates="prompt_frequents")


class LlmFrequent(Base):
    """LLM frequent model."""
    __tablename__ = 'llm_frequent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100), doc="Plugin ID")
    name = Column(String(100), doc="Name")
    short_name = Column(String(100), doc="Short name")
    model_type = Column(String(100), doc="Model type")
    alias_name = Column(String(100), doc="Alias name")
    position = Column(Integer, doc="Position")
    belong_to_agent_id = Column(String(100), doc="Belong to agent ID")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class Question(Base):
    """Question model."""
    __tablename__ = 'question'

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String, doc="Question")
    tag = Column(String(20), doc="Tag")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class ModelMetrics(Base):
    """Model metrics model."""
    __tablename__ = 'model_metrics'

    id = Column(Integer, primary_key=True)
    connector_name = Column(String, doc="Connector name")
    model_name = Column(String, doc="Model name")
    price = Column(Float, doc="Price")
    speed = Column(Integer, doc="Speed")
    understanding = Column(Integer, doc="Understanding")
    summarizing = Column(Integer, doc="Summarizing")
    knowledge = Column(Integer, doc="Knowledge")
    logical_reasoning = Column(Integer, doc="Logical reasoning")
    math = Column(Integer, doc="Math")
    coding = Column(Integer, doc="Coding")
    writing = Column(Integer, doc="Writing")
    attachment = Column(Integer, doc="Attachment")
    image_recognition = Column(Integer, doc="Image recognition")
    image_generation = Column(Integer, doc="Image generation")
    video_generation = Column(Integer, doc="Video generation")
    video_recognition = Column(Integer, doc="Video recognition")
    searching = Column(Integer, doc="Searching")
    tool_ability = Column(String, doc="Tool ability")


class ToolList(Base):
    """Tool list view model."""
    __tablename__ = 'tool_list'

    id = Column(String, primary_key=True, doc="ID")
    name = Column(String, doc="Name")
    description = Column(Text, doc="Description")
    plugin_type = Column(String, doc="Plugin type")
    confirm_needed = Column(Boolean, doc="Confirm needed")
    can_be_sold = Column(Boolean, doc="Can be sold")


class LlmConfig(Base):
    """LLM model configuration."""
    __tablename__ = 'llm_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(String(50), unique=True, nullable=False, doc="Configuration unique ID")
    name = Column(String(100), nullable=False, doc="Display name")
    provider = Column(String(50), nullable=False, doc="Provider type: openai|claude|gemini|custom")
    plugin_id = Column(String(100), doc="Associated plugin ID")

    # Basic connection configuration
    api_endpoint = Column(String(500), doc="API endpoint URL")
    api_key = Column(Text, doc="API key (encrypted)")
    model_name = Column(String(100), doc="Model name")

    # Advanced parameters
    temperature = Column(Float, default=0.7, doc="Temperature (0-2)")
    max_tokens = Column(Integer, default=2048, doc="Max tokens")
    top_p = Column(Float, default=1.0, doc="Top P")
    frequency_penalty = Column(Float, default=0.0, doc="Frequency penalty")
    presence_penalty = Column(Float, default=0.0, doc="Presence penalty")
    stream = Column(Boolean, default=True, doc="Enable streaming")

    # Custom parameters (JSON format)
    custom_params = Column(Text, doc="Custom parameters in JSON")

    # Metadata
    description = Column(Text, doc="Description")
    is_active = Column(Boolean, default=True, doc="Is active")
    is_default = Column(Boolean, default=False, doc="Is default model")
    position = Column(Integer, default=9999, doc="Display position")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    update_time = Column(DateTime, onupdate=datetime.now, doc="Update time")


class RoleConfig(Base):
    """Role/Persona configuration."""
    __tablename__ = 'role_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(String(50), unique=True, nullable=False, doc="Role unique ID")
    name = Column(String(100), nullable=False, doc="Role name")
    display_name = Column(String(100), doc="Display name")

    # Prompt configuration
    system_prompt = Column(Text, nullable=False, doc="System prompt")
    greeting_message = Column(Text, doc="Greeting message")

    # Role attributes
    role_type = Column(String(50), doc="Role type: preset|custom")
    category = Column(String(50), doc="Category: developer|writer|analyst|assistant|other")
    avatar = Column(String(200), doc="Avatar URL or icon")

    # Metadata
    description = Column(Text, doc="Description")
    tags = Column(String(200), doc="Tags (comma separated)")
    is_active = Column(Boolean, default=True, doc="Is active")
    is_default = Column(Boolean, default=False, doc="Is default role")
    is_preset = Column(Boolean, default=False, doc="Is preset template")
    position = Column(Integer, default=9999, doc="Display position")
    usage_count = Column(Integer, default=0, doc="Usage count")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    update_time = Column(DateTime, onupdate=datetime.now, doc="Update time")
