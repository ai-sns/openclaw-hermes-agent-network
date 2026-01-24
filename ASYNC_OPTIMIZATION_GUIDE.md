# AI Social Engine Adapter 异步优化实施指南

## 实施步骤

### 第一步：安装异步依赖

```bash
pip install sqlalchemy[asyncio] aiosqlite httpx
```

### 第二步：修改数据库配置

**文件：`backend/config/database.py`**

```python
"""
Database Configuration - 异步版本
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import logging

from .settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# SQLAlchemy Base
Base = declarative_base()

# 异步数据库 URL
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{settings.database.full_path}"

# 创建异步引擎
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.debug
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入 - 异步数据库会话
    """
    async with AsyncSessionLocal() as session:
        yield session


def init_db():
    """初始化数据库表（同步）"""
    try:
        # 导入所有模型以注册到 Base
        from backend.database.models import agent, chat, km, map, system

        # 创建所有表
        Base.metadata.create_all(bind=engine.sync_engine if hasattr(engine, 'sync_engine') else engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def close_db():
    """关闭数据库连接"""
    dispose_coro = engine.dispose() if hasattr(engine, 'dispose') else None
    if dispose_coro:
        # 异步关闭
        import asyncio
        asyncio.create_task(dispose_coro)
    logger.info("Database connection closed")
```

---

### 第三步：修改 `ai_social_engine_adapter.py`

#### 3.1 添加异步导入和替换 requests

```python
# 在文件开头修改导入
import asyncio
import httpx  # 替换 requests
from sqlalchemy.ext.asyncio import AsyncSession  # 替换 Session
from sqlalchemy import select  # 用于异步查询

# 删除：from sqlalchemy.orm import Session
```

#### 3.2 修改 `__init__` 和添加 `async_init`

```python
class AISocialEngine:
    """
    Backend adapter for AI Social Engine - 异步版本
    """

    def __init__(self, db: AsyncSession):
        """初始化（不包含数据库操作）"""
        self.db = db
        self.started_flag = False
        self.map_task_status = ""
        self.current_place = None
        self.process_list = []
        self.ability_list = []
        self.task_runner = None
        self.taskmng_js = JsTaskManager(self)
        self.taskmng = MapTaskManager(self)

        # 初始化其他属性（不包含数据库查询）
        self.config = None
        self.ai_chat_cfg = None
        self.aichatcfg_record = None

        # ... 其他同步初始化代码 ...
        self.human_take_over = False
        self.human_instruction = ""
        self.stopping_ai_process_flag = False
        self.pause_flag = False
        self.agent_replying_flag = False

        # ... 其他属性初始化 ...
        self.conversation_id = ""
        self.messages = []
        self.messages_command = []
        self.page_index = 0
        self.map_mode = 'org'
        self.personList = ["My_Agent", "wangwang"]
        self.agent = None
        self.kmselectedList = []
        self.pluginselectedList = []
        self.current_received_msg = ""
        self.messages = []
        self.is_browser_page_loaded = False
        self.first_event = None
        self.first_reply = ""
        self.chess_role = None
        self.chinese_chess_role = None
        self.system_role_prompt = "You are a helpful assistant who provides concise and accurate information."

        # 初始化全局变量
        self.user_map_setting = None
        self.current_place = ""
        self.current_position = []
        self.last_position = []
        self.target_position = None
        self.target_place = ""
        self.move_by_route_flag = False
        self.route_position_list = []
        self.ability_list = [
            {
                "function_name": "【activity_find_people_from_list_to_talk】",
                "function_description": "从人员名单中查找合适的人进行沟通，当你需要别人的帮助，需要别人给你指引的时候可以选择该功能，筛选人员不允许分多步骤筛选",
                "status": "enabled"
            },
            {
                "function_name": "【activity_find_place_from_list_to_move】",
                "function_description": "从地点列表中查找合适的地方作为目的地，当你需要去某个地方的时候可以选择该功能，筛选地方不允许分多步骤筛选",
                "status": "enabled"
            },
            {
                "function_name": "【activity_find_tool_from_list_to_use】",
                "function_description": "使用该功能可以从工具列表中查找合适的工具来调用系统服务、使用AI技能，解决其他功能解决不了的问题。筛选工具不允许分多步骤筛选。",
                "status": "enabled"
            }
        ]
        self.skill_list = []
        self.started_flag = False
        self.command_status = ""
        self.required_skills = []
        self.available_skills = []
        self.route_flag = False
        self.token_balance = 0

        self.taskmng_js = JsTaskManager(self)
        self.taskmng = MapTaskManager(self)

        self.people_list_to_ask_for_help = []
        self.current_talk_people = None
        self.asking_people_for_help_flag = False
        self.talk_history = {}
        self.current_talk_history = []
        self.people_talking_list = []

        self.thinking_step_index = 0
        self.process_step_index = 0
        self.place_selected = None
        self.max_tool_usage = 4
        self.max_people_comm = 4
        self.max_rounds_per_person = 6
        self.max_place_arrived = 3
        self.min_place_move_score = 80
        self.search_radius = 10000
        self.place_arrived_count = {}
        self.wait_for_trade_download_flag = False
        self.wait_for_trade_download_trade_id = ""
        self.command_list = []
        self.current_command_index = -1
        self.updown_message_index = -1
        self.temp_index = 0
        self.temp_index_2 = 0
        self.current_action = ""
        self.action_result = ""
        self.current_task_list = ""
        self.current_ongoing_content = ""

        self.life_point = 100
        self.energy_point = 100
        self.move_point = 100
        self.exp_point = 0
        self.iq_point = 60
        self.money = 1000
        self.credit = 100
        self.level = 1

        self.talk_type = ""
        self.route_total_distance = 0
        self.route_move_distance = 0
        self.route_target_place = ""
        self.route_target_position = None
        self.map_task_status = ""
        self.current_trade_price = -1
        self.wait_for_send_good = False

    async def async_init(self):
        """
        异步初始化 - 必须在创建实例后调用
        执行数据库查询等异步操作
        """
        try:
            # 异步查询数据库
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            self.config = result.scalar_one_or_none()

            # Initialize ai_chat_cfg
            self.ai_chat_cfg = self.config

            # 初始化 AiChatCfgManager
            self.aichatcfg_record = AiChatCfgManager()
            self.aichatcfg_record.connect(self.handle_aichatcfg_property_updated)

            # 异步加载用户数据
            await self.load_all_user_data()

            logger.info("AISocialEngine async_init completed")
        except Exception as e:
            logger.error(f"Error in async_init: {e}", exc_info=True)
            raise
```

