"""
AI Social Engine Adapter for Backend
This module provides a backend-compatible adapter for the AI social engine
"""
from sqlalchemy.orm import Session
from backend.database.models.chat import AiChatCfg
from backend.modules.sns.map_task_manager import MapTaskManager
from backend.modules.sns.js_task_manager import JsTaskManager
from backend.modules.agent.agent_manager import agent_manager

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

# from prompts_sns import  PromptManager#调用agent模块，里面大量和autogen相关的，非常重


logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """交易类型枚举"""
    SKILL_EXCHANGE = 1
    TOKEN_PURCHASE = 2


class AISocialEngine:
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

        # Load configuration from database
        self.config = self.db.query(AiChatCfg).filter(
            AiChatCfg.is_delete == False
        ).first()

        # Initialize ai_chat_cfg from database - get first record from aichat_cfg table
        self.ai_chat_cfg = self.config

        # Initialize aichatcfg_record for backend compatibility
        # self.aichatcfg_record = self.config

        self.aichatcfg_record = AiChatCfgManager()
        self.aichatcfg_record.connect(self.handle_aichatcfg_property_updated)

        # *******************************************
        self.human_take_over = False
        self.human_instruction = ""
        self.stopping_ai_process_flag = False
        self.pause_flag = False
        self.agent_replying_flag = False
        # Qt GUI signal connection - disabled for backend use
        # self.aichatcfg_record.on_property_updated.connect(self.handle_aichatcfg_property_updated)
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
            logger.info("Starting AI Social Engine...")

            self.started_flag = True
            # self.map_task_status = "started"

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
        self.started_flag = True
        if self.map_task_status == "":
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
            self.map_task_status = "paused"
            icon_path = "images/startcircle.png"  # 暂停时更改为启动图标
            # self.startButton.setText(QtCore.QCoreApplication.translate("MessageWidget", lt("Resume", "继续"), None))
            # self.pauseCheckBox.setChecked(True)
            # self.humantakeoverCheckBox.setEnabled(False)
            # self.humantakeoverCheckBox.setVisible(False)
            # self.show_status_on_map("standby")
        elif self.map_task_status == "paused":
            self.map_task_status = "started"  # 从暂停状态继续
            icon_path = "images/pause.png"  # 继续时更改为暂停图标
            # self.startButton.setText(QtCore.QCoreApplication.translate("MessageWidget", lt("Pause", "暂停"), None))
            # self.pauseCheckBox.setChecked(False)
            # self.humantakeoverCheckBox.setEnabled(True)
            # self.humantakeoverCheckBox.setVisible(True)
            # self.show_status_on_map("thinking")

        # self.startButton.setIcon(QtGui.QIcon(icon_path))  # 更新按钮图标
        # 添加可选操作：根据 self.task_status 更新其他 UI 元素或执行操作

    # *************************************************

    def toggle_pause_task(self):
        self.pause_flag = self.pauseCheckBox.isChecked()
        if self.pause_flag:
            print("Pause task:", self.pause_flag)
        else:
            print("Continue task:", self.pause_flag)

    # a.请求agent指示
    async def ask_agent_and_get_instruction(self, question, system_role_prompt, type_flag="command"):
        if self.stopping_ai_process_flag:
            self.stop_AI_process_finished()
            return

        command_status = self.command_status
        title_str = "Ask agent to get instruction"
        content_str = f"""🟪 *The function is*:

ask_agent_and_get_instruction

🟦 *The Command_status is*:

{command_status}

🟩 *The system_role_prompt is*:

{system_role_prompt}

🟨 *The content send to ai llm is*:

{question} 
"""

        self.write_thinking_process_to_pane(title_str, content_str)

        # Get agent instance from agent_manager by agent_id
        if hasattr(self.ai_chat_cfg, 'agent_id') and self.ai_chat_cfg.agent_id:
            self.agent = agent_manager.get_agent_by_id(self.ai_chat_cfg.agent_id)
            if not self.agent:
                logger.error(f"Failed to load agent with ID: {self.ai_chat_cfg.agent_id}")
                return
        else:
            logger.warning("No agent_id configured in ai_chat_cfg")
            return

        agent = self.agent
        # agent.give_it_plugin(pluginname)#使用配置里面的第一个
        # agent.give_it_km(vector_path, embedding_model_name)
        self.messages_command = []
        self.messages_command.append({"role": "user", "content": question})

        if self.messages_command[0]["role"] != "system":
            self.messages_command.insert(0, {"role": "system", "content": f"{system_role_prompt}"})
        else:
            self.messages_command[0]["content"] = system_role_prompt

        messages = self.messages_command
        # 保存原始system prompt
        original_prompt = agent.role_config.get('system_prompt', '')

        modified_prompt = system_role_prompt + original_prompt

        # 临时修改system prompt
        agent.role_config['system_prompt'] = modified_prompt

        try:
            # 调用Agent进行对话
            reply = await agent.chat(
                message=question,
                conversation_id=f"sns_cjrtesting",
                use_memory=False,
                use_knowledge_base=False
            )
            # return reply
        finally:
            # 恢复原始system prompt
            agent.role_config['system_prompt'] = original_prompt

        self.on_agent_return_instruction(question, reply)

        agent.role_config['system_prompt'] = original_prompt

    # b.agent返回指示
    def on_agent_return_instruction(self, question, content):
        self.agent_replying_flag = False
        if self.stopping_ai_process_flag:
            self.stop_AI_process_finished()
            return
        # content = content.strip('```json').strip('```').strip()
        content = re.sub(r'^\s*```json\s*|\s*```\s*$', '', content, flags=re.DOTALL)
        command_status = self.command_status
        title_str = "Agent return the instruction"
        content_str = f"""🟪 *The function is*:

on_agent_return_instruction

🟫 *The Content Returned is*:

{content}
        """

        self.write_thinking_process_to_pane(title_str, content_str)

        # self.loading_tab.stop_loading()

        if command_status == "ask_agent_to_decompose_task":
            self.taskmng.process_task(event="ask_agent_to_decompose_task_returned", result=content)

        elif command_status == "ask_agent_instruction_to_process_activity":
            self.taskmng.process_task(event="agent_instruction_to_process_activity_returned", instruction=content)

        elif command_status == "ask_agent_instruction_to_process_human_instruction":
            self.taskmng.process_task(event="agent_instruction_to_process_human_instruction_returned", instruction=content)


        elif command_status == "ask_agent_to_review_conversation":
            self.taskmng.process_task(event="ask_agent_to_review_conversation_returned", result=content)

        elif command_status == "ask_agent_to_review_conversation_sell":
            self.taskmng.process_task(event="ask_agent_to_review_conversation_sell_returned", result=content)


        elif command_status == "ask_agent_to_pick_place_list":
            self.taskmng.process_task(event="agent_pick_place_list_returned", result=content)


        elif command_status == "ask_agent_to_pick_people_list":
            self.taskmng.process_task(event="agent_pick_people_list_returned", result=content)

        elif command_status == "ask_agent_start_to_sell_to_a_people":
            self.taskmng.process_task(event="ask_agent_start_to_sell_to_a_people_returned", result=content)

        elif command_status == "ask_agent_start_to_buy_from_a_people":
            self.taskmng.process_task(event="ask_agent_start_to_buy_from_a_people_returned", result=content)


        elif command_status == "ask_agent_how_to_talk":
            self.taskmng.process_task(event="ask_agent_how_to_talk_returned", result=content)


        elif command_status == "ask_agent_to_pick_a_tool_to_buy":
            self.taskmng.process_task(event="ask_agent_to_pick_a_tool_to_buy_returned", result=content)

        elif command_status == "ask_agent_to_bargain_for_buyer":
            self.handle_ask_agent_to_bargain_for_buyer_result(content)

        elif command_status == "ask_agent_to_bargain_for_seller":
            self.handle_ask_agent_to_bargain_for_seller_result(content)


        elif command_status == "ask_agent_to_pick_a_tool":
            self.taskmng.process_task(event="ask_agent_to_pick_a_tool_returned", result=content)


        elif command_status == "ask_agent_to_make_a_deal":
            self.on_agent_make_deal_finished(content)

        elif command_status == "ask_agent_to_use_skill":
            self.on_ask_agent_to_use_skill_return(content)

        elif command_status == "ask_agent_to_use_service":
            self.on_ask_agent_to_use_service_return(content)

        elif command_status == "ask_agent_to_think_after_conversation":
            self.handle_agent_think_after_conversation_result(content)

        elif command_status == "ask_agent_to_arrange_function_list":
            self.handle_agent_arrange_function_list_result(content)

        elif command_status == "ask_agent_to_update_task":
            self.handle_agent_update_task_result(content)

        elif command_status == "run_tool_before_send_good":
            self.handle_send_goods(content)

        elif command_status == "handle_event_before_decistion":
            self.handle_event_before_decistion_result(content)

        elif command_status == "handle_event_after_decistion":
            self.handle_event_after_decistion_result(content)

        elif command_status == "handle_event_receive_msg":
            self.handle_event_receive_msg_result(content)

        elif command_status == "handle_event_before_send_msg":
            self.handle_event_before_send_msg_result(content)

        else:
            pass

        # self.loading_tab.stop_loading()

    def set_current_task_record(self, record):
        self.taskmng.current_task_record = record

    def write_task_plan_to_pane(self, content):
        # self.plan_edit.append(f"{content}")

        print("write_task_plan_to_pane")

    def write_thinking_process_to_pane(self, title, content):
        # 假设 self.thinking_edit 是 QTextEdit 的实例
        self.thinking_step_index += 1

        # 组合新内容
        new_content = f"\n🔶【{self.thinking_step_index}】{title}\n"
        new_content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        new_content += f"{content}\n"

        # self.thinking_edit.append(new_content)

    def write_task_process_to_pane(self, content):
        # 获取ongoing process和task process history的内容
        ongoing_process = self.get_on_going_process()
        task_process_history = self.get_task_process_history()

        # 合并内容并更新plan_edit
        combined_content = f"{ongoing_process}\n{task_process_history}"
        # self.plan_edit.setPlainText(combined_content)
        print("write_task_process_to_pane")

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

    def write_on_going_process_to_pane(self, new_ongoing_content: str):
        # 定义标记
        self.current_ongoing_content = new_ongoing_content
        # 获取ongoing process和task process history的内容
        ongoing_process = self.get_on_going_process()
        task_process_history = self.get_task_process_history()

        # 合并内容并更新plan_edit
        combined_content = f"{ongoing_process}\n{task_process_history}"
        # self.plan_edit.setPlainText(combined_content)
        print("write_on_going_process_to_pane")

    def get_on_going_process(self):
        """
        返回美化后的 ongoing process 文本（纯文本版）
        """
        # 获取基础信息
        profession = self.aichatcfg_record.profession
        lng = f"{self.aichatcfg_record.current_position[0]}" if self.aichatcfg_record.current_position and len(self.aichatcfg_record.current_position) >= 2 else "0"
        lat = f"{self.aichatcfg_record.current_position[1]}" if self.aichatcfg_record.current_position and len(self.aichatcfg_record.current_position) >= 2 else "0"

        # 构建美化文本
        result = "📊 Current Status\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        result += f"💰 Money      : {self.aichatcfg_record.money:,.2f}\n"
        result += f"❤️ Life           : {self.aichatcfg_record.life_point}\n"
        result += f"⚡ Energy      : {self.aichatcfg_record.energy_point}\n"
        result += f"🧑‍️ Profession: {profession}\n"
        result += "📍 Location\n"
        result += f"   ├─ lng : {lng}\n"
        result += f"   └─ lat : {lat}\n\n"

        result += "⏳ On Going\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        result += f"{self.current_ongoing_content or 'N/A'}\n"

        return result

    def show_information(self, info, type_str="1"):
        self.taskmng.js_task_manager.show_information(info, type_str)

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
                self.handle_event_after_decistion(tool_name, instruction)
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

    def handle_event_before_decistion(self, tool_name, ask_content):
        self.command_status = "handle_event_before_decistion"
        tool_record = query_single_tool(name=tool_name)
        tool_id = tool_record.id
        what_to_do = ask_content if ask_content else "请执行"
        self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)

    def handle_event_before_decistion_result(self, ask_content):
        self.command_status = "ask_agent_instruction_to_process_activity"
        self.handle_ask_agent_instruction_to_process_activity(ask_content)

    def handle_event_after_decistion(self, tool_name, instruction):
        self.command_status = "handle_event_after_decistion"
        tool_record = query_single_tool(name=tool_name)
        tool_id = tool_record.id
        what_to_do = instruction
        self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)

    def handle_event_after_decistion_result(self, instruction):
        self.command_status = ""
        self.handle_parse_agent_instruction_for_process_activity(instruction)

    def handle_event_receive_msg(self, tool_name, content, from_str):
        self.command_status = "handle_event_receive_msg"
        tool_record = query_single_tool(name=tool_name)
        tool_id = tool_record.id
        what_to_do = content
        self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)

    def handle_event_receive_msg_result(self, content):
        self.command_status = ""
        from_str = self.current_talk_people["account"]
        self.handle_receiveMessage(content, from_str)

    def handle_event_before_send_msg(self, tool_name, content, conversation_type):
        self.command_status = "handle_event_before_send_msg"
        tool_record = query_single_tool(name=tool_name)
        tool_id = tool_record.id
        what_to_do = content
        self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)

    def handle_event_before_send_msg_result(self, content):
        self.command_status = ""
        if self.talk_type == "sell":
            self.handle_agent_review_conversation_sell_result_final(content)
        else:
            self.handle_agent_review_conversation_result_final(content)

    def go_around(self):
        radius = 500  # 半径，单位为米
        # 初始化当前位置和上一个位置
        current_position = Point(self.aichatcfg_record.current_position[1], self.aichatcfg_record.current_position[0])
        last_position = Point(self.aichatcfg_record.last_position[1], self.aichatcfg_record.last_position[0])

        # 如果位置相同，跳过象限排除
        if current_position == last_position:
            excluded_quadrant = None
        else:
            # 确定上一个位置相对于当前坐标的象限
            last_lon_diff = last_position.longitude - current_position.longitude
            last_lat_diff = last_position.latitude - current_position.latitude

            # 根据差值计算上个位置所在的象限
            if last_lon_diff > 0 and last_lat_diff > 0:
                excluded_quadrant = 1  # 第一象限
            elif last_lon_diff < 0 and last_lat_diff > 0:
                excluded_quadrant = 2  # 第二象限
            elif last_lon_diff < 0 and last_lat_diff < 0:
                excluded_quadrant = 3  # 第三象限
            else:
                excluded_quadrant = 4  # 第四象限

        def generate_random_point(excluded_quadrant):
            while True:
                bearing = random.uniform(0, 360)
                candidate_position = distance(meters=radius).destination(current_position, bearing)

                if abs(candidate_position.latitude) >= 90:
                    candidate_position = Point(89.999 if candidate_position.latitude > 0 else -89.999,
                                               current_position.longitude)

                candidate_position = Point(candidate_position.latitude,
                                           (candidate_position.longitude + 180) % 360 - 180)

                if excluded_quadrant is None:  # 跳过象限排除
                    return candidate_position

                lon_diff = candidate_position.longitude - current_position.longitude
                lat_diff = candidate_position.latitude - current_position.latitude

                if lon_diff > 0 and lat_diff > 0:
                    candidate_quadrant = 1
                elif lon_diff < 0 and lat_diff > 0:
                    candidate_quadrant = 2
                elif lon_diff < 0 and lat_diff < 0:
                    candidate_quadrant = 3
                else:
                    candidate_quadrant = 4

                if candidate_quadrant != excluded_quadrant:
                    return candidate_position

        target_position = generate_random_point(excluded_quadrant)
        self.aichatcfg_record.last_position = self.aichatcfg_record.current_position
        self.aichatcfg_record.current_position = [target_position.longitude, target_position.latitude]

        new_pos = self.aichatcfg_record.current_position
        command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
        self.send_msg_to_map(command)

        result = f"你移动了500米，附近没有任何人。"
        self.update_after_moving()
        return result

    def initial_bearing(self, p1: Point, p2: Point) -> float:
        """
        计算从 p1 指向 p2 的初始方位角（度，0-360）
        """
        lon1, lat1 = math.radians(p1.longitude), math.radians(p1.latitude)
        lon2, lat2 = math.radians(p2.longitude), math.radians(p2.latitude)
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360

    def move_ahead(self, current_position, target_position, target_place):
        move_distance = 500  # 移动距离（米）

        # 转换为 geopy.Point（Point 接受 lat, lon）
        if not isinstance(current_position, Point):
            current_position = Point(current_position[1], current_position[0])

        if not isinstance(target_position, Point):
            target_position = Point(target_position[1], target_position[0])

            # 计算实际距离
        actual_distance = distance(current_position, target_position).m

        try:
            # 情况 1: 已经在目标点（零距离）
            if actual_distance == 0:
                self.aichatcfg_record.last_position = self.aichatcfg_record.current_position
                self.aichatcfg_record.current_position = [current_position.longitude, current_position.latitude]
                return f"您已在目标位置{target_place}。"

            # 情况 2: 剩余距离小于一步
            if actual_distance <= move_distance:
                self.aichatcfg_record.last_position = self.aichatcfg_record.current_position
                self.aichatcfg_record.current_position = [target_position.longitude, target_position.latitude]
                new_pos = self.aichatcfg_record.current_position
                command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
                self.send_msg_to_map(command)
                return f"您已到达目标位置{target_place}（剩余 0 公里）。"

                # 情况 3: 需要计算 bearing

            if abs(current_position.latitude) == 90:
                # 极点：方向不唯一 -> 默认朝向赤道
                bearing = 180 if current_position.latitude > 0 else 0
            else:
                inv = Geodesic.WGS84.Inverse(
                    current_position.latitude, current_position.longitude,
                    target_position.latitude, target_position.longitude
                )
                bearing = inv['azi1'] % 360

            # 沿该方向移动 move_distance
            next_position = distance(meters=move_distance).destination(
                point=current_position,
                bearing=bearing
            )

            self.aichatcfg_record.last_position = self.aichatcfg_record.current_position
            self.aichatcfg_record.current_position = [next_position.longitude, next_position.latitude]

            new_pos = self.aichatcfg_record.current_position
            command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
            self.send_msg_to_map(command)

            print("last_position", self.aichatcfg_record.last_position)
            print("current_position", self.aichatcfg_record.current_position)
            print("target_position", target_position)

            # 重新计算剩余距离
            remaining_distance = distance(next_position, target_position).km

            self.update_after_moving()

            return f"你向目标地点{target_place}移动了{move_distance}米。距离目标还剩 {remaining_distance:.2f} 公里。"


        except Exception as e:
            return f"计算移动坐标时出错：{str(e)}"

    def move_by_route(self):
        command = ("route_move_action", "", "")
        self.send_msg_to_map(command)
        target_place = self.route_target_place
        route_position_list = self.route_position_list
        total_distance = self.route_total_distance
        move_distance = self.route_move_distance
        remaining_distance = total_distance - move_distance
        return f"你向目标地点{target_place}移动了{move_distance}米。距离目标还剩 {remaining_distance:.2f} 公里。"

    def communicate_with_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "communication"
        self.ask_agent_start_to_talk_to_a_people(action_str, human_object)

        # self.taskmng.process_task(action="process_activity", ask_content=ask_content)

    def sell_to_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "sell"
        self.ask_agent_start_to_sell_to_a_people(action_str, human_object)

    def buy_from_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "buy"
        self.ask_agent_start_to_buy_from_a_people(action_str, human_object)

    def use_tools(self):
        result = ""

        result = "使用工具成功。"
        return result

    def pay_to_a_people(self, target_nation_id, target_person_name, count):
        nation_id = self.user_map_setting.get("nationid", "")
        # send_request_pay
        self.money = self.money - count
        result = f"已经成功付款{count}元给{target_person_name}。"
        return result

    def send_good(self):
        good_content = get_key_value("__good_content__")
        result = ""
        job = "医生"
        if job == "doctor":
            pass
        elif job == "driver":
            pass
        elif job == "seller":
            pass
        else:
            pass

        result = "交货成功。"
        return result

    def get_guidance(self):
        user_list_stra = """
        - J宝:是个律师,坐标[116.30375329461533,40.049108567364904],距离7公里\n
        - W宝:是个医生,坐标[116.30690718139134,40.06259235539735],距离8公里\n
                """
        user_list_str = """
暂时没有更多人员
                """
        place_list_str = """
- 北京天安门:很多人在此看升旗。坐标[116.3975,39.9087],距离40公里。\n
- 八达岭长城:著名旅游景点。坐标[116.0204,40.3606],距离60公里。\n
                """

        result = f"""
        您支付了10元费用，获得了如下信息：
        ### 人员列表：
        {user_list_str}
        ### 地址列表：
        {place_list_str}
        """""
        self.money = self.money - 10

        return result

    def set_food_order(self):
        result = ""
        self.aichatcfg_record.energy_point = self.aichatcfg_record.energy_point + 25
        self.aichatcfg_record.move_point = 100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100)
        self.aichatcfg_record.money = self.aichatcfg_record.money - 30
        result = f"你支付了30元购买食物，你的体力值已经恢复为{self.aichatcfg_record.energy_point}%，当前行动力为{self.aichatcfg_record.move_point}%"
        return result

    def set_taxi_order(self, current_position, target_position, target_place):
        point1 = (current_position[1], current_position[0])  # 转换成 (纬度, 经度)
        point2 = (target_position[1], target_position[0])  # 转换成 (纬度, 经度)

        # 使用 geopy 计算距离
        dist = distance(point1, point2).kilometers
        fee = dist * 2.5

        self.aichatcfg_record.money = self.aichatcfg_record.money - fee

        self.aichatcfg_record.last_position = current_position
        self.aichatcfg_record.current_position = target_position
        new_pos = self.aichatcfg_record.current_position
        command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
        self.send_msg_to_map(command)

        result = f"你支付了{fee:.2f}元车费，你已经到达{target_place}，坐标为{target_position}"
        return result

    def call_a_doctor(self):
        result = ""

        self.aichatcfg_record.life_point = self.aichatcfg_record.life_point + 25
        self.aichatcfg_record.move_point = 100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100)
        self.aichatcfg_record.money = self.aichatcfg_record.money - 210
        result = f"你支付了210元远程治疗服务，你的生命值已经恢复为{self.aichatcfg_record.life_point}%，当前行动力为{self.aichatcfg_record.move_point}%"
        return result

    def send_msg_to_map(self, command):
        """
        将命令发送到地图系统。
        """
        action, param_1, param_2 = command
        if action == "Use skills":
            print(f"执行技能：{param_1}")

            # self.message_handler.send_command_to_map(action, param_1, param_2)
        else:
            print(f"执行行动：{action}")

            # self.message_handler.send_command_to_map(action, param_1, param_2)

    def handle_event_before_decistion(self, tool_name, ask_content):
        self.command_status = "handle_event_before_decistion"
        tool_record = query_single_tool(name=tool_name)
        tool_id = tool_record.id
        what_to_do = ask_content if ask_content else "请执行"
        self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)

    def handle_event_before_decistion_result(self, ask_content):
        self.command_status = "ask_agent_instruction_to_process_activity"
        asyncio.create_task(self.handle_ask_agent_instruction_to_process_activity(ask_content))

    def ask_agent_to_run_a_tool(self, tool_id, tool_name, what_to_do):
        role_prompt = "You are a helpful assistant."

        question = f"{tool_id}__AISNS_INT_SEPARATOR__{tool_name}__AISNS_INT_SEPARATOR__{what_to_do}"
        asyncio.create_task(self.ask_agent_and_get_instruction(question, role_prompt, "tool"))
        return "success", "asking the agent to run tool"

    def show_status_on_map(self, status):
        print("show_status_on_map" + status)
        # self.message_handler.show_status_on_map(status)

    def show_alert_on_map(self, msg):
        print("show_status_on_map" + msg)
        # self.message_handler.show_alert_on_map(msg)

    def get_ability_list(self):
        # ability_list_str = get_key_value("ability_list")
        # ability_list = json.loads(ability_list_str)
        # self.ability_list = ability_list

        result = self.ability_list

        return result

    def get_skill_list(self):
        return []
        result = """
                    [{
		"id": "001",
		"name": "get_weather",
		"description": "get weather of a city",
		"place": "Any Place",
		"lng": 0,
		"lat": 0,
		"type": "plugin_tool",
		"address": "Not needed",
		"method": "python call",
		"parameter": {
			"city": "the city to get the weather",
			"date": "the date to get the weather"
		}
	},
	{
		"id": "002",
		"name": "get_stock",
		"description": "get the stock price of a company",
		"place": "Any Place",
		"lng": 0,
		"lat": 0,
		"type": "plugin_tool",
		"address": "Not needed",
		"method": "python call",
		"parameter": {
			"company": "the company name to get the stock price"
		}

	},
	{
		"id": "003",
		"name": "Calculator",
		"description": "a calculator for number",
		"place": "Any Place",
		"lng": 0,
		"lat": 0,
		"type": "plugin_tool",
		"address": "Not needed",
		"method": "python call",
		"parameter": {
			"operator": "choose from `+ / - *` for the calculator to perform calculate",
			"first_number":"the first number",
			"second_number":"the second number"
		}
	}
]
                """

        self.skill_list = json.loads(result)  # 保存到全局变量
        self.available_skills = self.skill_list  # self.skill_list = list(self.available_skills)
        result = self.skill_list
        return result

    def update_skill(self, skill_list):
        self.taskmng.process_task(event="skill_updated")

    def get_plugin_tool_list(self):
        records = query_tool_list()
        default_values = {
            "place": "Any Place",
            "lng": 0,
            "lat": 0,
            "type": "plugin_tool",
            "address": "Not needed",
            "method": "python call"
        }
        # 使用列表推导式生成所需格式的记录
        formatted_records = [
            {
                "id": record.id,  # 直接访问属性
                "name": record.name,
                "description": record.description,
                **default_values  # 展开 default_values 字典以添加缺省值
            }
            for record in records
        ]

        return formatted_records

    def get_service_list(self):
        url = "http://www.ai-sns.org/api/get_service_list/"

        pos = self.aichatcfg_record.current_position

        params = {
            "lng": pos[0],
            "lat": pos[1]
        }
        service_list = self.http_request(url, params)
        return service_list

    def update_service_list(self):
        url = "http://www.ai-sns.org/api/get_service"
        params = {
            "lng": self.aichatcfg_record.current_position[0],
            "lat": self.aichatcfg_record.current_position[1]
        }
        # people={
        #     "name":"Same",
        #     "position":[121.121,23.4554]
        # }
        service_list = self.http_request(url, params)

        return service_list

    def get_tool_list(self):
        service_list = self.get_service_list()
        skill_list = self.get_skill_list()
        plugin_tool_list = self.get_plugin_tool_list()
        tool_list = service_list + skill_list + plugin_tool_list
        return tool_list

    def get_tool_list_for_trade(self):
        service_list = self.get_service_list()
        skill_list = self.get_skill_list()
        tool_list = service_list + skill_list
        return tool_list

    def get_mcp_list_for_trade(self):
        service_list = self.get_service_list()
        skill_list = self.get_skill_list()
        tool_list = service_list + skill_list
        return tool_list

    def get_place_list(self):
        url = "http://www.ai-sns.org/api/get_place_list/"
        params = {
            "lng": self.aichatcfg_record.current_position[0],
            "lat": self.aichatcfg_record.current_position[1]
        }
        place_list = self.http_request(url, params)
        return place_list

    def get_people_list(self):
        url = "http://www.ai-sns.org/api/get_people_list/"
        params = {
            "lng": self.aichatcfg_record.current_position[0],
            "lat": self.aichatcfg_record.current_position[1]
        }
        data = self.http_request(url, params)

        remove_id = self.user_map_setting.get("nationid", "")

        people_list = [item for item in data if item["nation_id"] != remove_id]

        return people_list

    def are_lists_of_dicts_equal(self, list1, list2):
        """
        Checks if two lists of dictionaries are equal, regardless of order.

        Args:
            list1: The first list of dictionaries.
            list2: The second list of dictionaries.

        Returns:
            True if both lists contain the same dictionaries, otherwise False.
        """
        # Sort both lists by their string representations of dicts for consistent comparison
        sorted_list1 = sorted(list1, key=lambda d: str(sorted(d.items())))
        sorted_list2 = sorted(list2, key=lambda d: str(sorted(d.items())))

        return sorted_list1 == sorted_list2

    def get_balance(self):
        token_balance = 1000
        self.token_balance = token_balance
        return token_balance

    def update_balance(self, token_balance):
        self.token_balance = token_balance

    def add_friend(self):
        pass

    def talk_to_a_people(self, content, nationid, account, user_name):
        title_str = "选择人员交谈"
        content_str = f"""🟪 *The function is*:

talk_to_a_people

🟩 *The Content is*:

{lt(f"Talk to a people with {user_name} acount:{account},nationid:{nationid},content:{content}", f"和别人交谈 with {user_name} acount:{account},nationid:{nationid},content:{content}")}
        """

        self.write_thinking_process_to_pane(title_str, content_str)

        current_talk_people = self.current_talk_people
        round = current_talk_people.get("talk_round", 0) + 1
        self.current_talk_people["talk_round"] = round
        command = ("start_talk_to_it", nationid, content)
        self.send_msg_to_map(command)
        self.sendMessage(content, False, account, user_name)

        if account not in self.talk_history:
            self.talk_history[account] = []
        self.talk_history[account].append("Me:" + content)
        self.current_talk_history.append("Me:" + content)

    def move_to_a_place(self, lng, lat):
        # self.write_thinking_process_to_pane(lt(f"move to the place:{lng},{lat}", f"移动到:{lng},{lat}"), "move_to_a_place")
        command = ("move_to_a_place", str(lng), str(lat))
        self.send_msg_to_map(command)
        place_name = self.place_selected[0].get("place_name", "")
        self.place_selected = None
        self.taskmng.process_task(event="arrived_at_place", place_name=place_name)

    def explore_the_map(self):
        # self.write_thinking_process_to_pane("explore the map")
        return
        current_position = self.aichatcfg_record.current_position
        if len(self.taskmng.process_list) < 2:
            last_position = current_position
        else:
            last_position = self.taskmng.process_list[-2].get("current_position", [])

        search_radius = self.search_radius

        # 确保位置不为空
        if not last_position or not current_position:
            return None

        # 将位置转换为WKT（Well-Known Text）格式
        current_position_wkt = f"POINT({current_position[0]} {current_position[1]})"
        last_position_wkt = f"POINT({last_position[0]} {last_position[1]})"

        # SQL查询：寻找符合条件的坐标
        query = """
        SELECT ST_AsText(geom) AS location
        FROM locations
        WHERE ST_DWithin(geom::geography, ST_GeogFromText(%s), %s)
        AND NOT ST_DWithin(geom::geography, ST_GeogFromText(%s), %s)
        LIMIT 1;
        """

        # 执行查询并获取结果
        with db_conn.cursor() as cursor:
            cursor.execute(query, (current_position_wkt, search_radius, last_position_wkt, search_radius / 2))
            result = cursor.fetchone()

        # 返回结果
        if result:
            return result[0]
        return None

    def handle_arrived_at_place(self, place_name):
        # self.write_thinking_process_to_pane(lt(f"Arrived the place:{place_name}", f"到达了:{place_name}"), "handle_arrived_at_place")
        description = f"我成功到达地点：{place_name}。"
        self.taskmng.current_situation = description
        self.taskmng.process_task(event="move_to_a_place_completed", description=description)

    def stop_task(self):
        self.started_flag = False
        self.taskmng.current_task_record = None

    def check_place(self, address, lng, lat):
        command = ("check_place", address, str(lng) + "_" + str(lat));
        self.send_msg_to_map(command)

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

    def ask_agent_instruction_to_process_human_instruction(self, ask_content):
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

        instruction = instruction.strip()
        instruction_dict = json.loads(instruction)
        objective_to_achieve = instruction_dict.get("objective_to_achieve", "")
        human_instruction = instruction_dict.get("human_instruction", "")
        people_to_talk_to = instruction_dict.get("people_to_talk_to", "")
        place_to_move_to = instruction_dict.get("place_to_move_to", "")
        tool_to_use = instruction_dict.get("tool_to_use", "")

        # self.taskmng.set_current_activity_objective(objective_to_achieve)
        # self.taskmng.set_current_objective(objective_to_achieve)

        if "activity_find_people_from_list_to_talk" in instruction:
            self.command_status = "ask_agent_to_pick_people_list"
            provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
            if people_to_talk_to:
                objective_to_achieve = f"如果人员列表中有 {people_to_talk_to} 这个人，请把{people_to_talk_to}作为选择的目标。"
            self.ask_agent_to_pick_people_list(provided_profile_list, objective_to_achieve)
        elif "activity_find_place_from_list_to_move" in instruction:
            self.command_status = "ask_agent_to_pick_place_list"
            objective_to_achieve = self.taskmng.current_objective if self.taskmng.current_objective else self.taskmng.current_sub_task["details"]
            if place_to_move_to:
                objective_to_achieve = f"如果地址列表中有 {place_to_move_to} 这个地方，请把{place_to_move_to}作为选择的目标。{objective_to_achieve}"
            provided_place_list = json.dumps(self.get_place_list(), indent=4, ensure_ascii=False)
            self.ask_agent_to_pick_place_list(objective_to_achieve, provided_place_list)


        elif "activity_find_tool_from_list_to_use" in instruction:
            self.command_status = "ask_agent_to_pick_a_tool"
            task_summary = self.taskmng.get_task_summary()

            provided_tool_list = json.dumps(self.get_tool_list(), indent=4, ensure_ascii=False)

            if tool_to_use:
                objective_to_achieve = f"如果工具列表中有 {tool_to_use} 这个工具，请把{tool_to_use}作为选择的目标。"

            self.ask_agent_to_pick_a_tool(task_summary, provided_tool_list, objective_to_achieve)

        else:
            human_instruction = self.human_instruction
            self.taskmng.process_task(action="process_activity", ask_content="请优先根据人类反馈，做出决策。人类的指令如下：" + human_instruction, human_send_flag=True)

    # 4.让agent选择地址
    def ask_agent_to_pick_place_list(self, objective_to_achieve, provided_place_list):
        """
        向代理请求选择地点列表。

        :param objective_to_achieve: 任务描述
        :param provided_place_list: 提供的地点列表
        """
        self.show_status_on_map("watching")
        self.show_information(lt("Ask Agent to pick a place to move.", "让Agent选择一个地方作为目的地。"))
        task_summary = self.taskmng.get_task_summary()
        curren_situation = self.taskmng.current_situation
        current_process = f"- 当前目标\n{objective_to_achieve}\n- 当前进展\n{curren_situation}"
        role_prompt = get_prompt_by_title("__pick_place_list__")
        role_prompt = role_prompt.replace("__task_summary__", task_summary)
        role_prompt = role_prompt.replace("__current_situation__", current_process)
        role_prompt = role_prompt.replace("__provided_place_list__", provided_place_list)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        self.command_status = "ask_agent_to_pick_place_list"  # 需要这一行
        await self.ask_agent_and_get_instruction(question, role_prompt)

    # 4.1处理agent选择的地址
    def handle_agent_pick_place_list_result(self, content):
        """
        处理代理选择地点的结果。

        :param content: 代理返回的结果内容
        """
        result_list = json.loads(content)
        if result_list:
            result = result_list[0]
            place_id = result["place_id"]
            place_name = result["place_name"]
            place_position = result["place_position"]
            reason_for_selection = result["reason_for_selection"]
            match_score = result["match_score"]
            self.place_selected = result_list

            if self.place_selected:
                self.taskmng.process_task(action="move_to_a_place", place_name=self.place_selected[0]["place_name"], lng=self.place_selected[0]["place_position"][0], lat=self.place_selected[0]["place_position"][1], match_score=match_score)

    # 5.让agent选择一个工具
    def ask_agent_to_pick_a_tool(self, task_summary, provided_tool_list_str, human_objective_to_achieve=""):
        task_summary = self.taskmng.get_task_summary()
        curren_situation = self.taskmng.current_situation
        objective_to_achieve = self.taskmng.get_current_objective()
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        current_process = f"- 当前目标\n{objective_to_achieve}\n- 当前进展\n{curren_situation}"
        role_prompt = get_prompt_by_title("__pick_tool_list__")
        if self.human_take_over and self.human_instruction.startswith("!!!"):
            role_prompt = role_prompt.replace("__task_summary__", self.human_instruction)
            role_prompt = role_prompt.replace("__current_process__", "")
        else:
            role_prompt = role_prompt.replace("__task_summary__", task_summary)
            role_prompt = role_prompt.replace("__current_process__", current_process)
        role_prompt = role_prompt.replace("__provided_tool_list__", provided_tool_list_str)

        question = "请严格遵照要求评估，并严格按照格式输出。"
        await self.ask_agent_and_get_instruction(question, role_prompt)

    # 5.1处理agent选择的工具
    def handle_agent_pick_a_tool_result(self, content):
        """
        处理代理选择云端服务的结果。

        :param content: 代理返回的结果内容
        """
        result_list = json.loads(content)
        if result_list:
            tool = result_list[0]
            id = tool["id"]
            name = tool["name"]
            type_str = tool["type"]
            reason_for_selection = tool["reason_for_selection"]
            tell_the_tool_what_to_do = tool["tell_the_tool_what_to_do"]
            match_score = tool["match_score"]

            self.taskmng.add_process_info_to_list(f"我已经选定了目标工具：name:{name},id:{id},因为{reason_for_selection}")
            flag, res = self.call_tool(tool)
            if flag == "success":
                self.taskmng.add_process_info_to_list("Use_tool使用工具成功，获得如下反馈：" + res)
                self.write_task_process_to_pane("Use_tool使用工具成功，获得如下反馈：" + res + "\n\n")
                # self.write_thinking_process_to_pane("Use_tool使用工具成功，获得如下反馈：" + res)
                self.taskmng.current_situation = "Use_tool使用工具成功，获得如下反馈：" + res
                ask_content = f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\nUse_tool使用工具成功，获得如下反馈：{res}"
                self.taskmng.process_task(action="process_activity", ask_content=ask_content)
            elif flag == "fail":
                self.taskmng.add_process_info_to_list("Use_tool使用工具失败，获得如下反馈：" + res)
                self.taskmng.current_situation = "Use_tool使用工具失败，获得如下反馈：" + res
                self.write_task_process_to_pane("Use_tool使用工具失败，获得如下反馈：" + res + "\n\n")
                # self.write_thinking_process_to_pane("Use_tool使用工具失败，获得如下反馈：" + res)
                ask_content = f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\nUse_tool使用工具失败，获得如下反馈：{res}"
                self.taskmng.process_task(action="process_activity", ask_content=ask_content)

    def call_tool(self, tool):
        tool_id = tool["id"]
        name = tool["name"]
        type_str = tool["type"]
        reason_for_selection = tool["reason_for_selection"]
        tell_the_tool_what_to_do = tool["tell_the_tool_what_to_do"]
        match_score = tool["match_score"]

        tool_list = self.get_tool_list()
        tool_full = self.get_dict_by_id(tool_list, tool_id)
        if type_str.lower() == "built_in_function":
            flag, result = self.call_built_in_function(tool_full)
            return flag, result

        elif type_str.lower() == "plugin_tool":
            flag, result = self.ask_agent_to_run_a_tool(tool_id, name, tell_the_tool_what_to_do)
            return flag, result

        elif type_str.lower() == "web_service":
            flag, result = self.call_built_in_function(tool_full)
            return flag, result

        elif type_str.lower() == "map_application":
            flag, result = self.call_built_in_function(tool_full)
            return flag, result

        elif type_str.lower() == "website":
            flag, result = self.call_built_in_function(tool_full)
            return flag, result

        else:
            flag = "fail"
            result = "任务失败。"
            return flag, result

    def call_built_in_function(self, tool):
        name = tool.get("name", "")
        if name == "Check in":
            flag, result = self.check_in_at_a_place(tool)
            return flag, result

        elif name == "Get clues":
            flag, result = self.get_a_clue_at_a_place(tool)
            return flag, result

        else:
            pass

    def get_dict_by_id(self, dict_list, target_id):
        """
        根据目标 id 从字典列表中查找并返回对应的字典

        :param dict_list: 包含若干字典的列表
        :param target_id: 目标 id 字符串
        :return: 对应 id 的字典，如果没有找到，则返回 None
        """
        # 使用字典推导式将列表转换为以 id 为键的字典，以实现 O(1) 的查找效率
        dict_map = {d['id']: d for d in dict_list}

        # 使用 get 方法返回目标字典，若目标 id 不存在，则返回 None
        return dict_map.get(target_id)

    def ask_agent_to_pick_a_tool_to_buy(self, provided_tool_list_str, human_objective_to_achieve="", human_want_to_buy_str=""):
        task_summary = self.taskmng.get_task_summary()
        curren_situation = self.taskmng.current_situation
        objective_to_achieve = self.taskmng.get_current_objective()
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        my_tool_list = json.dumps(self.get_tool_list(), ensure_ascii=False)

        current_process = f"- 当前目标\n{objective_to_achieve}\n- 当前进展\n{curren_situation}"
        role_prompt = get_prompt_by_title("__pick_tools_to_buy__")
        role_prompt = role_prompt.replace("__task_summary__", task_summary)
        role_prompt = role_prompt.replace("__current_process__", current_process)
        role_prompt = role_prompt.replace("__human_want_to_buy__", human_want_to_buy_str)
        role_prompt = role_prompt.replace("__provided_tool_list__", provided_tool_list_str)
        role_prompt = role_prompt.replace("__my_tool_list__", my_tool_list)

        question = "请严格遵照要求评估，并严格按照格式输出。"
        await self.ask_agent_and_get_instruction(question, role_prompt)

    def handle_agent_pick_a_tool_to_buy_result(self, content):
        """
        处理代理选择云端服务的结果。

        :param content: 代理返回的结果内容
        """
        result_list = json.loads(content)
        if result_list:
            tool = result_list[0]
            self.tool_trade_inquiry(tool)
            # self.taskmng.add_process_info_to_list(f"我已经选定了要购买的目标工具：name:{name},id:{id},因为{reason_for_selection}")

    def ask_agent_to_run_a_tool(self, tool_id, tool_name, what_to_do):
        role_prompt = "You are a helpful assistant."

        question = f"{tool_id}__AISNS_INT_SEPARATOR__{tool_name}__AISNS_INT_SEPARATOR__{what_to_do}"
        await self.ask_agent_and_get_instruction(question, role_prompt, "tool")
        return "success", "asking the agent to run tool"

    # 6.让agent选择人员
    def ask_agent_to_pick_people_list(self, provided_profile_list, human_objective_to_achieve=""):
        # provided_profile_list = json.dumps(self.get_people_list(),indent=4,ensure_ascii=False)
        objective_to_achieve = self.taskmng.get_current_objective()
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        task_summary = self.taskmng.get_task_summary()
        current_process = f"- 当前位置\n{self.current_place}\n- 当前坐标\n{self.aichatcfg_record.current_position}\n- 当前目标\n{objective_to_achieve}\n- 当前进展\n{self.taskmng.current_situation}"
        role_prompt = get_prompt_by_title("__pick_people_list__")
        role_prompt = role_prompt.replace("__task_summary__", task_summary)
        role_prompt = role_prompt.replace("__current_process__", current_process)
        role_prompt = role_prompt.replace("__people__to__select__", provided_profile_list)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        self.command_status = "ask_agent_to_pick_people_list"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def ask_agent_start_to_talk_to_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        role_prompt = get_prompt_by_title("__start_to_talk_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_talk_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_to_pick_people_list"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    def ask_agent_start_to_sell_to_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        role_prompt = get_prompt_by_title("__start_to_sell_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_sell_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_sell_to_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    def ask_agent_start_to_buy_from_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        role_prompt = get_prompt_by_title("__start_to_buy_from_a_people__")

        content_prompt = get_prompt_by_title("__start_to_buy_from_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_buy_from_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    # 6.处理agent选择的人员
    def handle_agent_pick_people_list_result(self, content):
        result = json.loads(content)
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]
            self.current_talk_people = result

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "我未找到目标人员。"

            self.taskmng.process_task(event="agent_pick_people_list_fail")

    def handle_ask_agent_start_to_talk_to_a_people_result(self, content):
        result = json.loads(content)
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]
            self.current_talk_people = result

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "我未找到目标人员。"

            self.taskmng.process_task(event="agent_pick_people_list_fail")

    def handle_ask_agent_start_to_sell_to_a_people_result(self, content):
        result = json.loads(content)
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]
            self.current_talk_people = result

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "我未找到目标人员。"

            self.taskmng.process_task(event="agent_pick_people_list_fail")

    def handle_ask_agent_start_to_buy_from_a_people_result(self, content):
        result = json.loads(content)
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]
            self.current_talk_people = result

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            message = "[AISNS_INT_003_INQUIRY]" + message
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "我未找到目标人员。"

            self.taskmng.process_task(event="agent_pick_people_list_fail")

    def ask_agent_to_review_conversation(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation__")
        # role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
        # role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "## 聊天记录 \n" + messages_history
        await   self.ask_agent_and_get_instruction(question, role_prompt)

    def ask_agent_to_review_conversationbak(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation__")
        role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def ask_agent_to_review_conversation_sell(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation_sell__")
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def ask_agent_to_review_conversation_buy(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation_buy__")
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def handle_agent_review_conversation_result(self, content):
        if self.ai_chat_cfg.event_before_send_msg:
            if self.ai_chat_cfg.event_before_send_msg != "N/A":
                tool_name = self.ai_chat_cfg.event_before_send_msg
                self.handle_event_before_send_msg(tool_name, content, "common")
                return

        self.handle_agent_review_conversation_result_final(content)

    def handle_agent_review_conversation_result_final(self, content):
        content = content.strip()
        result = json.loads(content)
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]

        buy_score = result.get("buy_score", False)
        price = result.get("price", 0)

        if buy_score >= 80 and price >= 0:
            self.send_pay(price)
            return

        if not continue_chat:
            self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
            self.write_task_process_to_pane(f"和朋友沟通后得到如下情况：{current_chat_summary}\n\n")
            self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
            self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}")

        else:
            if not self.taskmng.current_process:
                self.taskmng.current_process = {"rounds_current_person": 0}
            if not self.current_talk_people:
                self.current_talk_people = {
                    "nation_id": "AI123451234567890ABCDEF7894",
                    "account": "yangyang@xabber.de",
                    "location": [
                        116.30690718139134,
                        40.06259235539735
                    ],
                    "nick_name": "W宝",
                    "avatar": "img_woman_hi",
                    "avatar_3d": "smallofficewoman_0_0_0_0_1_0.glb",
                    "profile": "我是个医生",
                    "sns_url": "x.com"
                }

            if self.taskmng.current_process["rounds_current_person"] < self.max_rounds_per_person:
                self.taskmng.current_process["rounds_current_person"] = self.taskmng.current_process["rounds_current_person"] + 1
                self.talk_to_a_people(message, self.current_talk_people["nation_id"], self.current_talk_people["account"], self.current_talk_people["nick_name"])
            else:
                self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
                self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
                self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}")

    def handle_agent_review_conversation_sell_result(self, content):
        if self.ai_chat_cfg.event_before_send_msg:
            if self.ai_chat_cfg.event_before_send_msg != "N/A":
                tool_name = self.ai_chat_cfg.event_before_send_msg
                self.handle_event_before_send_msg(tool_name, content, "sell")
                return

        self.handle_agent_review_conversation_sell_result_final(content)

    def handle_agent_review_conversation_sell_result_final(self, content):
        content = content.strip()
        result = json.loads(content)
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]

        if not continue_chat:
            self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
            self.write_task_process_to_pane(f"和朋友沟通后得到如下情况：{current_chat_summary}\n\n")
            self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
            self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}")

        else:
            if self.taskmng.current_process["rounds_current_person"] < self.max_rounds_per_person:
                self.taskmng.current_process["rounds_current_person"] = self.taskmng.current_process["rounds_current_person"] + 1
                self.talk_to_a_people(message, self.current_talk_people["nation_id"], self.current_talk_people["account"], self.current_talk_people["nick_name"])
            else:
                self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
                self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
                self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}")

    def ask_agent_to_bargain_for_buyer(self, tool_list):
        messages_history = json.dumps(self.current_talk_history, ensure_ascii=False)
        conversation_target = self.taskmng.current_objective
        role_prompt = get_prompt_by_title("__buyer_bargain_content__")
        role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        role_prompt = role_prompt.replace("__tool_list__", tool_list)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def handle_ask_agent_to_bargain_for_buyer_result(self, content):
        result = json.loads(content)
        goal_achieved = result["goal_achieved"]
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]
        self.tool_trade_send_bargain_for_buyer(content)

    def ask_agent_to_bargain_for_seller(self, tool_list):
        messages_history = json.dumps(self.current_talk_history, ensure_ascii=False)
        conversation_target = self.taskmng.current_objective
        role_prompt = get_prompt_by_title("__seller_bargain_content__")
        role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        role_prompt = role_prompt.replace("__tool_list__", tool_list)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def handle_ask_agent_to_bargain_for_seller_result(self, content):
        result = json.loads(content)
        goal_achieved = result["goal_achieved"]
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]

        self.tool_trade_send_bargain_for_seller(content)

    def ask_agent_to_use_service(self, question, service_list, objective_to_achieve):
        role_prompt = get_prompt_by_title("__ask_agent_use_service__")
        role_prompt = role_prompt.replace("__service_list__", service_list)
        role_prompt = role_prompt.replace("__objective_to_achieve__", objective_to_achieve)

        question = question + "\n请根据相关的任务要求，准确选择服务，如果没有合适的服务请返回空列表。"

        self.command_status = "ask_agent_to_use_service"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def on_ask_agent_to_use_service_return(self, content):
        command_status = self.command_status
        code = self.parse_content_to_call_service(content)
        self.call_service(code)

    def parse_content_to_call_service(self, content):
        try:
            data = json.loads(content)
            url = data["address"]
            method = data.get("method", "get").lower()  # Default to 'get' if not specified or invalid
            params = data.get("Parameter", {})  # Use "Parameter" key, handle missing key gracefully

            if not isinstance(url, str) or not url.startswith("http"):
                raise ValueError("Invalid 'address' value. Must be a valid URL.")

            if method not in ["get", "post", "put", "delete", "patch"]:  # Validate method
                raise ValueError("Invalid 'method' value. Supported methods: get, post, put, delete, patch")

            response = self.call_service(url, method, **params)
            return response  # Return the response

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error processing content: {e}")
            return None  # or raise the exception, depending on desired behavior

    def call_service(self, url, method, **params):
        try:
            if method == "get":
                response = requests.get(url, params=params)
            elif method == "post":
                response = requests.post(url, data=params)  # Use 'data' for post
            elif method == "put":
                response = requests.put(url, data=params)
            elif method == "delete":
                response = requests.delete(url, params=params)  # params can also be used with delete
            elif method == "patch":
                response = requests.patch(url, data=params)

            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            self.handle_service_called_result(response.json())  # Assuming the response is JSON, parse and return it
        except requests.exceptions.RequestException as e:
            print(f"Error calling service: {e}")
            return None  # Or handle the error as needed, e.g., retry, log, etc.

    def handle_service_called_result(self, response):
        exit_code = response["exit_code"]
        output = response["output"]
        if exit_code == 0:
            self.taskmng.process_task(event="service_called", result=output)

        else:
            self.taskmng.process_task(event="service_called", result=f"Execute Error,the output:{output}")

    def ask_agent_to_use_skill(self, question, function_name, function_description):
        role_prompt = get_prompt_by_title("__ask_agent_use_skill__")
        role_prompt = role_prompt.replace("XXXXXXXX", function_name)
        role_prompt = role_prompt + "\n" + function_description

        question = "\n" + question + "这是我建议使用的函数：" + function_name + "，请根据相关的任务要求，把相关的任务完成掉。"
        question = question + "\n请输出完整的可独立运行的代码。"
        self.command_status = "ask_agent_to_use_skill"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def on_ask_agent_to_use_skill_return(self, content):
        command_status = self.command_status
        code = self.parse_content_to_code(content)
        self.execute_skill(code)

    def parse_content_to_code(self, content):
        code = content
        return code

    def execute_skill(self, code):
        execute_result = "waiting to impl"
        self.handle_skill_executed_result(execute_result)

    def handle_skill_executed_result(self, execute_result):
        exit_code = execute_result.exit_code
        output = execute_result.output
        code_file = execute_result.code_file
        if exit_code == 0:
            self.taskmng.process_task(event="skill_executed", result=output)

        else:
            self.taskmng.process_task(event="skill_executed", result=f"Execute Error,the output:{output}")

    def tool_trade_show(self, content, nationid, account, user_name):
        # self.write_thinking_process_to_pane(lt(f"Show tool detail to a people with {user_name} acount:{account},nationid:{nationid},content:{content}", f"向别人展现工具详情 with {user_name} acount:{account},nationid:{nationid},content:{content}"), "tool_trade_show")
        tool_list_str = f"AISNS_INT_001_TOOL_DETAIL_SHOW_START\n{json.dumps(self.get_mcp_list_for_trade(), indent=4, ensure_ascii=False)}\nAISNS_INT_001_TOOL_DETAIL_SHOW_END"
        content = f"{content}\n{tool_list_str}"
        command = ("start_talk_to_it", nationid, content)
        self.send_msg_to_map(command)
        self.sendMessage(content, False, account, user_name)
        if account not in self.talk_history:
            self.talk_history[account] = []
        self.talk_history[account].append("Me:" + content)
        self.current_talk_history.append("Me:" + content)

    def tool_trade_order(self, tool_list_str) -> None:
        trade_id = generate_random_id()

        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if tool_list_str:
            tool = json.loads(tool_list_str)
            name = tool["name"]
            mcp_record = query_mcp_mng(name=name)
            detail = mcp_record.description
            price = 6

        try:
            content = {
                "trade_id": trade_id,
                "name": name,
                "detail": detail,
                "price": price
            }

            message = f"AISNS_INT_002_TOOL_ORDER_START\n{json.dumps(content, indent=4, ensure_ascii=False)}\nAISNS_INT_002_TOOL_ORDER_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

        except Exception as e:
            print(f"Tool trade buy error: {str(e)}")

    def tool_trade_order_confirm(self, tool) -> None:
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        try:
            content = tool

            message = f"AISNS_INT_003_TOOL_ORDER_CONFIRM_START\n{json.dumps(content, indent=4, ensure_ascii=False)}\nAISNS_INT_003_TOOL_ORDER_CONFIRM_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

        except Exception as e:
            print(f"tool_trade_order_confirm error: {str(e)}")

    def tool_trade_send_tool(self, tool_list_str) -> None:
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        try:
            tool = json.loads(tool_list_str)
            id = tool.get("id", "")
            name = tool.get("name", "")
            price = tool["price"]
            detail = tool["detail"]
            mcp_record = query_mcp_mng(name=name)
            file_path = mcp_record.file_path

            filename = os.path.join(os.getcwd(), "mcp", file_path + ".json")
            if filename:
                with open(filename, "rt", encoding='utf-8') as file:
                    content = file.read()
            tool["mcp"] = json.loads(content)
            tool_str = json.dumps(tool, ensure_ascii=False, indent=4)
            message = f"AISNS_INT_004_TOOL_SEND_START\n{tool_str}\nAISNS_INT_004_TOOL_SEND_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

            trade_id = generate_random_id()
            trade_type = "S"
            title = name
            trade_with_name = nick_name
            trade_with_account = account
            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account)
            self.add_money(price)
            self.money = self.money + price
        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def send_pay(self, price) -> None:
        trade_id = generate_random_id()
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]
        try:
            message = f"AISNS_INT_001_PAY_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{price}\nAISNS_INT_001_PAY_SEND_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

            self.money = self.money - price
            self.add_money(0 - price)
            trade_type = "B"
            title = f"Trade with {nick_name}"
            detail = "Waiting for goods"
            trade_with_name = nick_name
            trade_with_account = account

            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account)
        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def handle_pay_received(self, price_str) -> None:
        good_str = ""
        trade_id = ""
        talk_history_str = json.dumps(self.current_talk_history, ensure_ascii=False)
        if "__AISNS_INT_SEPARATOR__" in price_str:
            price_str = price_str.strip()
            trade_id = price_str.split("__AISNS_INT_SEPARATOR__")[0]
            trade_price = price_str.split("__AISNS_INT_SEPARATOR__")[1]

        self.current_trade_price = float(trade_price)

        try:
            record = query_AiChatCfg_map()
            profession = record.profession
            handle_after_trade = record.handle_after_trade
            handle_content = record.handle_content
            if profession == "doctor":
                good_str = handle_content
            elif profession == "driver":
                good_str = handle_content
            if profession == "seller":
                good_str = handle_content
            else:
                if handle_after_trade == "发送消息":
                    good_str = handle_content
                else:
                    tool_name = handle_content
                    tool_record = query_single_tool(name=tool_name)
                    tool_id = tool_record.id
                    what_to_do = "## 聊天记录 \n" + talk_history_str
                    print("run tool:", handle_content)
                    print("talk_history_str for run tool", talk_history_str)
                    self.command_status = "run_tool_before_send_good"
                    good_str = self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)
                    return

            self.handle_send_goods(good_str, trade_id)


        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def handle_send_goods(self, good_str, trade_id):
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]
        price = self.current_trade_price

        try:
            if not trade_id:
                trade_id = generate_random_id()

            message = f"AISNS_INT_002_GOOD_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{good_str}\nAISNS_INT_002_GOOD_SEND_END"
            self.talk_to_a_people(message, nation_id, account, nick_name)
            trade_type = "S"
            title = f"Trade with {nick_name}"
            detail = good_str
            trade_with_name = nick_name
            trade_with_account = account
            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account)
            self.add_money(price)
            self.money = self.money + price

        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def handle_good_received(self, goods_str) -> None:
        trade_id = ""
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if "__AISNS_INT_SEPARATOR__" in goods_str:
            goods_str = goods_str.strip()
            trade_id = goods_str.split("__AISNS_INT_SEPARATOR__")[0]
            goods_detail = goods_str.split("__AISNS_INT_SEPARATOR__")[1]

        try:
            update_map_trade(trade_id, detail=goods_detail)
        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def tool_trade_receive_tool(self, tool_list_str) -> None:
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        try:
            tool = json.loads(tool_list_str)
            name = tool["name"]
            price = tool["price"]
            detail = tool.get("detail", "")
            mcp = tool.get("mcp", "")
            content = json.dumps(mcp, ensure_ascii=False, indent=4)

            mcp_id = generate_random_id()
            instruction = ""
            file_path = mcp_id
            requirement = ""
            parameter = ""
            description = detail
            detail = detail
            mcp_type = "0"
            mcp_event = ""
            creator = ""

            add_mcp_mng(mcp_id, name, instruction, file_path, requirement, parameter, description, detail, mcp_type, mcp_event, creator)

            filename = os.path.join(os.getcwd(), "mcp", file_path + ".json")
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(content)  # 将文本写入文件

            trade_id = generate_random_id()
            trade_type = "B"
            title = name
            trade_with_name = nick_name
            trade_with_account = account
            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account)
            self.add_money(0 - price)
            self.money = self.money - price

        except Exception as e:
            print(f"tool_trade_receive_tool error: {str(e)}")

    def tool_trade_inquiry(self, tool) -> None:
        trade_id = generate_random_id()

        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if tool:
            tool.pop("reason_for_selection", None)  # 删除 'reason_for_selection' 键，如果不存在则不抛出异常
            tool.pop("match_score", None)

        try:
            content = tool

            message = f"AISNS_INT_005_TOOL_INQUIRY_START\n{json.dumps(content, indent=4, ensure_ascii=False)}\nAISNS_INT_005_TOOL_INQUIRY_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

        except Exception as e:
            print(f"Tool trade inquiry error: {str(e)}")

    def tool_trade_bargain_for_buyer(self, tool_list_str):
        self.command_status = "ask_agent_to_bargain_for_buyer"
        self.ask_agent_to_bargain_for_buyer(tool_list_str)

    def tool_trade_bargain_for_seller(self, tool_list_str):
        self.command_status = "ask_agent_to_bargain_for_seller"
        self.ask_agent_to_bargain_for_seller(tool_list_str)

    def tool_trade_send_bargain_for_buyer(self, tool_str) -> None:
        tool = json.loads(tool_str)
        trade_id = generate_random_id()

        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if tool:
            tool.pop("reason_for_selection", None)  # 删除 'reason_for_selection' 键，如果不存在则不抛出异常
            tool.pop("match_score", None)

        try:
            content = tool

            message = f"AISNS_INT_006_TOOL_BARGAIN_FOR_BUYER_START\n{json.dumps(content, indent=4, ensure_ascii=False)}\nAISNS_INT_006_TOOL_BARGAIN_FOR_BUYER_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

        except Exception as e:
            print(f"Tool trade inquiry error: {str(e)}")

    def tool_trade_send_bargain_for_seller(self, tool_str) -> None:
        tool = json.loads(tool_str)
        trade_id = generate_random_id()

        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if tool:
            tool.pop("reason_for_selection", None)  # 删除 'reason_for_selection' 键，如果不存在则不抛出异常
            tool.pop("match_score", None)

        try:
            content = tool

            message = f"AISNS_INT_007_TOOL_BARGAIN_FOR_SELLER_START\n{json.dumps(content, indent=4, ensure_ascii=False)}\nAISNS_INT_007_TOOL_BARGAIN_FOR_SELLER_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

        except Exception as e:
            print(f"Tool trade inquiry error: {str(e)}")

    def add_money(self, count):
        record = query_AiChatCfg_map()
        if record.money:
            money = record.money
        else:
            money = 0

        money = money + count

        update_AiChatCfg_map(money=money)

    def tool_trade_buy(self, tool) -> None:
        trade_id = generate_random_id()

        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if tool:
            id = tool["id"]
            name = tool["name"]
            type_str = tool["type"]
            detail = tool.get("description", "No Description")
        try:
            message = f"AISNS_INT_001_TN_{trade_id}_MN_{id}"

            self.talk_to_a_people(message, nation_id, account, nick_name)

            trade_type = "B"
            title = name
            trade_with_name = nick_name
            trade_with_account = account
            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, trade_with_name=trade_with_name, trade_with_account=trade_with_account)


        except Exception as e:
            print(f"Tool trade buy error: {str(e)}")

    def tool_trade_sell(self, trade_id, tool) -> None:
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if tool:
            id = tool["id"]
            name = tool["name"]
            type_str = tool["type"]
            detail = tool.get("description", "No Description")
            file_path = tool.get("file_path", "")
        try:
            message = f"AISNS_INT_002_TN_{trade_id}_SYS_CONTENT_SENDING_FILE"

            self.talk_to_a_people(message, nation_id, account, nick_name)
            to_jid = account
            link = self.send_file_bg(self, file_path, to_jid)

            trade_type = "S"
            title = name
            trade_with_name = nick_name
            trade_with_account = account
            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, link=link, trade_with_name=trade_with_name, trade_with_account=trade_with_account)
        except Exception as e:
            logger.error(f"Tool trade initiate error: {str(e)}")

    def tool_trade_pay(self, trade_id, account) -> None:
        message = f"AISNS_INT_003_TN_{trade_id}"

        self.sendMessage(message, by_click=False, to_jid=account, to_name=None, back_ground=True)

        self.handle_as_coint("001", account)

        update_map_trade(trade_id, status=1)

    def tool_trade_paid(self, trade_id) -> None:
        update_map_trade(trade_id, status=1)

    def handle_as_coint(amount, type_str):
        pass

    def get_tool_list_in_message(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_001_TOOL_DETAIL_SHOW_START(.*?)AISNS_INT_001_TOOL_DETAIL_SHOW_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            tool_list_string = match.group(1).strip()  # 提取并去除首尾空白
            return tool_list_string
        else:
            return None  # 如果没有匹配，返回 None

    def get_tool_order_in_message(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_002_TOOL_ORDER_START(.*?)AISNS_INT_002_TOOL_ORDER_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            tool_list_string = match.group(1).strip()  # 提取并去除首尾空白
            return tool_list_string
        else:
            return None  # 如果没有匹配，返回 None

    def get_order_confirm_in_message(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_003_TOOL_ORDER_CONFIRM_START(.*?)AISNS_INT_003_TOOL_ORDER_CONFIRM_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            tool_list_string = match.group(1).strip()  # 提取并去除首尾空白
            return tool_list_string
        else:
            return None  # 如果没有匹配，返回 None

    def get_tool_mcp_in_message(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_004_TOOL_SEND_START(.*?)AISNS_INT_004_TOOL_SEND_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            tool_list_string = match.group(1).strip()  # 提取并去除首尾空白
            return tool_list_string
        else:
            return None  # 如果没有匹配，返回 None

    def get_tool_inquiry_in_message(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_005_TOOL_INQUIRY_START(.*?)AISNS_INT_005_TOOL_INQUIRY_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            tool_list_string = match.group(1).strip()  # 提取并去除首尾空白
            return tool_list_string
        else:
            return None  # 如果没有匹配，返回 None

    def get_buyer_bargain_in_message(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_006_TOOL_BARGAIN_FOR_BUYER_START(.*?)AISNS_INT_006_TOOL_BARGAIN_FOR_BUYER_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            tool_list_string = match.group(1).strip()  # 提取并去除首尾空白
            return tool_list_string
        else:
            return None  # 如果没有匹配，返回 None

    def get_seller_bargain_in_message(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_007_TOOL_BARGAIN_FOR_SELLER_START(.*?)AISNS_INT_007_TOOL_BARGAIN_FOR_SELLER_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            tool_list_string = match.group(1).strip()  # 提取并去除首尾空白
            return tool_list_string
        else:
            return None  # 如果没有匹配，返回 None

    def get_tool_url_in_message(self, msg):
        # 使用正则表达式提取需要的部分
        match = re.search(r'AISNS_INT_002_TN_(.*?)_SYS_CONTENT_(.*)', msg)

        if match:
            tn_value = match.group(1)  # 提取JC值
            url_value = match.group(2)  # 提取URL值
            return tn_value, url_value
        else:
            return None  # 未找到匹配，返回None

    def get_tool_url_in_message_v2(self, msg):
        # 使用正则表达式提取需要的部分

        match = re.search(r'AISNS_INT_002_TN_(.*?)_SYS_CONTENT_SENDING_FILE', msg)

        if match:
            tn_value = match.group(1)  # 提取JC值
            return tn_value
        else:
            return None  # 未找到匹配，返回None

    def get_tool_confirm_in_message(self, msg, prefix="AISNS_INT_003_TN_"):
        if msg.startswith(prefix):
            # 返回去掉前缀后的部分
            return msg[len(prefix):]
        else:
            # 如果前缀不匹配，返回原字符串
            return ""

    def initiate_tool_tradebak(self, offered_skills: List[str]) -> None:
        """
        主动向对方发起技能交易请求
        Args:
            offered_skills: 对方提供的技能列表
        """
        try:
            # 构建问题传递给大模型
            question = {
                "current_task": self.taskmng.current_objective,
                "skills_offered_to_me": offered_skills,
                "available_for_exchange": self.available_skills
            }

            system_prompt = """你是一个专业的交易AI，请根据以下条件分析交易请求：
            1. 优先推荐技能交换方案（需对方需要我方技能）
            2. 如果无法技能交换，再推荐Token购买
            3. 输出格式必须为JSON：{"decision": "exchange|purchase", "target_skill": "skill_name", "offer_skill": "skill_name|null"}"""

            await  self.ask_agent_and_get_instruction(json.dumps(question, ensure_ascii=False), system_prompt)
        except Exception as e:
            logger.error(f"技能交易发起失败: {str(e)}")

    def respond_to_skill_trade(self, incoming_skills: List[str]) -> None:
        """
        被动响应对方发起的技能交易请求
        Args:
            incoming_skills: 对方提供的技能列表
        """
        try:
            # 构建问题传递给大模型
            question = {
                "current_task": list(self.required_skills),
                "received_skills": incoming_skills,
                "available_for_exchange": list(self.available_skills)
            }

            system_prompt = """你是一个专业的交易AI，请根据以下条件分析交易请求：
            1. 优先推荐技能交换方案（需对方需要我方技能）
            2. 如果无法技能交换，再推荐Token购买
            3. 输出格式必须为JSON：{"decision": "exchange|purchase", "target_skill": "skill_name", "offer_skill": "skill_name|null"}"""

            await  self.ask_agent_and_get_instruction(json.dumps(question, ensure_ascii=False), system_prompt)
        except Exception as e:
            logger.error(f"响应技能交易失败: {str(e)}")

    def send_skill(self, skill_id, skill_name, account, skill_type="function"):
        if skill_type == "function":
            self.create_skill_cfg(skill_id, skill_name)
            file_path = self.create_skill_zip(skill_name)
            self.send_file_bg(file_path, account)

    def create_skill_cfg(skill_id, skill_name):
        """创建技能配置文件并将其写入指定路径。

        参数:
            skill_id (int): 技能的唯一标识符。
            skill_name (str): 技能的名称，用于生成配置文件名。

        返回:
            str: 配置文件的路径。
        """
        # 查询技能记录
        record = query_function_mng(function_id=skill_id)

        # 构建技能配置字典
        skill_cfg = {
            "name": record.name,
            "description": record.description,
            "detail": record.detail
        }

        # 构建配置文件路径
        cfg_file_path = os.path.join(os.getcwd(), "coding", f"{skill_name}.json")

        # 将配置写入 JSON 文件
        try:
            with open(cfg_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(skill_cfg, json_file, ensure_ascii=False, indent=4)
        except IOError as e:
            raise IOError(f"Failed to write config file: {cfg_file_path}. Error: {e}")

        return cfg_file_path

    def create_skill_zip(skill_name):
        """将指定技能的 Python 文件和配置文件压缩成一个 ZIP 文件。

        参数:
            skill_name (str): 技能名称，用于构建文件路径。

        返回:
            str: 压缩文件的路径。
        """
        # 构造文件路径
        python_file_path = os.path.join(os.getcwd(), "coding", f"{skill_name}.py")
        cfg_file_path = os.path.join(os.getcwd(), "coding", f"{skill_name}.json")
        file_path = os.path.join(os.getcwd(), "coding", f"{skill_name}.zip")

        # 确保要压缩的文件存在
        if not os.path.exists(python_file_path):
            raise FileNotFoundError(f"Python file does not exist: {python_file_path}")

        if not os.path.exists(cfg_file_path):
            raise FileNotFoundError(f"Config file does not exist: {cfg_file_path}")

        # 创建 ZIP 文件并写入文件
        with zipfile.ZipFile(file_path, 'w') as zipf:
            # 将 Python 文件添加到 ZIP
            zipf.write(python_file_path, os.path.basename(python_file_path))
            # 将配置文件添加到 ZIP
            zipf.write(cfg_file_path, os.path.basename(cfg_file_path))

        return file_path

    def check_skill(self, msg):
        if self.wait_for_trade_download_flag:
            if ".zip" in msg:
                self.received_skill(msg)
                trade_id = self.wait_for_trade_download_trade_id
                url = msg
                update_map_trade(trade_id, link=url)
                record_trade = query_single_map_trade(trade_id=trade_id)
                self.wait_for_trade_download_trade_id = ""
                self.wait_for_trade_download_flag = False
                tool_id = generate_random_id()
                add_map_tool(plugin_id=tool_id, name=record_trade.title, description=record_trade.detail)

    def received_skill(self, msg):
        url = self.get_url_from_msg(msg)
        file_name = os.path.basename(url)
        file__without_extension = os.path.splitext(file_name)[0]
        file_extension = os.path.splitext(file_name)[1]
        file_path = os.path.join(os.getcwd(), "download", file_name)

        if os.path.exists(file_path):
            current_timestamp = str(time.time()).replace('.', '')
            file_name = file__without_extension + current_timestamp + file_extension
            file_path = os.path.join(os.getcwd(), "download", file_name)
        self.download_file(url, file_path)
        self.skill_install(file_path)

    def check_tool_for_buy(self, msg):
        tool_list_str = self.get_tool_list_in_message(msg)
        return tool_list_str

    def check_tool_for_buyer_bargain(self, msg):
        tool_list_str = self.get_buyer_bargain_in_message(msg)
        return tool_list_str

    def check_tool_for_seller_bargain(self, msg):
        tool_list_str = self.get_seller_bargain_in_message(msg)
        return tool_list_str

    def check_tool_for_inquiry(self, msg):
        tool_list_str = self.get_tool_inquiry_in_message(msg)
        return tool_list_str

    def check_tool_for_order(self, msg):
        tool_list_str = self.get_tool_order_in_message(msg)
        return tool_list_str

    def check_tool_for_order_confirm(self, msg):
        tool_list_str = self.get_order_confirm_in_message(msg)
        return tool_list_str

    def check_tool_for_receive(self, msg):
        tool_list_str = self.get_tool_mcp_in_message(msg)
        return tool_list_str

    def check_tool_for_trade(self, msg):
        tool_list_str = self.get_tool_list_in_message(msg)
        if tool_list_str:
            tool_list = json.loads(tool_list_str)
            self.tool_trade_buy(tool_list[0])

    def check_tool_for_download(self, msg):
        trade_id = self.get_tool_url_in_message_v2(msg)
        if trade_id:
            self.wait_for_trade_download_flag = True
            self.wait_for_trade_download_trade_id = trade_id

        # result = self.get_tool_url_in_message(msg)
        # if result:
        #     trade_id = result[0]
        #     url = result[1]
        #     update_map_trade(trade_id, link=url)

    def check_tool_for_end(self, msg):
        trade_id = self.get_tool_confirm_in_message(msg)
        update_map_trade(trade_id, status=1)

    def check_pay_in_received(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_001_PAY_SEND_START(.*?)AISNS_INT_001_PAY_SEND_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            result = match.group(1).strip()  # 提取并去除首尾空白
            return result
        else:
            return None  # 如果没有匹配，返回 None

    def check_good_in_received(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_002_GOOD_SEND_START(.*?)AISNS_INT_002_GOOD_SEND_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            result = match.group(1).strip()  # 提取并去除首尾空白
            return result
        else:
            return None  # 如果没有匹配，返回 None

    def check_buy_in_received(self, msg):
        pattern = '[AISNS_INT_003_INQUIRY]'

        if pattern in msg:
            return True
        else:
            return False

    def get_url_from_msg(self, msg):
        url = msg
        return url

    def download_file(self, url, file_path):
        # 发送 GET 请求并获取响应对象
        response = requests.get(url)

        # 检查响应状态码是否为成功
        if response.status_code == 200:
            # 打开文件并写入响应内容
            with open(file_path, 'wb') as file:
                file.write(response.content)
            print(f"文件 '{file_path}' 下载成功！")
        else:
            print(f"下载失败，状态码：{response.status_code}")

    def skill_install(self, zip_file_path):
        """
        Installs a skill from a zip file by extracting its contents,
        processing a JSON file for database entry, and moving a Python
        file to a specified directory.

        Parameters:
        zip_file_path (str): Path to the zip file containing the skill.
        """
        # Obtain the base name of the zip file without the extension
        file_without_extension = os.path.splitext(os.path.basename(zip_file_path))[0]
        # Define the extraction path for the zip contents
        extract_to_path = os.path.join(os.getcwd(), "download", "temp", file_without_extension)

        # Unzip the file to the specified directory
        self.unzip_file(zip_file_path, extract_to_path)

        # Define the directory to move Python files to
        python_files_dest = os.path.join(os.getcwd(), "coding")

        # Iterate over all files in the extracted path
        for root, dirs, files in os.walk(extract_to_path):
            for file in files:
                # Get full file path
                file_path = os.path.join(root, file)

                # Check if the file is a JSON file
                if file.endswith('.json'):
                    # Open and load the JSON file
                    with open(file_path, 'r') as json_file:
                        data = json.load(json_file)
                    # Assuming `record` is the parsed data
                    add_function_mng(
                        function_id=generate_random_id(),  # Assuming you generate or fetch this ID elsewhere
                        name=data["name"],
                        file_path=None,  # Assuming you set this path elsewhere, possibly `python_file_path`
                        requirement=None,  # Placeholder, set appropriately
                        parameter=None,  # Placeholder, set appropriately
                        description=data["description"],
                        detail=data["detail"],
                        function_type=None,  # Placeholder, set appropriately
                        function_event=None,  # Placeholder, set appropriately
                        creator=None  # Placeholder, set appropriately
                    )

                # Check if the file is a Python file
                elif file.endswith('.py'):
                    # Define destination path for the Python file
                    python_file_dest = os.path.join(python_files_dest, file)
                    # Copy the Python file to the destination directory
                    shutil.copy(file_path, python_file_dest)

        self.ask_human_to_check_skill()

    def unzip_file(self, zip_file_path, extract_to_path):
        # 创建一个ZipFile对象，并打开要解压的zip文件
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # 解压缩到指定位置
            zip_ref.extractall(extract_to_path)

        print("解压缩完成！")

    def on_agent_make_deal_finished(self, content: str) -> None:
        """
        处理大模型返回的决策结果
        Args:
            content: 大模型返回的决策内容
        """
        try:
            decision_data = self._parse_decision(content)
            if not decision_data:
                logger.warning("无法解析大模型返回结果")
                return

            # 根据决策类型处理交易
            if decision_data["decision"] == TransactionType.SKILL_EXCHANGE:
                self._handle_skill_exchange(
                    target_skill=decision_data["target_skill"],
                    offer_skill=decision_data["offer_skill"]
                )
            elif decision_data["decision"] == TransactionType.TOKEN_PURCHASE:
                self._handle_token_purchase(
                    target_skill=decision_data["target_skill"]
                )
        except Exception as e:
            logger.error(f"交易处理失败: {str(e)}")

    def _parse_decision(self, content: str) -> Optional[Dict]:
        """
        解析大模型的决策结果
        Returns:
            dict: 包含decision_type, target_skill, offer_skill的字典
        """
        try:
            decision = json.loads(content)
            if not all(key in decision for key in ["decision", "target_skill"]):
                raise ValueError("无效的决策格式")

            decision["decision"] = TransactionType.SKILL_EXCHANGE if decision["decision"] == "exchange" else TransactionType.TOKEN_PURCHASE

            if decision["decision"] == TransactionType.SKILL_EXCHANGE and decision["offer_skill"] not in self.available_skills:
                raise ValueError("无法提供的技能不在可交换列表中")

            return decision
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"决策解析失败: {str(e)}")
            return None

    def _handle_skill_exchange(self, target_skill: dict, offer_skill: dict) -> None:
        """处理技能交换逻辑"""
        if offer_skill not in self.available_skills:
            logger.warning("技能交换请求缺少提供技能")
            return

        logger.info(f"执行技能交换：用 [{offer_skill}] 交换 [{target_skill}]")
        self.available_skills = self.remove_dict_from_list(self.available_skills, offer_skill)
        self.required_skills = self.remove_dict_from_list(self.required_skills, target_skill)
        self.available_skills.append(target_skill)

    def remove_dict_from_list(self, dict_list, t_dict):
        """
        从 available_skills 中移除 offer_skill 字典。

        参数:
        offer_skill (dict): 需要移除的字典
        """
        # 过滤列表，保留不等于 offer_skill 的字典
        dict_list = [dict_item for dict_item in dict_list if dict_item != t_dict]
        return dict_list

    def _handle_token_purchase(self, target_skill: dict) -> None:
        """处理Token购买逻辑"""
        if self.token_balance < 100:
            logger.warning("Token余额不足，无法购买技能")
            return

        logger.info(f"使用100 Token购买技能 [{target_skill}]")
        self.token_balance -= 100
        self.required_skills = self.remove_dict_from_list(self.required_skills, target_skill)
        self.available_skills.append(target_skill)

    def on_human_confirm_skill(self):
        skill_list = self.get_skill_list()
        self.update_skill(skill_list)

    def on_human_reject_skill(self):
        self.move_on()

    def ask_human_instruction(self):
        self.human_instruction = ""
        self.command_status = "wait_human_feedback"
        while True:
            time.sleep(1)
            if self.human_instruction:
                self.handle_human_instruction(self.human_instruction)
                self.command_status = ""
                break

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

    def ask_other_people_for_help(self, objective_to_achieve):
        if self.asking_people_for_help_flag == False:
            self.people_list_to_ask_for_help = self.get_people_nearby()
            self.asking_people_for_help_flag = True

        if self.people_list_to_ask_for_help:
            people = self.people_list_to_ask_for_help.pop(0)
            self.current_talk_people = people
            self.ask_a_people_for_help(people)
        else:
            self.asking_people_for_help_flag = False
            self.move_on()

    def ask_a_people_for_help(self, people):
        objective_to_achieve = self.taskmng.current_objective
        self.talk_to_a_people(objective_to_achieve, people["nation_id"], people["account"], people["nick_name"])

    def ask_people_help_success(self, summary):
        self.handle_the_help_summary(summary)

    def ask_people_help_fail(self, summary):
        self.move_on()

    def get_people_nearby(self):
        people_list = self.get_people_list()
        people_list_nearby = self.get_people_by_distance(3, people_list)
        return people_list_nearby

    def get_people_by_distance(self, count, people_list):
        my_position = self.aichatcfg_record.current_position
        """
        返回按与给定位置的距离排序的最近人员列表。

        Args:
            count: 要返回的最近人员数量。
            my_position: 形式为 (longitude, latitude) 的元组或列表。
            people_list: 人员字典列表，每个字典都包含一个“location”键，其值为 (longitude, latitude) 的列表。

        Returns:
            按距离排序的最近人员列表，最多包含 count 个条目。 
            如果 people_list 为空或无效，则返回一个空列表。
        """

        if not people_list or not all("location" in person and len(person["location"]) == 2 for person in people_list):
            return []  # 处理无效输入

        # 将位置转换为 (latitude, longitude) 的形式以适应 geopy
        my_position_converted = (my_position[1], my_position[0])  # 转换为 (latitude, longitude)

        # 使用 geopy 计算距离并存储在元组列表中
        distances = [
            (geopy.distance.geodesic(my_position_converted, (person["location"][1], person["location"][0])).km, person)
            for person in people_list
        ]

        # 按距离排序
        distances.sort()

        # 返回最近的人员，最多 count 个
        return [person for distance, person in distances[:count]]

    def handle_the_help_summary(self, summary):
        result = self.analyze_help_summary(summary)

        if result == "trade_skill":
            self.initiate_tool_trade(self.get_skill_list())
        elif result == "get_help":
            self.taskmng.process_task(event="ask_people_help_success", result=summary)

        elif result == "talk_to_next_people":
            pass
        else:
            self.move_on()

    def analyze_help_summary(self, summary):
        if "trade_skill" in summary:
            result = "trade_skill"
        else:
            result = "get_help"
        return result

    def move_on(self):
        if self.route_flag:
            self.move_on_route()

        else:
            self.move_on_people()

    def move_on_route(self):
        command = ("move_on_route", 500, "")
        self.send_msg_to_map(command)
        self.current_place = "未知"
        self.aichatcfg_record.current_position = [116.01, 29.01]
        self.taskmng.add_process(current_place=self.current_place, current_position=self.aichatcfg_record.current_position)
        ask_content = f"- 当前位置\n{self.current_place}\n- 当前坐标\n{self.aichatcfg_record.current_position}\n- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n{self.taskmng.current_situation}"
        self.taskmng.process_task(action="process_activity", ask_content=ask_content)

    def move_on_people(self):
        people = self.get_nearest_people()
        pos = people.get("location", [])
        new_pos = self.calculate_pos(pos)
        command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
        self.send_msg_to_map(command)
        self.current_place = "未知"
        self.aichatcfg_record.current_position = new_pos
        self.taskmng.add_process(current_place=self.current_place, current_position=self.aichatcfg_record.current_position)
        ask_content = f"- 当前位置\n{self.current_place}\n- 当前坐标\n{self.aichatcfg_record.current_position}\n- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n{self.taskmng.current_situation}"
        self.taskmng.process_task(action="process_activity", ask_content=ask_content)

    def get_nearest_people(self):
        url = "http://www.ai-sns.org/api/get_nearest_people"
        params = {
            "lng": self.aichatcfg_record.current_position[0],
            "lat": self.aichatcfg_record.current_position[1]
        }
        people = {
            "nation_id": "AI123451234567890ABCDEF7894",
            "account": "yangyang@xabber.de",
            "location": [
                116.30690718139134,
                40.06259235539735
            ],
            "nick_name": "W宝",
            "avatar": "img_woman_hi",
            "avatar_3d": "smallofficewoman_0_0_0_0_1_0.glb",
            "profile": "我是个医生",
            "talk_limit": 10,
            "talk_number": 5,
            "llm": "openai-4o",
            "level": 1,
            "credit": 100,
            "status": "1"
        }
        return people
        people = self.http_request(url, params)
        return people

    def calculate_pos(self, pos):
        new_pos = pos
        return new_pos

    def update_after_moving(self):
        lng = self.aichatcfg_record.current_position[0]
        lat = self.aichatcfg_record.current_position[1]
        url = "http://www.ai-sns.org/api/update-location/"
        params = {
            "nation_id": "AI123451234567890ABCDEF7890",
            "password": "securePassword123!",
            "longitude": lng,
            "latitude": lat,
        }
        response = requests.post(url, data=params)
        print(response)

    def http_request(self, url, params=None, method="POST"):
        """
        # GET 请求
        res = http_request("http://example.com/api", {"key": "value"}, method="GET")

        # POST 请求
        res = http_request("http://example.com/api", {"username": "tom", "password": "123"}, method="POST")

        """
        try:
            method = method.upper()
            if method == "GET":
                response = requests.get(url, params=params)
            elif method == "POST":
                response = requests.post(url, data=params)
            else:
                raise ValueError(f"不支持的请求方法: {method}")

            response.raise_for_status()  # 检查 HTTP 状态码
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP错误发生: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"请求错误发生: {req_err}")
        except ValueError as json_err:
            print(f"JSON解析错误: {json_err}")

        return None

    def save_all_user_data(self):
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
        update_AiChatCfg_map(**data)

    def load_all_user_data(self):
        record = query_AiChatCfg_map()
        self.current_place = record.current_place

        # 处理 current_position，支持多种格式
        self.aichatcfg_record.current_position = self._parse_position_data(record.current_position)
        self.last_position = self._parse_position_data(record.last_position)

        self.life_point = record.life_point  # db
        self.energy_point = record.energy_point  # db
        self.move_point = record.move_point  # db
        self.exp_point = record.exp_point  # db
        self.iq_point = record.iq_point  # db
        self.money = record.money  # db
        self.credit = record.credit  # db
        self.level = record.level  # db

        if record.route_status == "playing":
            self.move_by_route_flag = True
        else:
            self.move_by_route_flag = False

        user_map_setting = query_AiChatCfg_map_setting()
        self.user_map_setting = user_map_setting
        print("self.aichatcfg_record", self.aichatcfg_record.current_position)
        print("self.aichatcfg_recordprofile", self.aichatcfg_record.sign)

    def _parse_position_data(self, position_data):
        """
        解析位置数据，支持以下格式：
        1. JSON字符串格式：{"lat": 39.51783322503789, "lng": -76.20197639555775}
        2. JSON数组格式：[116.31633245364759, 39.83663838626669]
        3. 已经是数组格式：[lng, lat]
        返回统一的 [lng, lat] 数字数组格式
        """
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

    def decline_energy(self):
        exp = self.exp_point
        decline_point = 25 * ((100 - exp) / 100)
        self.energy_point = self.energy_point - decline_point
        self.move_point = 100 * (self.life_point / 100) * (self.energy_point / 100)

    def decline_life(self):
        exp = self.exp_point
        decline_point = 25 * ((100 - exp) / 100)
        self.life_point = self.life_point - decline_point
        self.move_point = 100 * (self.life_point / 100) * (self.energy_point / 100)


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
