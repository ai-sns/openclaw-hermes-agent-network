"""
AI Social Engine Adapter - 异步优化补丁

这个文件包含了 ai_social_engine_adapter.py 需要进行的所有异步化修改
请按照以下步骤应用这些修改
"""

# ========================================
# 1. 导入部分修改（文件开头）
# ========================================

"""
将第5-40行的导入修改为：

# 原始导入：
from sqlalchemy.orm import Session
import requests

# 修改为：
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
"""

# ========================================
# 2. __init__ 方法修改
# ========================================

"""
将第60-83行的 __init__ 方法修改为：

class AISocialEngine:
    \"\"\"
    Backend adapter for AI Social Engine - 异步版本
    Wraps the Qt-based ai_social_engine functionality for API use
    \"\"\"

    def __init__(self, db: AsyncSession):
        \"\"\"初始化（不包含数据库操作）\"\"\"
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

        # ... 保持原有的所有属性初始化 ...


"""

"""
在 AISocialEngine 类中添加异步初始化方法（在 __init__ 之后）：

    async def async_init(self):
        \"\"\"
        异步初始化 - 必须在创建实例后调用
        执行数据库查询等异步操作
        \"\"\"
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
"""

# ========================================
# 3. HTTP 请求方法修改
# ========================================

"""
将 http_request 方法（约在第3495-3516行）修改为：

async def http_request(self, url, params=None, method="GET", data=None):
    \"\"\"
    异步 HTTP 请求

    Args:
        url: 请求的 URL
        params: GET 请求参数
        method: HTTP 方法（GET, POST, PUT, DELETE, PATCH）
        data: POST/PUT 请求体

    Returns:
        JSON 响应数据
    \"\"\"
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
"""

"""
将 call_service 方法（约在第2274-2291行）修改为：

async def call_service(self, url, method, **params):
    \"\"\"异步调用服务\"\"\"
    try:
        response_data = await self.http_request(url, method, **params)
        if response_data:
            self.handle_service_called_result(response_data)
            return response_data
    except Exception as e:
        logger.error(f"Error calling service: {e}")
        return None
"""

# ========================================
# 4. API 获取方法修改
# ========================================

"""
将以下方法改为异步（约在第1486-1552行）：

async def get_service_list(self):
    \"\"\"异步获取服务列表\"\"\"
    url = "http://www.ai-sns.org/api/get_service_list/"
    pos = self.aichatcfg_record.current_position
    params = {
        "lng": pos[0],
        "lat": pos[1]
    }
    service_list = await self.http_request(url, params)
    return service_list

async def get_skill_list(self):
    \"\"\"异步获取技能列表\"\"\"
    # 当前返回空列表，但如果是数据库查询，需要改为异步
    return []

async def get_plugin_tool_list(self):
    \"\"\"异步获取插件工具列表\"\"\"
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
    \"\"\"异步获取工具列表\"\"\"
    service_list = await self.get_service_list()
    skill_list = await self.get_skill_list()
    plugin_tool_list = await self.get_plugin_tool_list()
    tool_list = service_list + skill_list + plugin_tool_list
    return tool_list

async def get_tool_list_for_trade(self):
    \"\"\"异步获取交易工具列表\"\"\"
    service_list = await self.get_service_list()
    skill_list = await self.get_skill_list()
    tool_list = service_list + skill_list
    return tool_list

async def get_mcp_list_for_trade(self):
    \"\"\"异步获取MCP交易列表\"\"\"
    service_list = await self.get_service_list()
    skill_list = await self.get_skill_list()
    tool_list = service_list + skill_list
    return tool_list

async def get_place_list(self):
    \"\"\"异步获取地点列表\"\"\"
    url = "http://www.ai-sns.org/api/get_place_list/"
    params = {
        "lng": self.aichatcfg_record.current_position[0],
        "lat": self.aichatcfg_record.current_position[1]
    }
    place_list = await self.http_request(url, params)
    return place_list

async def get_people_list(self):
    \"\"\"异步获取人员列表\"\"\"
    url = "http://www.ai-sns.org/api/get_people_list/"
    params = {
        "lng": self.aichatcfg_record.current_position[0],
        "lat": self.aichatcfg_record.current_position[1]
    }
    data = await self.http_request(url, params)

    remove_id = self.user_map_setting.get("nationid", "")
    people_list = [item for item in data if item["nation_id"] != remove_id]

    return people_list
"""

# ========================================
# 5. 数据库加载/保存方法修改
# ========================================

"""
将 load_all_user_data 方法（约在第3534-3559行）修改为：

async def load_all_user_data(self):
    \"\"\"异步加载用户数据\"\"\"
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
"""

"""
将 save_all_user_data 方法（约在第3518-3532行）修改为：

async def save_all_user_data(self):
    \"\"\"异步保存用户数据\"\"\"
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
"""

# ========================================
# 6. 异步函数调用方法修改
# ========================================

"""
将 think 方法（约在第681-692行）修改为：

async def think(self, **kwargs):
    \"\"\"异步思考方法\"\"\"
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
"""