#### 3.3 修改 HTTP 请求方法

```python
async def http_request(self, url, params=None, method="GET", data=None):
    """
    异步 HTTP 请求

    Args:
        url: 请求的 URL
        params: GET 请求参数
        method: HTTP 方法（GET, POST, PUT, DELETE, PATCH）
        data: POST/PUT 请求体

    Returns:
        JSON 响应数据
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, params=params)
            elif method == "POST":
                response = await client.post(url, data=data)
            elif method == "PUT":
                response = await client.put(url, data=data)
            elif method == "DELETE":
                response = await client.delete(url, params=params)
            elif method == "PATCH":
                response = await client.patch(url, data=data)
            else:
                raise ValueError(f"不支持的请求方法: {method}")

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as http_err:
        logger.error(f"HTTP错误发生: {http_err}")
    except httpx.RequestError as req_err:
        logger.error(f"请求错误发生: {req_err}")
    except ValueError as json_err:
        logger.error(f"JSON解析错误: {json_err}")

    return None
```

#### 3.4 修改 `call_service` 方法

```python
async def call_service(self, url, method, **params):
    """异步调用服务"""
    try:
        response_data = await self.http_request(url, method, **params)
        if response_data:
            self.handle_service_called_result(response_data)
            return response_data
    except Exception as e:
        logger.error(f"Error calling service: {e}")
        return None
```

#### 3.5 修改 API 获取方法

