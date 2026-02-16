from sqlalchemy.orm import Session
from backend.database.models.chat import AiChatCfg
from backend.apps.sns.map_task_manager import MapTaskManager
from backend.apps.sns.js_task_manager import JsTaskManager
from backend.apps.sns.xmpp_client import XMPPClientManager
from backend.modules.agent.agent_manager import agent_manager
from backend.shared.websocket_manager import manager as websocket_manager

# *********
import os
import math
# 主要用于发送附件
import asyncio
import zipfile
import shutil
import time

import logging

import re

log = logging.getLogger(__name__)
from db.DBFactory import (query_AgentCfg, add_AIChatMessages, get_prompt_by_title, query_function_mng,
                          add_function_mng, update_map_task, add_map_visit, get_key_value,
                          update_map_trade, add_map_trade, add_map_tool, query_single_map_trade, update_AiChatCfg_by_user_id, update_AiChatCfg_map, query_AiChatCfg_map, add_mcp_mng, query_mcp_mng,
                          delete_map_preset_msg, query_map_preset_msg_all, add_map_preset_msg, query_tool_list, query_single_tool, query_AiChatCfg_map_setting)
from util import (generate_random_id, add_memory_list)
from i18n import lt
from enum import Enum
from typing import List, Dict, Optional
import json
import logging
import requests
import geopy.distance
from geopy.distance import distance
from geopy.point import Point
from geographiclib.geodesic import Geodesic
import random

from .mixin.xmpp_mixin import XmppMixin
from .mixin.tools_mixin import ToolsMixin
from .mixin.map_movement_mixin import MapMovementMixin
from .mixin.communication_mixin import CommunicationMixin
from .mixin.agent_interaction_mixin import AgentInteractionMixin
from .mixin.trade_mixin import TradeMixin
from .mixin.ui_display_mixin import UIDisplayMixin
from .mixin.data_query_mixin import DataQueryMixin

logger = logging.getLogger(__name__)


