"""Agent-related ORM models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from backend.config.database import Base


class AgentCfg(Base):
    """Agent configuration model."""
    __tablename__ = 'agent_cfg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), doc="User ID")
    name = Column(String(200), doc="Agent name")
    memo = Column(String(200), doc="Memo")
    borndate = Column(DateTime, default=datetime.now, doc="Birth date")
    borncontry = Column(String(100), doc="Birth country")
    language = Column(String(100), doc="Language")
    gender = Column(Integer, doc="Gender")
    joinfederation = Column(Boolean, default=False, doc="Join federation")
    syncfederation = Column(Boolean, default=False, doc="Sync federation")
    federationid = Column(String(150), doc="Federation ID")
    defaultmodel = Column(String(200), doc="Default model")
    defaultrole = Column(String(200), doc="Default role")
    lastmodel = Column(String(200), doc="Last model")
    lastrole = Column(String(200), doc="Last role")
    specialization = Column(Text, doc="Specialization")
    plugins = Column(Text, doc="Plugins")
    kms = Column(Text, doc="Knowledge bases")
    last_plugins = Column(Text, doc="Last plugins")
    last_kms = Column(Text, doc="Last knowledge bases")
    prompt = Column(Text, doc="System prompt")
    snsaccount = Column(String(100), doc="SNS account")
    snsnickname = Column(String(100), doc="SNS nickname")
    islimittotalmessage = Column(Boolean, default=True, doc="Limit total messages")
    islimitmessagepp = Column(Boolean, default=True, doc="Limit messages per person")
    totalmessages = Column(Integer, doc="Total messages")
    ppmessages = Column(Integer, doc="Messages per person")
    readfile = Column(Boolean, default=True, doc="Can read files")
    writefile = Column(Boolean, default=True, doc="Can write files")
    deletefile = Column(Boolean, default=True, doc="Can delete files")
    execfile = Column(Boolean, default=True, doc="Can execute files")
    uselastmodel = Column(Boolean, default=False, doc="Use last model")
    uselastrole = Column(Boolean, default=False, doc="Use last role")
    uselastplugins = Column(Boolean, default=False, doc="Use last plugins")
    uselastkms = Column(Boolean, default=False, doc="Use last KMs")
    callpluginbyinstruct = Column(Boolean, default=True, doc="Call plugin by instruction")
    modelfrequent = Column(Boolean, default=False, doc="Model frequent")
    rolefrequent = Column(Boolean, default=False, doc="Role frequent")
    multimodelfrequent = Column(Boolean, default=False, doc="Multi-model frequent")
    multimodellastmodel = Column(String(500), doc="Multi-model last model")
    multimodellastrole = Column(String(100), doc="Multi-model last role")
    autorunrounds = Column(Integer, doc="Auto run rounds")
    position = Column(Integer, default=9999, doc="Display position")
    is_show = Column(Boolean, default=True, doc="Is visible")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class AgentDocSkill(Base):
    __tablename__ = 'agent_doc_skills'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, nullable=False)
    skill_key = Column(String(200), nullable=False)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)


class AgentTask(Base):
    """Single agent task model."""
    __tablename__ = 'agent_task'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), doc="Task ID")
    title = Column(String(500), default=None, doc="Title")
    problem = Column(Text, doc="Problem/Question")
    answer = Column(Text, doc="Answer")
    attachment_list = Column(Text, doc="Attachment list")
    document_content = Column(Text, doc="Document content")
    image_json = Column(Text, doc="Image JSON")
    km_list = Column(Text, doc="Knowledge base list")
    km_content = Column(Text, doc="Knowledge base content")
    model_name = Column(String(100), doc="Model name")
    agent_id = Column(String(200), doc="Agent ID")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    is_first = Column(Boolean, default=False, doc="Is first message")
    stick_time = Column(DateTime, nullable=True, doc="Stick time")
    label = Column(String(50), doc="Category label")


class AgentTaskMulti(Base):
    """Multi-agent task model."""
    __tablename__ = 'agent_task_multi'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), doc="Task ID")
    topic = Column(String(500), default=None, doc="Topic")
    content = Column(Text, doc="Content")
    owner = Column(String(100), doc="Content owner")
    group_id = Column(String(200), doc="Group ID")
    attachment_list = Column(Text, doc="Attachment list")
    document_content = Column(Text, doc="Document content")
    image_json = Column(Text, doc="Image JSON")
    km_list = Column(Text, doc="Knowledge base list")
    km_content = Column(Text, doc="Knowledge base content")
    model_name = Column(String(100), doc="Model name")
    agent_id = Column(String(200), doc="Agent ID")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    is_first = Column(Boolean, default=False, doc="Is first message")
    stick_time = Column(DateTime, nullable=True, doc="Stick time")
    label = Column(String(50), doc="Category label")


class MutiAgentCfg(Base):
    """Multi-agent configuration model."""
    __tablename__ = 'mutiagent_cfg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(100), doc="Group ID")
    name = Column(String(200), doc="Group name")
    memo = Column(String(200), doc="Memo")
    agents = Column(Text, doc="Participating agents")
    agentcommander = Column(String(500), doc="Agent commander")
    specialization = Column(String(100), doc="Specialization")
    plugins = Column(String(500), doc="Plugins")
    kms = Column(String(500), doc="Knowledge bases")
    prompt = Column(Text, doc="System prompt")
    islimittotalmessage = Column(Boolean, default=True, doc="Limit total messages")
    islimitmessagepp = Column(Boolean, default=True, doc="Limit messages per person")
    totalmessages = Column(Integer, doc="Total messages")
    ppmessages = Column(Integer, doc="Messages per person")
    readfile = Column(Boolean, default=True, doc="Can read files")
    writefile = Column(Boolean, default=True, doc="Can write files")
    deletefile = Column(Boolean, default=True, doc="Can delete files")
    execfile = Column(Boolean, default=True, doc="Can execute files")
    autorunrounds = Column(Integer, doc="Auto run rounds")
    position = Column(Integer, default=9999, doc="Display position")
    is_show = Column(Boolean, default=True, doc="Is visible")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
