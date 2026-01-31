from sqlalchemy.orm import Session
from backend.database.models.chat import AiChatCfg
from backend.modules.sns.map_task_manager import MapTaskManager
from backend.modules.sns.js_task_manager import JsTaskManager
from backend.modules.sns.xmpp_client import XMPPClientManager
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


from .xmpp_mixin import XmppMixin
from .tools_mixin import ToolsMixin
from .map_movement_mixin import MapMovementMixin
from .communication_mixin import CommunicationMixin
from .agent_interaction_mixin import AgentInteractionMixin
from .trade_mixin import TradeMixin
from .ui_display_mixin import UIDisplayMixin
from .data_query_mixin import DataQueryMixin
from .event_handler_mixin import EventHandlerMixin
logger = logging.getLogger(__name__)


class AISocialEngine(
    XmppMixin,
    ToolsMixin,
    MapMovementMixin,
    CommunicationMixin,
    AgentInteractionMixin,
    TradeMixin,
    EventHandlerMixin,
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
        self.human_talk_type = 0#0 talk to your ai，1 talk to friend
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

        self.life_point = 100  # db
        self.energy_point = 100  # db
        self.move_point = 100  # db
        self.exp_point = 0  # db
        self.iq_point = 60  # db
        self.money = 1000  # db
        self.credit = 100  # db
        self.level = 1  # db

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

    async def start(self):
        """
        Start the AI social engine
        This is the backend-compatible version of the start() method
        """
        try:
            logger.info("[Step-02],Start AISocialEngine...")
            logger.info("Starting AI Social Engine...")


            self.started_flag = True
            self.map_task_status = ""  # Reset to empty string to allow start_task() to execute

            # Initialize ability list
            self.ability_list = [
                {
                    "function_name": "【activity_find_people_from_list_to_talk】",
                    "function_description": "从人员名单中查找合适的人进行沟通",
                    "status": "enabled"
                },
                {
                    "function_name": "【activity_find_place_from_list_to_move】",
                    "function_description": "从地点列表中查找合适的地方作为目的地",
                    "status": "enabled"
                },
                {
                    "function_name": "【activity_find_tool_from_list_to_use】",
                    "function_description": "使用该功能可以从工具列表中查找合适的工具来调用系统服务",
                    "status": "enabled"
                },
                {
                    "function_name": "【activity_find_task_from_list_to_do】",
                    "function_description": "从任务列表中查找合适的任务来做",
                    "status": "enabled"
                },
                {
                    "function_name": "【activity_find_trade_from_list_to_trade】",
                    "function_description": "从交易列表中查找合适的交易来进行",
                    "status": "enabled"
                },
                {
                    "function_name": "【activity_find_visit_from_list_to_visit】",
                    "function_description": "从探访列表中查找合适的探访来进行",
                    "status": "enabled"
                }
            ]

            # Initialize current situation
            current_situation = f"准备开始执行任务"

            # Get current position from config
            if self.config:
                current_position = self.config.current_position
                logger.info(f"Current position: {current_position}")

            # Start the task processing loop in background
            self.task_runner = asyncio.create_task(self._run_task_loop())

            logger.info("AI Social Engine started successfully")
            logger.info(f"Map task status: {self.map_task_status}")
            logger.info(f"Abilities enabled: {len(self.ability_list)}")

        except Exception as e:
            logger.error(f"Error in start(): {e}", exc_info=True)
            self.started_flag = False
            self.map_task_status = "error"
            raise

    async def stop(self):
        """
        Stop the AI social engine
        """
        try:
            logger.info("Stopping AI Social Engine...")

            self.started_flag = False
            self.map_task_status = "stopped"

            # Cancel the task runner if it's running
            if self.task_runner and not self.task_runner.done():
                self.task_runner.cancel()
                try:
                    await self.task_runner
                except asyncio.CancelledError:
                    pass

            logger.info("AI Social Engine stopped successfully")

        except Exception as e:
            logger.error(f"Error in stop(): {e}", exc_info=True)
            raise

    async def _run_task_loop(self):
        """
        Main task processing loop
        This runs in the background when the engine is started
        """
        try:
            logger.info("[Step-03],Start run_task_loop...")
            while self.started_flag:
                # Process tasks here
                # This is where you would implement the actual AI social engine logic
                logger.debug("AI Social Engine is running...")
                self.start_task()

                # Sleep to prevent busy-waiting
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("Task loop cancelled")
        except Exception as e:
            logger.error(f"Error in task loop: {e}", exc_info=True)

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

    def start_task(self):
        logger.info("[Step-04],Start Start_task...")
        self.started_flag = True
        if self.map_task_status == "":
            print("[Info]:","map_task_status is blank")
            self.map_task_status = "started"
            # icon_path = "images/pause.png"  # 启动时更改为暂停图标
            # self.startButton.setText(QtCore.QCoreApplication.translate("MessageWidget", lt("Pause", "暂停"), None))
            # self.humantakeoverCheckBox.setEnabled(True)
            # self.humantakeoverCheckBox.setVisible(True)
            # self.show_status_on_map("thinking")

            # text_content = self.plan_edit.toPlainText()
            # process_list_start = text_content.find("📜【Process history】")
            # if process_list_start != -1:
            #     process_content = text_content[process_list_start:].strip()
            # else:
            #     process_content = "📜【Process history】"

            # 输出提取的内容
            # print(process_content)
            #
            # self.plan_edit.clear()
            #
            # self.write_task_plan_to_pane(process_content)

            self.started_flag = True
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
            self.taskmng.process_task(action="process_activity")
        elif self.map_task_status == "started":
            print("[Info]:", "map_task_status is started")
            self.map_task_status = "paused"
            icon_path = "images/startcircle.png"  # 暂停时更改为启动图标
            # self.startButton.setText(QtCore.QCoreApplication.translate("MessageWidget", lt("Resume", "继续"), None))
            # self.pauseCheckBox.setChecked(True)
            # self.humantakeoverCheckBox.setEnabled(False)
            # self.humantakeoverCheckBox.setVisible(False)
            # self.show_status_on_map("standby")
        elif self.map_task_status == "paused":
            print("[Info]:", "map_task_status is paused")
            self.map_task_status = "started"  # 从暂停状态继续
            icon_path = "images/pause.png"  # 继续时更改为暂停图标
            # self.startButton.setText(QtCore.QCoreApplication.translate("MessageWidget", lt("Pause", "暂停"), None))
            # self.pauseCheckBox.setChecked(False)
            # self.humantakeoverCheckBox.setEnabled(True)
            # self.humantakeoverCheckBox.setVisible(True)
            # self.show_status_on_map("thinking")

        # self.startButton.setIcon(QtGui.QIcon(icon_path))  # 更新按钮图标
        # 添加可选操作：根据 self.task_status 更新其他 UI 元素或执行操作

    def set_current_task_record(self, record):
        self.taskmng.current_task_record = record

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

    def think(self, **kwargs):
        event = kwargs.get("event", "")
        current_chat_summary = kwargs.get("current_chat_summary", "")
        asyncio.create_task(self.ask_agent_to_update_task())
        pass
        if event == "after_conversation":
            self.taskmng.js_task_manager.show_information(lt("I'm thinking after conversation.", "正在思考对话内容。"))
            self.taskmng.set_command_status("ask_agent_to_think_after_conversation")
            self.ask_agent_to_think_after_conversation(current_chat_summary)

        else:
            pass

    # 1.1让Agent分解任务
    async def ask_agent_to_decompose_task(self, task):
        ability_list = self.get_ability_list()
        role_prompt = get_prompt_by_title("__compose_task__")
        # role_prompt = role_prompt.replace("__ability_list__", json.dumps(ability_list, ensure_ascii=False))
        question = f"""### 具体任务描述
{task}
"""
        # self.write_thinking_process_to_pane(lt(f"Ask agent to decompose the task to a plan:\n{question}", f"请求Agent开始分解任务计划:\n{question}"), "ask_agent_to_decompose_task")
        await self.ask_agent_and_get_instruction(question, role_prompt)

    # 1.2处理任务分解结果
    def handle_agent_plan_task_result(self, sub_task_list_str):
        try:
            # 尝试将字符串解析为 JSON 对象
            sub_task_list = json.loads(sub_task_list_str)
            # 检查解析后的对象是否包含 'tasks' 键并且是一个列表
            if 'tasks' in sub_task_list and isinstance(sub_task_list['tasks'], list):
                # 返回第一个子任务，如果存在的话
                current_sub_task = sub_task_list['tasks'][0] if sub_task_list['tasks'] else None
                current_sub_task_str = json.dumps(current_sub_task, ensure_ascii=False) if current_sub_task else ""
                self.taskmng.sub_task_list = sub_task_list['tasks']
                self.taskmng.current_sub_task = current_sub_task

                update_map_task(self.taskmng.current_task_record.id, sub_task_list=sub_task_list_str, current_sub_task=current_sub_task_str, current_place=self.current_place, current_position=json.dumps(self.aichatcfg_record.current_position, ensure_ascii=False))
                self.taskmng.reload_current_task_record()
                self.taskmng.update_task_plan_in_pane()
                self.taskmng.process_task(event="task_plan_is_decomposed", sub_task_list=sub_task_list)

            else:
                raise ValueError("JSON 中不包含有效的 'tasks' 列表")
        except json.JSONDecodeError as e:
            raise ValueError(f"提供的字符串不是合法的 JSON: {e}")

    def restart_plan(self):
        self.talk_history = {}
        self.handle_agent_plan_task_result(json.dumps(self.taskmng.get_sub_task_list(), indent=4, ensure_ascii=False))
        print("restarted...")

    # 2.1执行子任务前，先review当前任务情况
    async def ask_agent_to_update_task(self):
        self.show_status_on_map("watching")
        self.show_information(lt("Reviewing plan...", "正在重新评估任务计划"))
        self.write_on_going_process_to_pane(lt("Reviewing plan...", "正在重新评估任务计划"))
        role_prompt = get_prompt_by_title("__task_update__")
        task_summary = self.taskmng.get_task_summary_simple()
        role_prompt = role_prompt.replace("__task_summary__", task_summary)
        current_objective = self.taskmng.get_current_objective()
        current_process = self.taskmng.current_situation

        question_to_llm = """
###当前情况
- 当前进展
__current_process__

###需要你处理的工作
- 1.请你根据当前任务进展重新分解一下主任务
- 2.设定一下当前目标
- **要求**：
- 分解的子任务必须使用到一个功能列表中的功能
- 分解的子任务必须能够和主任务有高度相关性
- 分解的子任务必须能够收敛
- 分解的子任务不能陷入死循环
- 设定的目标必须和主任务高度相关，能够朝着完成主任务的方向发展
- 分解的子任务必须覆盖整个主任务，不得有步骤缺失。
- 重点调整一直没有执行成功的子任务
- 请你给我输出如下内容：
子任务列表，当前目标,当前目标和主任务相关性及评分，请按如下json格式输出:
{
    "tasks": [
        {
            "id": 1,
            "title": "任务标题",
            "details": "任务详细内容。",
            "command": "使用的功能指令",
            "completed": "是否已经完成(true/false)",
            "main_task_relevance_score": "和主任务的相关性(0-100分)"
        },
        {
            "id": 2,
            "title": "任务标题",
            "details": "任务详细内容。",
            "command": "使用的功能指令",
            "completed": "是否已经完成(true/false)",
            "main_task_relevance_score": "和主任务的相关性(0-100分)"
        }
    ],
    "current_goal": {
        "target": "当前的主要目标",
        "relevance_and_reason": "设定该目标的原因",
        "relevance_score": "和主任务的相关性(0-100分)"
    }
}
        """
        question_to_llm = question_to_llm.replace("__current_objective__", current_objective)
        question_to_llm = question_to_llm.replace("__current_process__", current_process)
        self.taskmng.set_command_status("ask_agent_to_update_task")
        await self.ask_agent_and_get_instruction(question_to_llm, role_prompt)

    def handle_agent_update_task_result(self, content):
        try:
            # 尝试将字符串解析为 JSON 对象
            sub_task_list_str = content
            sub_task_list = json.loads(content)
            # 检查解析后的对象是否包含 'tasks' 键并且是一个列表
            if 'tasks' in sub_task_list and isinstance(sub_task_list['tasks'], list):
                # 返回第一个子任务，如果存在的话
                current_sub_task = sub_task_list['tasks'][0] if sub_task_list['tasks'] else None
                current_sub_task_str = json.dumps(current_sub_task, ensure_ascii=False) if current_sub_task else ""
                self.taskmng.sub_task_list = sub_task_list['tasks']
                self.taskmng.current_sub_task = current_sub_task
                current_objective = sub_task_list['current_goal']['target']
                self.taskmng.current_objective = current_objective
                current_situation = self.taskmng.current_situation
                update_map_task(self.taskmng.current_task_record.id, sub_task_list=sub_task_list_str, current_sub_task=current_sub_task_str, current_place=self.current_place, current_position=json.dumps(self.aichatcfg_record.current_position, ensure_ascii=False))
                self.taskmng.reload_current_task_record()
                self.taskmng.update_task_plan_in_pane()
                ask_content = f"- 当前位置\n{self.current_place}\n- 当前坐标\n{self.aichatcfg_record.current_position}\n- 当前目标\n{current_objective}\n- 当前进展\n{current_situation}"
                process_over = False
                current_process = self.taskmng.current_process
                tool_used_count = current_process.get("tool_used_count")
                people_communicated_count = current_process.get("people_communicated_count")

                if tool_used_count >= self.max_tool_usage:
                    self.ability_list[2]["status"] = "disabled"

                if people_communicated_count >= self.max_people_comm:
                    self.ability_list[0]["status"] = "disabled"

                if tool_used_count >= self.max_tool_usage and people_communicated_count >= self.max_people_comm:
                    process_over = True

                if not process_over:
                    self.taskmng.process_task(action="process_activity", ask_content=ask_content)
                else:
                    self.reviewing_task = False
                    self.taskmng.process_task(action="explore_the_map", ask_content=ask_content)


            else:
                raise ValueError("JSON 中不包含有效的 'tasks' 列表")
        except json.JSONDecodeError as e:
            raise ValueError(f"提供的字符串不是合法的 JSON: {e}")

    # 3.执行具体子任务
    async def ask_agent_instruction_to_process_activity(self, ask_content):
        if self.ai_chat_cfg.event_before_decistion:
            if self.ai_chat_cfg.event_before_decistion != "N/A":
                tool_name = self.ai_chat_cfg.event_before_decistion
                self.handle_event_before_decistion(tool_name, ask_content)
                return

        await self.handle_ask_agent_instruction_to_process_activity(ask_content)

    async def handle_ask_agent_instruction_to_process_activity(self, ask_content):
        self.show_status_on_map("thinking")
        if not self.started_flag:
            return

        role_prompt = get_prompt_by_title("__main_control__")
        process_info_list_str = "\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.taskmng.process_info_list))
        ability_list = self.get_ability_list()
        # question_to_llm = ask_content + "请告诉我，我接着应该干什么，具体请从功能列表中挑选。"
        question_to_llm = ask_content
        full_ask_content = self.compose_full_ask_content(process_info_list_str, ability_list, question_to_llm)
        await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)

    # 3.1构建完整的请求任务指示的提示词

    def compose_full_ask_content(self, task_description, ability_list, question_to_llm):
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
        # prompt = prompt.replace(f"__current_task_list__", self.current_task_list)
        # prompt = prompt.replace(f"__current_action__", self.current_action)
        prompt = prompt.replace(f"__action_result__", self.action_result)
        prompt = prompt.replace(f"__current_status__", current_status)
        prompt = prompt.replace(f"__tool_list__", json.dumps(self.get_tool_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__people_list__", json.dumps(self.get_people_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__place_list__", json.dumps(self.get_place_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__question_to_llm__", question_to_llm)
        return prompt.strip()

    # 3.2解析大模型关于如何执行任务的指示

    def parse_agent_instruction_for_process_activity(self, instruction):
        if self.ai_chat_cfg.event_after_decistion:
            if self.ai_chat_cfg.event_after_decistion != "N/A":
                tool_name = self.ai_chat_cfg.event_after_decistion
                asyncio.create_task(self.handle_event_after_decistion(tool_name, instruction))
                return

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


        elif "工具" in action_str:
            action_result = self.use_tools()

        elif "付款" in action_str:
            action_result = self.pay_to_a_people("", "", 0)

        elif "交货" in action_str:
            action_result = self.send_good()

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
        self.taskmng.process_task(action="process_activity", ask_content=ask_content)

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

    def stop_task(self):
        self.started_flag = False
        self.taskmng.current_task_record = None

    def human_message_received(self,instruction):

        if self.human_take_over:
            if self.human_talk_type==0:
                if self.agent_replying_flag:
                    #todo 请给前端发送提示："提示", "Agent正在完成上一个任务，请稍等..."
                    return
                self.taskmng_js.show_information(lt(f"Human:{instruction}",f"人类:{instruction}"))
                self.write_on_going_process_to_pane(lt("Human take control...","人类控制中..."))
                self.handle_human_instruction(instruction)
            else:
                self.sendMessage(instruction, True)


    async def ask_agent_instruction_to_process_human_instruction(self, ask_content):
        self.show_status_on_map("thinking")
        if not self.started_flag:
            return

        role_prompt = get_prompt_by_title("__human_instruction_to_process_activity_role__")
        task_description = self.taskmng.get_task_summary()
        ability_list = self.get_ability_list()
        question_to_llm = ask_content
        full_ask_content = self.compose_full_ask_content_human(task_description, ability_list, question_to_llm)
        await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)

    def compose_full_ask_content_human(self, task_description, ability_list, question_to_llm):
        prompt = get_prompt_by_title("__human_instruction_to_process_activity_content__")
        prompt = prompt.replace(f"__human_instruction__", question_to_llm)
        # prompt = prompt.replace(f"__ability_list__", json.dumps(ability_list, indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__tool_list__", json.dumps(self.get_tool_list(), indent=4, ensure_ascii=False))
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
            self.taskmng.process_task(action="process_human_instruction", ask_content=human_instruction, human_send_flag=True)

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