class AISocialEngine(
    XmppMixin,
    ToolsMixin,
    MapMovementMixin,
    CommunicationMixin,
    AgentInteractionMixin,
    TradeMixin,
    DataQueryMixin,
    UIDisplayMixin
):
    """
    Backend adapter for AI Social Engine
    Wraps the Qt-based ai_social_engine functionality for API use
    """

    def __init__(self, db: Session):
        self.db = db
        self.started_flag = False
        self.map_task_status = ""
        self.current_place = None
        self.process_list = []
        self.ability_list = []
        self.task_runner = None
        self.taskmng_js = JsTaskManager(self)
        self.taskmng = MapTaskManager(self)

        # Initialize XMPP client manager
        self.xmpp_manager = XMPPClientManager.get_instance()

        # Load configuration from database
        self.config = self.db.query(AiChatCfg).filter(
            AiChatCfg.is_delete == False
        ).first()

        # Initialize ai_chat_cfg from database - get first record from aichat_cfg table
        self.ai_chat_cfg = self.config

        self.aichatcfg_record = AiChatCfgManager()
        self.aichatcfg_record.connect(self.handle_aichatcfg_property_updated)
        # self.update_resource_display()  # 移到 load_all_user_data() 之后调用

        # *******************************************
        self.human_take_over = False
        self.human_instruction = ""
        self.stopping_ai_process_flag = False
        self.pause_flag = False
        self.agent_replying_flag = False
        self.human_talk_type = 0  # 0 talk to your ai，1 talk to friend
        self.conversation_id = ""
        self.messages = []
        self.messages_command = []
        self.page_index = 0
        self.map_mode = 'org'  # self.map_mode有两种模式，一种是发送给进入服务场景的比如3d的aigccenter 这种是map_application模式，一种是发送到地图的org
        # Qt GUI setup - disabled for backend use
        # self.setupUi(self)

        # self.messageEdit.setFocus()
        # self.messageEdit.installEventFilter(self)

        self.personList = ["My_Agent", "wangwang"]

        self.agent = None
        self.kmselectedList = []
        self.pluginselectedList = []
        self.current_received_msg = ""

        self.messages = []

        self.is_browser_page_loaded = False
        self.first_event = None
        self.first_reply = ""

        # plugin相关
        self.chess_role = None
        self.chinese_chess_role = None
        self.system_role_prompt = "You are a helpful assistant who provides concise and accurate information."

        # 初始化全局变量
        self.user_map_setting = None
        self.current_place = ""  # db
        self.current_position = []  # db
        self.last_position = []  # db

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

    async def async_init(self):
        """
        异步初始化方法
        用于在创建实例后进行额外的异步初始化
        """
        logger.info("[Step-01],Init AISocialEngine...")
        logger.info("Async initializing AISocialEngine...")
        # 这里可以添加需要在 async 上下文中执行的初始化代码
        # 目前大部分初始化已经在 __init__ 中完成
        logger.info("AISocialEngine async initialization complete")
        self.command_status = ""
        # 初始化当前任务所需技能集合（示例）
        self.required_skills = []
        # 初始化自身可交换技能集合
        self.available_skills = []
        self.route_flag = False
        # 初始化拥有的Token数量
        self.token_balance = 0  # todo remove？

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
        self.max_people_comm = 4  # 最大可沟通人数
        self.max_rounds_per_person = 6  # 单个人员最大沟通轮数 3
        self.max_place_arrived = 3  # 单个人员最大沟通轮数
        self.min_place_move_score = 80  # 单个人员最大沟通轮数
        self.search_radius = 10000  # cloud
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

        self.talk_type = ""  # communication,sell
        self.route_total_distance = 0
        self.route_move_distance = 0
        self.route_target_place = ""
        self.route_target_position = None
        self.map_task_status = ""
        self.current_trade_price = -1
        self.wait_for_send_good = False
        self.load_all_user_data()
        # self.update_map_charts()
        # self.update_resource_display()

    async def start_engine(self):
        """
        Start the AI social engine
        This is the backend-compatible version of the start() method
        """
        try:
            logger.info("[Step-02],Start AISocialEngine...")
            logger.info("Starting AI Social Engine...")

            self.started_flag = True

            if self.map_task_status not in ("", "started", "paused"):
                self.map_task_status = ""

            if self.map_task_status == "":
                print("[Info]:", "map_task_status is blank")
                self.map_task_status = "started"

                self.taskmng.reviewing_task = True
                self.process_list = []
                self.taskmng.current_process = None
                self.taskmng.add_process(current_place=self.current_place, current_position=self.aichatcfg_record.current_position)

                self.taskmng.current_situation = f"准备开始执行任务"
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
                asyncio.create_task(self.taskmng.process_task(action="process_activity"))
            elif self.map_task_status == "started":
                print("[Info]:", "map_task_status is started, continuing task processing")
            elif self.map_task_status == "paused":
                print("[Info]:", "map_task_status is paused, waiting for resume")

            # Get current position from config
            if self.config:
                current_position = self.config.current_position
                logger.info(f"Current position: {current_position}")

            logger.info("AI Social Engine started successfully")
            logger.info(f"Map task status: {self.map_task_status}")
            logger.info(f"Abilities enabled: {len(self.ability_list)}")

        except Exception as e:
            logger.error(f"Error in start(): {e}", exc_info=True)
            self.started_flag = False
            self.map_task_status = "error"
            raise

    async def pause_engine(self):
        """
        Pause the AI social engine
        """
        try:
            logger.info("Pausing AI Social Engine...")

            # 设置暂停状态
            self.map_task_status = "paused"

            logger.info("AI Social Engine paused successfully")
            return {
                "success": True,
                "message": "AI Social Engine paused successfully",
                "status": "paused"
            }

        except Exception as e:
            logger.error(f"Error in pause_engine(): {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to pause AI Social Engine: {str(e)}",
                "status": "error"
            }

    async def resume_engine(self):
        """
        Resume the AI social engine
        """
        try:
            logger.info("Resuming AI Social Engine...")

            # 设置运行状态
            self.map_task_status = "started"

            logger.info("AI Social Engine resumed successfully")
            return {
                "success": True,
                "message": "AI Social Engine resumed successfully",
                "status": "started"
            }

        except Exception as e:
            logger.error(f"Error in resume_engine(): {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to resume AI Social Engine: {str(e)}",
                "status": "error"
            }

    def get_status(self) -> dict:
        """
        Get the current status of the engine
        """
        return {
            "started": self.started_flag,
            "task_status": self.map_task_status,
            "abilities_count": len(self.ability_list),
            "current_place": self.current_place
        }

    def get_task_process_history(self):
        """
        获取任务处理历史记录，按照指定格式返回字符串
        """
        result = "📜 Process history\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        if not self.taskmng.process_info_list:
            result += "N/A\n"
        else:
            for index, process_content in enumerate(self.taskmng.process_info_list, 1):
                result += f"【{index}】{process_content}\n"
        return result

    async def ask_agent_instruction_to_process_activity(self, ask_content):
        await self.handle_ask_agent_instruction_to_process_activity(ask_content)

    async def handle_ask_agent_instruction_to_process_activity(self, ask_content):
        self.show_status_on_map("thinking")
        if not self.started_flag:
            return

        role_prompt = get_prompt_by_title("__main_control__")
        process_info_list_str = "\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.taskmng.process_info_list))
        # question_to_llm = ask_content + "请告诉我，我接着应该干什么，具体请从功能列表中挑选。"
        question_to_llm = ask_content
        full_ask_content = self.compose_full_ask_content(process_info_list_str, question_to_llm)
        await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)

    def compose_full_ask_content(self, task_description, question_to_llm):
        if self.temp_index > 7:
            self.decline_life()

        if self.temp_index_2 > 3:
            self.decline_energy()

        money = float(self.aichatcfg_record.money or 0)
        life_point = int(self.aichatcfg_record.life_point or 0)
        energy_point = int(self.aichatcfg_record.energy_point or 0)
        move_point = int(self.aichatcfg_record.move_point or 0)

        current_status = f"""
* 资金值: {money:.2f}元
* 生命值: {life_point}%
* 体力值: {energy_point}%
* 行动力: {move_point}%
                    """
        question_to_llm = question_to_llm.replace("下一行动", "执行行动")
        question_to_llm = question_to_llm.replace("### 游戏攻略", "### 相关思考")
        question_to_llm = question_to_llm.replace("### 当前状况回顾", "### 行动前状况")

        prompt = get_prompt_by_title("__current_status__")
        prompt = prompt.replace(f"__task_description__", task_description)
        prompt = prompt.replace(f"__last_instruction__", question_to_llm)
        # prompt = prompt.replace(f"__current_task_list__", self.current_task_list)
        # prompt = prompt.replace(f"__current_action__", self.current_action)
        prompt = prompt.replace(f"__action_result__", self.action_result)
        prompt = prompt.replace(f"__current_status__", current_status)
        prompt = prompt.replace(f"__tool_list__", json.dumps(self.get_service_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__people_list__", json.dumps(self.get_people_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__place_list__", json.dumps(self.get_place_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__question_to_llm__", question_to_llm)
        return prompt.strip()

    def parse_agent_instruction_for_process_activity(self, instruction):
        self.handle_parse_agent_instruction_for_process_activity(instruction)

    def handle_parse_agent_instruction_for_process_activity(self, instruction):
        print("llm return instruction:", instruction)
        instruction = instruction.strip()
        self.current_task_list = self.get_current_task_list(instruction)
        action_str = self.get_next_action(instruction)
        self.current_action = action_str

        print("current action_str:", action_str)

        if self.temp_index > 7:
            self.temp_index = 0
        else:
            self.temp_index = self.temp_index + 1

        if self.temp_index_2 > 3:
            self.temp_index_2 = 0
        else:
            self.temp_index_2 = self.temp_index_2 + 1

        self.write_on_going_process_to_pane(action_str)
        # self.loading_tab.stop_loading()

        if "附近逛逛" in action_str:
            # self.move_by_route_flag = True
            if self.target_position:
                action_result = self.move_ahead(self.aichatcfg_record.current_position, self.target_position, self.target_place)
            elif self.move_by_route_flag:
                action_result = self.move_by_route()
                return
            else:
                action_result = self.go_around()

        elif "走路前往" in action_str:
            # 使用正则表达式提取JSON部分
            json_match = re.search(r'\{.*\}', action_str)
            if not json_match:
                return None, None

            # 解析JSON
            data = json.loads(json_match.group(0))

            # 提取所需字段
            place = data.get('place')
            position = data.get('position')
            target_position = position

            self.target_position = target_position
            self.target_place = place

            action_result = self.move_ahead(self.aichatcfg_record.current_position, target_position, place)

        elif "沟通" in action_str:
            self.communicate_with_a_people(action_str, instruction)
            return

        elif "推销" in action_str:
            self.sell_to_a_people(action_str, instruction)
            return

        elif "求购" in action_str:
            self.buy_from_a_people(action_str, instruction)
            return

        elif "Web Service" in action_str:
            self.use_service(action_str, instruction)
            return

        elif "导航服务" in action_str:
            if self.move_by_route_flag:
                # 如果按路线移动则不需要导航
                action_result = self.move_by_route()
                return
            else:
                action_result = self.get_guidance()

        elif "外卖服务" in action_str:
            action_result = self.set_food_order()

        elif "叫车服务" in action_str:
            # 使用正则表达式提取JSON部分
            json_match = re.search(r'\{.*\}', action_str)
            if not json_match:
                return None, None

            # 解析JSON
            data = json.loads(json_match.group(0))

            # 提取所需字段
            place = data.get('place')
            position = data.get('position')

            target_position = position
            action_result = self.set_taxi_order(self.aichatcfg_record.current_position, target_position, place)

        elif "远程医疗" in action_str:
            action_result = self.call_a_doctor()

        else:
            action_result = f"'{action_str}'不在有效行动列表中。"

        self.action_result = action_result
        self.taskmng.add_process_info_to_list(f"system:{action_result}")
        self.write_task_process_to_pane(action_result + "\n\n")
        self.show_alert_on_map(action_result)
        ask_content = instruction
        asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=ask_content))

    def get_next_action(self, instruction):
        # 定义分隔标记
        delimiter = "下一行动"

        # 检查分隔标记是否存在
        if delimiter in instruction:
            # 分割字符串并取最后一部分（防止有多个相同标记）
            parts = instruction.split(delimiter, 1)
            return parts[1].strip() if len(parts) > 1 else ""
        delimiter = "下一步行动"
        if delimiter in instruction:
            # 分割字符串并取最后一部分（防止有多个相同标记）
            parts = instruction.split(delimiter, 1)
            return parts[1].strip() if len(parts) > 1 else ""

        return ""

    def get_current_task_list(self, text):
        start_marker = "### 当前任务清单"
        end_marker = "### 下一行动"
        try:
            # Find indices of markers (case-sensitive)
            start_idx = text.index(start_marker) + len(start_marker)
            end_idx = text.index(end_marker, start_idx)  # Search after start marker

            # Extract and strip whitespace
            return text[start_idx:end_idx].strip()
        except ValueError:
            # Handle case where markers are not found
            return ""

    def human_message_received(self, instruction):
        if self.human_take_over:
            if self.human_talk_type == 0:
                if self.agent_replying_flag:
                    # todo 请给前端发送提示："提示", "Agent正在完成上一个任务，请稍等..."
                    return
                self.taskmng_js.show_information(lt(f"Human:{instruction}", f"人类:{instruction}"))
                self.write_on_going_process_to_pane(lt("Human take control...", "人类控制中..."))
                self.handle_human_instruction(instruction)
            else:
                self.sendMessage(instruction, True)

    async def ask_agent_instruction_to_process_human_instruction(self, ask_content):
        self.show_status_on_map("thinking")
        if not self.started_flag:
            return

        role_prompt = get_prompt_by_title("__human_instruction_to_process_activity_role__")
        task_description = self.taskmng.get_task_summary()
        question_to_llm = ask_content
        full_ask_content = self.compose_full_ask_content_human(task_description,  question_to_llm)
        await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)

    def compose_full_ask_content_human(self, task_description,  question_to_llm):
        prompt = get_prompt_by_title("__human_instruction_to_process_activity_content__")
        prompt = prompt.replace(f"__human_instruction__", question_to_llm)
        prompt = prompt.replace(f"__tool_list__", json.dumps(self.get_service_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__people_list__", json.dumps(self.get_people_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__place_list__", json.dumps(self.get_place_list(), indent=4, ensure_ascii=False))

        return prompt.strip()

    def parse_agent_instruction_for_process_human_instruction(self, instruction):
        self.parse_agent_instruction_for_process_activity(instruction)
        return

    def handle_human_instruction(self, human_instruction):
        if human_instruction:
            if human_instruction.startswith("@Memory:"):
                memory_content = human_instruction.split(':', 1)[1].strip()
                messages = [
                    {"role": "user", "content": f"{memory_content}"}
                ]
                add_memory_list(messages)
                return

            # 将人类指令整合到full_ask_content中
            self.human_instruction = human_instruction
            asyncio.create_task(self.taskmng.process_task(action="process_human_instruction", ask_content=human_instruction, human_send_flag=True))

    def handle_aichatcfg_property_updated(self, property_name):
        """
        处理AiChatCfg属性更新的函数
        当特定属性发生变化时，更新相关的界面元素

        Args:
            property_name (str): 被更新的属性名称
        """
        # 定义需要更新图表的属性
        chart_related_properties = [
            'iq_point', 'energy_point', 'life_point',
            'move_point', 'exp_point', 'money',
            'credit', 'level'
        ]

        # 定义需要更新进行中进程面板的属性
        process_pane_related_properties = [
            'profession', 'current_position', 'money',
            'life_point', 'energy_point'
        ]

        # 如果属性与图表相关，则更新图表
        if property_name in chart_related_properties:
            self.update_map_charts()

        # 如果属性与进行中进程面板相关，则更新面板
        if property_name in process_pane_related_properties:
            self.write_on_going_process_to_pane(self.current_ongoing_content or "")


class AiChatCfgManager:
    """
    管理AiChatCfg数据库记录的类
    支持通过属性访问获取最新值，通过属性赋值更新数据库记录
    """

    def __init__(self, user_id=None):
        """
        初始化AiChatCfgManager

        Args:
            user_id (str, optional): 用户ID，默认为None，使用第一条记录
        """
        self._user_id = user_id
        self._record = None
        self._callbacks = []  # 存储回调函数列表
        self._load_record()

    def connect(self, callback):
        """
        连接回调函数，当属性更新时调用

        Args:
            callback: 回调函数，接收一个参数(property_name)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def disconnect(self, callback):
        """
        断开回调函数

        Args:
            callback: 要移除的回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _emit_property_updated(self, property_name):
        """
        触发属性更新回调

        Args:
            property_name: 更新的属性名
        """
        for callback in self._callbacks:
            try:
                callback(property_name)
            except Exception as e:
                logger.error(f"Error in property update callback: {e}")

    def _load_record(self):
        """加载数据库记录"""
        if self._user_id:
            self._record = query_AiChatCfg_map_setting(user_id=self._user_id)
        else:
            self._record = query_AiChatCfg_map()

    def _refresh_record(self):
        """刷新记录以获取最新数据"""
        self._load_record()

    def __getattr__(self, name):
        """
        当访问不存在的属性时调用此方法
        用于获取数据库记录中的字段值

        Args:
            name (str): 属性名

        Returns:
            字段值
        """
        # 避免在__init__过程中调用此方法
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        # 刷新记录以获取最新数据
        self._refresh_record()

        # 检查记录是否存在
        if self._record is None:
            raise AttributeError(f"No record found in database")

        # 特殊处理 current_position 属性
        if name == 'current_position':
            raw_position = getattr(self._record, name, None)
            # 创建一个临时实例来调用 _parse_position_data 方法
            temp_instance = type('Temp', (object,), {})()
            temp_instance._parse_position_data = lambda pos_data: self._parse_position_data_impl(pos_data)
            return temp_instance._parse_position_data(raw_position)

        # 特殊处理其他位置相关属性
        other_position_fields = ['last_position', 'home_position', 'route_start', 'route_end', 'route_current_position']
        if name in other_position_fields:
            import json
            raw_value = getattr(self._record, name, None)
            if raw_value:
                try:
                    return json.loads(raw_value)
                except (json.JSONDecodeError, TypeError):
                    return raw_value
            else:
                return None

        # 检查属性是否存在
        if hasattr(self._record, name):
            return getattr(self._record, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """
        当设置属性时调用此方法
        用于更新数据库记录中的字段值

        Args:
            name (str): 属性名
            value: 要设置的值
        """
        # 处理内部属性
        if name.startswith('_') or name in ['user_id']:
            super().__setattr__(name, value)
            return

        # 需要特殊处理的字段列表
        position_fields = ['current_position', 'last_position', 'home_position',
                           'route_start', 'route_end', 'route_current_position']

        # 如果是位置相关字段且值为list或dict类型，则转换为字符串
        if name in position_fields and isinstance(value, (list, dict)):
            import json
            value = json.dumps(value, ensure_ascii=False)

        # 对于其他属性，更新数据库记录
        if '_record' in self.__dict__ and self._record is not None:
            # 更新数据库
            if self._user_id:
                update_AiChatCfg_by_user_id(self._user_id, **{name: value})
            else:
                update_AiChatCfg_map(**{name: value})

            # 更新内存中的记录
            setattr(self._record, name, value)

            # 触发属性更新回调
            self._emit_property_updated(name)
        else:
            super().__setattr__(name, value)

    def __getitem__(self, key):
        """
        支持使用字典索引语法获取属性值
        例如: value = obj["property_name"]

        Args:
            key (str): 属性名

        Returns:
            属性值
        """
        return self.__getattr__(key)

    def __setitem__(self, key, value):
        """
        支持使用字典索引语法设置属性值
        例如: obj["property_name"] = value

        Args:
            key (str): 属性名
            value: 要设置的值
        """
        self.__setattr__(key, value)

    def _parse_position_data_impl(self, position_data):
        """
        解析位置数据，支持以下格式：
        1. JSON字符串格式：{"lat": 39.51783322503789, "lng": -76.20197639555775}
        2. JSON数组格式：[116.31633245364759, 39.83663838626669]
        3. 已经是数组格式：[lng, lat]
        返回统一的 [lng, lat] 数字数组格式
        """
        import json

        if not position_data:
            return []

        # 如果已经是列表格式，直接返回
        if isinstance(position_data, list):
            # 确保是 [lng, lat] 格式
            if len(position_data) >= 2:
                return [float(position_data[0]), float(position_data[1])]
            else:
                return []

        # 如果是字符串，尝试解析
        if isinstance(position_data, str):
            try:
                # 尝试解析为JSON
                parsed_data = json.loads(position_data)

                # 如果解析后是字典格式 {"lat": ..., "lng": ...}
                if isinstance(parsed_data, dict):
                    lat = float(parsed_data.get("lat", 0))
                    lng = float(parsed_data.get("lng", 0))
                    return [lng, lat]

                # 如果解析后是列表格式 [lng, lat] 或 [lat, lng]
                elif isinstance(parsed_data, list) and len(parsed_data) >= 2:
                    # 假设列表中第一个是lng，第二个是lat
                    return [float(parsed_data[0]), float(parsed_data[1])]

            except json.JSONDecodeError:
                # 如果不是有效的JSON，返回空数组
                return []

        # 其他情况返回空数组
        return []