```python
async def get_service_list(self):
    """异步获取服务列表"""
    url = "http://www.ai-sns.org/api/get_service_list/"
    pos = self.aichatcfg_record.current_position
    params = {
        "lng": pos[0],
        "lat": pos[1]
    }
    service_list = await self.http_request(url, params)
    return service_list

async def get_skill_list(self):
    """异步获取技能列表"""
    # 当前返回空列表，但如果是数据库查询，需要改为异步
    return []

async def get_plugin_tool_list(self):
    """异步获取插件工具列表"""
    # 注意：query_tool_list() 需要改为异步版本
    from db.DBFactory import query_tool_list_async  # 需要创建异步版本
    records = await query_tool_list_async()

    default_values = {
        "place": "Any Place",
        "lng": 0,
        "lat": 0,
        "type": "plugin_tool",
        "address": "Not needed",
        "method": "python call"
    }

    formatted_records = [
        {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            **default_values
        }
        for record in records
    ]

    return formatted_records

async def get_tool_list(self):
    """异步获取工具列表"""
    service_list = await self.get_service_list()
    skill_list = await self.get_skill_list()
    plugin_tool_list = await self.get_plugin_tool_list()
    tool_list = service_list + skill_list + plugin_tool_list
    return tool_list

async def get_tool_list_for_trade(self):
    """异步获取交易工具列表"""
    service_list = await self.get_service_list()
    skill_list = await self.get_skill_list()
    tool_list = service_list + skill_list
    return tool_list

async def get_mcp_list_for_trade(self):
    """异步获取MCP交易列表"""
    service_list = await self.get_service_list()
    skill_list = await self.get_skill_list()
    tool_list = service_list + skill_list
    return tool_list

async def get_place_list(self):
    """异步获取地点列表"""
    url = "http://www.ai-sns.org/api/get_place_list/"
    params = {
        "lng": self.aichatcfg_record.current_position[0],
        "lat": self.aichatcfg_record.current_position[1]
    }
    place_list = await self.http_request(url, params)
    return place_list

async def get_people_list(self):
    """异步获取人员列表"""
    url = "http://www.ai-sns.org/api/get_people_list/"
    params = {
        "lng": self.aichatcfg_record.current_position[0],
        "lat": self.aichatcfg_record.current_position[1]
    }
    data = await self.http_request(url, params)

    remove_id = self.user_map_setting.get("nationid", "")
    people_list = [item for item in data if item["nation_id"] != remove_id]

    return people_list
```

#### 3.6 修改数据库加载方法

```python
async def load_all_user_data(self):
    """异步加载用户数据"""
    from db.DBFactory import (
        query_AiChatCfg_map_async,  # 需要创建异步版本
        query_AiChatCfg_map_setting_async
    )

    record = await query_AiChatCfg_map_async()
    self.current_place = record.current_place

    # 处理 current_position
    self.aichatcfg_record.current_position = self._parse_position_data(record.current_position)
    self.last_position = self._parse_position_data(record.last_position)

    self.life_point = record.life_point
    self.energy_point = record.energy_point
    self.move_point = record.move_point
    self.exp_point = record.exp_point
    self.iq_point = record.iq_point
    self.money = record.money
    self.credit = record.credit
    self.level = record.level

    if record.route_status == "playing":
        self.move_by_route_flag = True
    else:
        self.move_by_route_flag = False

    user_map_setting = await query_AiChatCfg_map_setting_async()
    self.user_map_setting = user_map_setting

    logger.debug(f"Loaded user data - Position: {self.aichatcfg_record.current_position}")
```

#### 3.7 修改数据库保存方法

```python
async def save_all_user_data(self):
    """异步保存用户数据"""
    from db.DBFactory import update_AiChatCfg_map_async  # 需要创建异步版本

    data = {
        "current_place": self.current_place,
        "current_position": json.dumps(self.aichatcfg_record.current_position, ensure_ascii=False),
        "last_position": json.dumps(self.aichatcfg_record.last_position, ensure_ascii=False),
        "life_point": self.life_point,
        "energy_point": self.energy_point,
        "move_point": self.move_point,
        "exp_point": self.exp_point,
        "iq_point": self.iq_point,
        "money": self.money,
        "credit": self.credit,
        "level": self.level,
    }
    await update_AiChatCfg_map_async(**data)
```

#### 3.8 修改异步函数调用方法