"""
将 ask_agent_to_bargain_for_buyer 方法（约在第2202-2210行）修改为：

async def ask_agent_to_bargain_for_buyer(self, tool_list):
    \"\"\"异步要求代理为买家议价\"\"\"
    messages_history = json.dumps(self.current_talk_history, ensure_ascii=False)
    conversation_target = self.taskmng.current_objective
    role_prompt = get_prompt_by_title("__buyer_bargain_content__")
    role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
    role_prompt = role_prompt.replace("__messages_history__", messages_history)
    role_prompt = role_prompt.replace("__tool_list__", tool_list)
    question = "请严格遵照要求评估，并严格按照格式输出。"
    await self.ask_agent_and_get_instruction(question, role_prompt)
"""

"""
将 ask_agent_to_bargain_for_seller 方法（约在第2220-2228行）修改为：

async def ask_agent_to_bargain_for_seller(self, tool_list):
    \"\"\"异步要求代理为卖家议价\"\"\"
    messages_history = json.dumps(self.current_talk_history, ensure_ascii=False)
    conversation_target = self.taskmng.current_objective
    role_prompt = get_prompt_by_title("__seller_bargain_content__")
    role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
    role_prompt = role_prompt.replace("__messages_history__", messages_history)
    role_prompt = role_prompt.replace("__tool_list__", tool_list)
    question = "请严格遵照要求评估，并严格按照格式输出。"
    await self.ask_agent_and_get_instruction(question, role_prompt)
"""

"""
将 ask_agent_to_use_service 方法（约在第2239-2247行）修改为：

async def ask_agent_to_use_service(self, question, service_list, objective_to_achieve):
    \"\"\"异步要求代理使用服务\"\"\"
    role_prompt = get_prompt_by_title("__ask_agent_use_service__")
    role_prompt = role_prompt.replace("__service_list__", service_list)
    role_prompt = role_prompt.replace("__objective_to_achieve__", objective_to_achieve)

    question = question + "\\n请根据相关的任务要求，准确选择服务，如果没有合适的服务请返回空列表。"

    self.command_status = "ask_agent_to_use_service"
    await self.ask_agent_and_get_instruction(question, role_prompt)
"""

"""
将 ask_agent_to_use_skill 方法（约在第2302-2310行）修改为：

async def ask_agent_to_use_skill(self, question, function_name, function_description):
    \"\"\"异步要求代理使用技能\"\"\"
    role_prompt = get_prompt_by_title("__ask_agent_use_skill__")
    role_prompt = role_prompt.replace("XXXXXXXX", function_name)
    role_prompt = role_prompt + "\\n" + function_description

    question = "\\n" + question + "这是我建议使用的函数：" + function_name + "，请根据相关的任务要求，把相关的任务完成掉。"
    question = question + "\\n请输出完整的可独立运行的代码。"
    self.command_status = "ask_agent_to_use_skill"
    await self.ask_agent_and_get_instruction(question, role_prompt)
"""

# ========================================
# 7. 组合调用方法修改
# ========================================

"""
将 compose_full_ask_content 方法（约在第862-891行）修改为：

async def compose_full_ask_content(self, task_description, ability_list, question_to_llm):
    \"\"\"异步构建完整的请求内容\"\"\"
    if self.temp_index > 7:
        self.decline_life()

    if self.temp_index_2 > 3:
        self.decline_energy()

    current_status = f\"\"\"
* 资金值: {self.money:.2f}元
* 生命值: {self.life_point}%
* 体力值: {self.energy_point}%
* 行动力: {self.move_point}%
    \"\"\"
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
"""

"""
将 handle_ask_agent_instruction_to_process_activity 方法（约在第848-859行）修改为：

async def handle_ask_agent_instruction_to_process_activity(self, ask_content):
    \"\"\"异步处理代理指令\"\"\"
    self.show_status_on_map("thinking")
    if not self.started_flag:
        return

    role_prompt = get_prompt_by_title("__main_control__")
    process_info_list_str = "\\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.taskmng.process_info_list))
    ability_list = self.get_ability_list()

    # 异步调用 compose_full_ask_content
    full_ask_content = await self.compose_full_ask_content(
        process_info_list_str, ability_list, ask_content
    )
    await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)
"""

# ========================================
# 8. 更新 service.py 中的 start_social_engine
# ========================================

"""
在 service_async.py 的 start_social_engine 方法中已经包含了异步初始化调用：

if _social_engine_instance is None:
    _social_engine_instance = AISocialEngine(self.db)
    await _social_engine_instance.async_init()  # 关键：异步初始化

await _social_engine_instance.start()
"""

# ========================================
# 9. 创建异步数据库函数文件
# ========================================

"""
创建文件：db/DBFactory_async.py

内容见下一个文件
"""

print("=" * 60)
print("异步优化补丁说明")
print("=" * 60)
print("\n请按照以下步骤应用这些修改：\n")
print("1. 修改 ai_social_engine_adapter.py 的导入")
print("2. 在 AISocialEngine 类中添加 async_init 方法")
print("3. 修改所有 HTTP 请求方法为异步")
print("4. 修改所有 API 获取方法为异步")
print("5. 修改数据库加载/保存方法为异步")
print("6. 修改所有异步函数调用方法")
print("7. 修改组合调用方法")
print("8. 确保 service_async.py 已创建并使用")
print("9. 创建 DBFactory_async.py 异步数据库函数")
print("10. 在 router.py 中添加 await 调用")
print("\n" + "=" * 60)
