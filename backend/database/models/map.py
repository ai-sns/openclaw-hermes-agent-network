"""Map-related ORM models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from backend.config.database import Base


class MapCfg(Base):
    """Map configuration model."""
    __tablename__ = 'map_cfg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), doc="User ID")
    account = Column(String(100), doc="Account")
    password = Column(String(256), doc="Password hash")
    nickname = Column(String(100), doc="Nickname")
    sign = Column(String(200), doc="Signature")
    status = Column(String(100), doc="Status")
    humantakeover = Column(Integer, default=0, doc="Human takeover")
    name = Column(String(200), doc="Name")
    borndate = Column(DateTime, doc="Birth date")
    gender = Column(Integer, doc="Gender")
    area = Column(String(100), doc="Area")
    city = Column(String(100), doc="City")
    address = Column(String(200), doc="Address")
    mail = Column(String(100), doc="Email")
    imaccount = Column(String(100), doc="IM account")
    phone = Column(String(100), doc="Phone")
    organization = Column(String(200), doc="Organization")
    title = Column(String(100), doc="Title")
    orgposition = Column(String(100), doc="Position")
    memo = Column(String(200), doc="Memo")
    serveraddress = Column(String(100), doc="Server address")
    port = Column(Integer, doc="Port")
    ssl = Column(Boolean, doc="SSL")
    resource = Column(String(100), doc="Resource")
    proxyused = Column(Boolean, doc="Proxy used")
    proxyaddress = Column(String(100), doc="Proxy address")
    proxyport = Column(Integer, doc="Proxy port")
    proxyssl = Column(Boolean, doc="Proxy SSL")
    savepasswordlocal = Column(Boolean, doc="Save password locally")
    autoconnect = Column(Boolean, doc="Auto connect")
    sendreceipt = Column(Boolean, doc="Send receipt")
    sendreadflag = Column(Boolean, doc="Send read flag")
    sendchatstatus = Column(Boolean, doc="Send chat status")
    sendgroupchatstatus = Column(Boolean, doc="Send group chat status")
    agreeallfriendrequest = Column(Boolean, doc="Agree all friend requests")
    level = Column(Integer, doc="Level")
    credit = Column(Integer, doc="Credit")
    money = Column(Integer, default=0, doc="Money")
    token_unit = Column(String(100), doc="Token unit")
    growth = Column(Integer, doc="Growth")
    tech = Column(Integer, doc="Tech")
    knowledge = Column(Integer, doc="Knowledge")
    speed = Column(Integer, doc="Speed")
    Intelligence = Column(Integer, doc="Intelligence")
    init_address = Column(String(500), doc="Initial address")
    init_lng = Column(Float, doc="Initial longitude")
    init_lat = Column(Float, doc="Initial latitude")
    current_address = Column(String(500), doc="Current address")
    current_lng = Column(Float, doc="Current longitude")
    current_lat = Column(Float, doc="Current latitude")
    nation_id = Column(String(200), doc="Nation ID")
    avatar = Column(String(1000), doc="Avatar")
    talk_persons_concurrent_limit = Column(Integer, doc="Concurrent talk persons limit")
    talk_rounds_limit = Column(Integer, doc="Talk rounds limit")
    position = Column(Integer, default=9999, doc="Display position")
    is_show = Column(Boolean, default=True, doc="Is visible")
    is_delete = Column(Boolean, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class MapTask(Base):
    """Map task model."""
    __tablename__ = 'map_task'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), doc="Task ID")
    title = Column(String(500), doc="Title")
    detail = Column(Text, doc="Detail")
    result = Column(Text, doc="Result")
    sub_task_list = Column(Text, doc="Sub-task list")
    current_sub_task = Column(Text, doc="Current sub-task")
    process_info_list = Column(Text, doc="Process info list")
    current_place = Column(String(500), doc="Current place")
    current_position = Column(String(100), doc="Current position")
    task_summary = Column(Text, doc="Task summary")
    status = Column(Integer, default=0, doc="Status")
    rating = Column(Integer, doc="Rating")
    comment = Column(Text, doc="Comment")
    agent_id = Column(String(200), doc="Agent ID")
    model_name = Column(String(100), doc="Model name")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class MapTool(Base):
    """Map tool model."""
    __tablename__ = 'map_tool'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100), doc="Plugin ID")
    name = Column(String(100), doc="Name")
    plugin_title = Column(String(100), doc="Plugin title")
    plugin_type = Column(String(100), doc="Plugin type")
    instruction = Column(Text, doc="Instruction")
    description = Column(Text(200), doc="Description")
    run_mode = Column(String(100), doc="Run mode")
    run_scope = Column(String(100), doc="Run scope")
    plugin_directory = Column(String(100), doc="Plugin directory")
    plugin_executed = Column(String(100), doc="Plugin executed")
    plugin_event = Column(String(100), doc="Plugin event")
    detail = Column(Text(2000), doc="Detail")
    company = Column(String(200), doc="Company")
    company_abbr = Column(String(100), doc="Company abbreviation")
    version = Column(String(100), doc="Version")
    alias_name = Column(String(100), doc="Alias name")
    filename = Column(String(200), doc="Filename")
    runtime_main = Column(String(200), doc="Runtime main")
    runtime_test = Column(String(200), doc="Runtime test")
    get_from_name = Column(String(200), doc="Get from name")
    get_from_account = Column(String(200), doc="Get from account")
    get_time = Column(DateTime, default=datetime.now, doc="Get time")
    pay = Column(Float, default=100, doc="Pay")
    pay_method = Column(String(100), doc="Pay method")
    trade_id = Column(String(100), doc="Trade ID")
    confirm_needed = Column(Boolean, default=True, doc="Confirm needed")
    can_be_sold = Column(Boolean, default=False, doc="Can be sold")
    creator = Column(String(100), doc="Creator")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")


class MapTrade(Base):
    """Map trade model."""
    __tablename__ = 'map_trade'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(50), doc="Trade ID")
    trade_type = Column(String(100), doc="Trade type")
    title = Column(String(500), doc="Title")
    detail = Column(Text, doc="Detail")
    link = Column(Text, doc="Link")
    trade_with_name = Column(String(200), doc="Trade with name")
    trade_with_account = Column(String(200), doc="Trade with account")
    trade_with_company = Column(Boolean, default=False, doc="Trade with company")
    pay = Column(Float, default=100, doc="Pay")
    pay_method = Column(Text, default="as_coin", doc="Pay method")
    status = Column(Integer, default=0, doc="Status")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class MapVisit(Base):
    """Map visit model."""
    __tablename__ = 'map_visit'

    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String(50), doc="Visit ID")
    title = Column(String(500), doc="Title")
    detail = Column(Text, doc="Detail")
    place_type = Column(String(100), doc="Place type")
    address = Column(Text, doc="Address")
    lng = Column(Float, doc="Longitude")
    lat = Column(Float, doc="Latitude")
    url = Column(Text, doc="Place intro URL")
    coord_key = Column(String(80), doc="Normalized coordinate key")
    owner_name = Column(String(200), doc="Owner name")
    owner_account = Column(String(100), doc="Owner account")
    owner_type = Column(String(50), doc="Owner type")
    is_free = Column(Boolean, default=True, doc="Is free")
    trade_id = Column(String(100), doc="Trade ID")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class MapActivity(Base):
    """Map activity model."""
    __tablename__ = 'map_activity'

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(String(50), doc="Activity ID")
    content = Column(Text, doc="Content")
    type = Column(String(100), doc="Type")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class MapPresetMsg(Base):
    """Map preset message model."""
    __tablename__ = 'map_preset_msg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, doc="Content")
    position = Column(Integer, default=0, doc="Position")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class ChatPresetMsg(Base):
    """Chat preset message model."""
    __tablename__ = 'chat_preset_msg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, doc="Content")
    position = Column(Integer, default=0, doc="Position")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