```python
async def think(self, **kwargs):
    """异步思考方法"""
    event = kwargs.get("event", "")
    current_chat_summary = kwargs.get("current_chat_summary", "")

    # 使用 await 而不是 create_task
    await self.ask_agent_to_update_task()

    if event == "after_conversation":
        self.taskmng.js_task_manager.show_information(
            lt("I'm thinking after conversation.", "正在思考对话内容。")
        )
        self.taskmng.set_command_status("ask_agent_to_think_after_conversation")
        self.ask_agent_to_think_after_conversation(current_chat_summary)
    else:
        pass

async def ask_agent_to_bargain_for_buyer(self, tool_list):
    """异步要求代理为买家议价"""
    messages_history = json.dumps(self.current_talk_history, ensure_ascii=False)
    conversation_target = self.taskmng.current_objective
    role_prompt = get_prompt_by_title("__buyer_bargain_content__")
    role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
    role_prompt = role_prompt.replace("__messages_history__", messages_history)
    role_prompt = role_prompt.replace("__tool_list__", tool_list)
    question = "请严格遵照要求评估，并严格按照格式输出。"
    await self.ask_agent_and_get_instruction(question, role_prompt)

async def ask_agent_to_bargain_for_seller(self, tool_list):
    """异步要求代理为卖家议价"""
    messages_history = json.dumps(self.current_talk_history, ensure_ascii=False)
    conversation_target = self.taskmng.current_objective
    role_prompt = get_prompt_by_title("__seller_bargain_content__")
    role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
    role_prompt = role_prompt.replace("__messages_history__", messages_history)
    role_prompt = role_prompt.replace("__tool_list__", tool_list)
    question = "请严格遵照要求评估，并严格按照格式输出。"
    await self.ask_agent_and_get_instruction(question, role_prompt)

async def ask_agent_to_use_service(self, question, service_list, objective_to_achieve):
    """异步要求代理使用服务"""
    role_prompt = get_prompt_by_title("__ask_agent_use_service__")
    role_prompt = role_prompt.replace("__service_list__", service_list)
    role_prompt = role_prompt.replace("__objective_to_achieve__", objective_to_achieve)

    question = question + "\n请根据相关的任务要求，准确选择服务，如果没有合适的服务请返回空列表。"

    self.command_status = "ask_agent_to_use_service"
    await self.ask_agent_and_get_instruction(question, role_prompt)

async def ask_agent_to_use_skill(self, question, function_name, function_description):
    """异步要求代理使用技能"""
    role_prompt = get_prompt_by_title("__ask_agent_use_skill__")
    role_prompt = role_prompt.replace("XXXXXXXX", function_name)
    role_prompt = role_prompt + "\n" + function_description

    question = "\n" + question + "这是我建议使用的函数：" + function_name + "，请根据相关的任务要求，把相关的任务完成掉。"
    question = question + "\n请输出完整的可独立运行的代码。"
    self.command_status = "ask_agent_to_use_skill"
    await self.ask_agent_and_get_instruction(question, role_prompt)
```

#### 3.9 修改 `compose_full_ask_content` 方法

```python
async def compose_full_ask_content(self, task_description, ability_list, question_to_llm):
    """异步构建完整的请求内容"""
    if self.temp_index > 7:
        self.decline_life()

    if self.temp_index_2 > 3:
        self.decline_energy()

    current_status = f"""
* 资金值: {self.money:.2f}元
* 生命值: {self.life_point}%
* 体力值: {self.energy_point}%
* 行动力: {self.move_point}%
    """
    question_to_llm = question_to_llm.replace("下一行动", "执行行动")
    question_to_llm = question_to_llm.replace("### 游戏攻略", "### 相关思考")
    question_to_llm = question_to_llm.replace("### 当前状况回顾", "### 行动前状况")

    prompt = get_prompt_by_title("__current_execute_status__")
    prompt = prompt.replace(f"__task_description__", task_description)
    prompt = prompt.replace(f"__last_instruction__", question_to_llm)
    prompt = prompt.replace(f"__action_result__", self.action_result)
    prompt = prompt.replace(f"__current_status__", current_status)

    # 异步获取列表
    tool_list = await self.get_tool_list()
    people_list = await self.get_people_list()
    place_list = await self.get_place_list()

    prompt = prompt.replace(f"__tool_list__", json.dumps(tool_list, indent=4, ensure_ascii=False))
    prompt = prompt.replace(f"__people_list__", json.dumps(people_list, indent=4, ensure_ascii=False))
    prompt = prompt.replace(f"__place_list__", json.dumps(place_list, indent=4, ensure_ascii=False))
    prompt = prompt.replace(f"__question_to_llm__", question_to_llm)
    return prompt.strip()
```

#### 3.10 修改 `handle_ask_agent_instruction_to_process_activity` 方法

```python
async def handle_ask_agent_instruction_to_process_activity(self, ask_content):
    """异步处理代理指令"""
    self.show_status_on_map("thinking")
    if not self.started_flag:
        return

    role_prompt = get_prompt_by_title("__main_control__")
    process_info_list_str = "\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.taskmng.process_info_list))
    ability_list = self.get_ability_list()

    # 异步调用 compose_full_ask_content
    full_ask_content = await self.compose_full_ask_content(
        process_info_list_str, ability_list, ask_content
    )
    await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)
```

---

### 第四步：创建异步数据库函数

**文件：`db/DBFactory_async.py`（新文件）**

```python
"""
异步数据库操作函数
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.database import AsyncSessionLocal, AiChatCfg
import logging

logger = logging.getLogger(__name__)


async def query_AiChatCfg_map():
    """异步查询 AiChatCfg 记录"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AiChatCfg))
        record = result.scalar_one_or_none()
        return record


async def query_AiChatCfg_map_setting(**kwargs):
    """异步查询 AiChatCfg 地图设置"""
    async with AsyncSessionLocal() as session:
        query = select(AiChatCfg)
        if kwargs:
            query = query.filter_by(**kwargs)
        result = await session.execute(query)
        record = result.scalar_one_or_none()

        if record:
            fields = {
                "nick_name": record.nickname,
                "account": record.account,
                "profile": record.sign,
                "profession": record.profession,
                "nationid": record.nationid,
                "nationpassword": record.nationpassword,
                "sns_url": record.sns_url,
                "status": record.status,
                "avatar": record.avatar,
                "avatar3d": record.avatar3d,
                "house3d": record.house3d,
                "map_type": record.map_type,
                "map_api_key": record.map_api_key,
                "map_id": record.map_id,
                "current_position": record.current_position,
                "home_position": record.home_position,
                "positionx": record.positionx,
                "positiony": record.positiony,
                "positionz": record.positionz,
                "route_start": record.route_start,
                "route_end": record.route_end,
                "route_status": record.route_status,
                "route_current_position": record.route_current_position,
                "route": record.route
            }
            return fields
        return None


async def update_AiChatCfg_map(**kwargs):
    """异步更新 AiChatCfg 记录"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AiChatCfg))
        record = result.scalar_one_or_none()

        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            await session.commit()

        return record


async def query_tool_list():
    """异步查询工具列表"""
    from db.database import Tool
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tool))
        records = result.scalars().all()
        return records
```

---

### 第五步：修改 `service.py`

**文件：`backend/modules/sns/service.py`**

```python
"""SNS Module - Business Logic Service - 异步版本"""
import logging
import os
import uuid
import base64
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession  # 替换 Session
from sqlalchemy import select  # 用于异步查询
from typing import List
from fastapi import HTTPException
from backend.database.models.chat import AIFriend, AIChatMessages, AiChatCfg
from backend.database.models.system import Prompt
from backend.modules.sns.xmpp_client import XMPPClientManager

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/sns_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AVATAR_DIR = Path("uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

_social_engine_instance = None
_social_engine_running = False


class SNSService:
    """SNS service for handling social network operations - 异步版本"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_stats(self) -> dict:
        """异步获取用户统计"""
        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if not config:
                return {
                    "level": 3,
                    "credit": 100,
                    "money": 10996.61,
                    "life": 125,
                    "iq": 70,
                    "energy": 150,
                    "move": 187.5,
                    "exp": 30
                }

            return {
                "level": config.level or 3,
                "credit": config.credit or 100,
                "money": config.money or 10996.61,
                "life": config.life_point or 125,
                "iq": config.iq_point or 70,
                "energy": config.energy_point or 150,
                "move": config.move_point or 187.5,
                "exp": config.exp_point or 30
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                "level": 3,
                "credit": 100,
                "money": 10996.61,
                "life": 125,
                "iq": 70,
                "energy": 150,
                "move": 187.5,
                "exp": 30
            }

    async def get_contacts(self) -> List[AIFriend]:
        """异步获取联系人列表"""
        try:
            stmt_config = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result_config = await self.db.execute(stmt_config)
            config = result_config.scalar_one_or_none()

            if not config:
                return []

            owner_account = config.account

            stmt_contacts = select(AIFriend).where(
                AIFriend.is_delete == False,
                AIFriend.owner_sns_account == owner_account
            ).order_by(AIFriend.nick_name)
            result_contacts = await self.db.execute(stmt_contacts)
            contacts = result_contacts.scalars().all()

            return contacts
        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return []

    async def get_chat_history(self, friend_account: str, limit: int = 50) -> List[AIChatMessages]:
        """异步获取聊天历史"""
        try:
            stmt_config = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result_config = await self.db.execute(stmt_config)
            config = result_config.scalar_one_or_none()

            if not config:
                return []

            owner_account = config.account

            from sqlalchemy import or_
            stmt_messages = select(AIChatMessages).where(
                AIChatMessages.is_delete == False,
                or_(
                    (AIChatMessages.owner_account == owner_account) &
                    (AIChatMessages.friend_account == friend_account),
                    (AIChatMessages.owner_account == friend_account) &
                    (AIChatMessages.friend_account == owner_account)
                )
            ).order_by(AIChatMessages.create_time.desc()).limit(limit)

            result_messages = await self.db.execute(stmt_messages)
            messages = result_messages.scalars().all()
            messages.reverse()

            return messages
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []

    # ... 其他方法类似地改为异步 ...
```

---

### 第六步：修改 `router.py` 中的调用

**文件：`backend/modules/sns/router.py`**

```python
@router.get("/user-stats", response_model=UserStatsResponse)
async def get_user_stats(db: AsyncSession = Depends(get_db)):
    """获取用户统计"""
    service = SNSService(db)
    return await service.get_user_stats()


@router.get("/contacts", response_model=List[ContactResponse])
async def get_contacts(db: AsyncSession = Depends(get_db)):
    """获取联系人列表"""
    service = SNSService(db)
    return await service.get_contacts()


@router.get("/chat-history/{account}", response_model=List[ChatMessageResponse])
async def get_chat_history(account: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取聊天历史"""
    service = SNSService(db)
    return await service.get_chat_history(account, limit)
```

---

### 第七步：更新 `service.py` 中的 `start_social_engine`

```python
async def start_social_engine(self) -> dict:
    """启动 AI 社交引擎"""
    global _social_engine_instance, _social_engine_running

    try:
        if _social_engine_running:
            return {
                "success": True,
                "message": "AI Social Engine is already running",
                "running": True
            }

        from backend.modules.sns.ai_social_engine_adapter import AISocialEngine

        if _social_engine_instance is None:
            _social_engine_instance = AISocialEngine(self.db)
            await _social_engine_instance.async_init()  # 异步初始化

        await _social_engine_instance.start()
        _social_engine_running = True

        logger.info("AI Social Engine started successfully")
        return {
            "success": True,
            "message": "AI Social Engine started successfully",
            "running": True
        }
    except Exception as e:
        logger.error(f"Error starting AI social engine: {e}")
        _social_engine_running = False
        return {
            "success": False,
            "message": f"Failed to start AI Social Engine: {str(e)}",
            "running": False
        }
```

---

## 测试清单

### 1. 单元测试
- [ ] 测试异步数据库查询
- [ ] 测试异步 HTTP 请求
- [ ] 测试异步函数调用链

### 2. 集成测试
- [ ] 测试启动 AI 社交引擎
- [ ] 测试获取用户统计
- [ ] 测试获取联系人列表
- [ ] 测试发送消息
- [ ] 测试获取聊天历史

### 3. 性能测试
- [ ] 对比异步/同步版本的响应时间
- [ ] 测试并发请求性能
- [ ] 监控内存和CPU使用情况

---

## 注意事项

1. **数据库连接池**: 确保 AsyncSessionLocal 配置了合适的连接池大小
2. **超时设置**: 所有 HTTP 请求都应设置合理的超时时间
3. **错误处理**: 异步操作需要适当的错误处理和日志记录
4. **资源清理**: 使用 `async with` 确保 HTTP 客户端和数据库会话正确关闭
5. **并发控制**: 对于批量操作，使用 `asyncio.gather()` 提高性能
6. **向后兼容**: 保留同步版本作为后备，直到完全迁移完成
