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
# Mainly used for sending attachments
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
from db.DBFactory import query_SystemCfg
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
        self._background_tasks = set()
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
        # self.update_resource_display()  # Move to after load_all_user_data() is called

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
        self.map_mode = 'org'  # Two modes: map_application (for service scenes like 3D aigccenter) and org (for map)
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

        # Plugin-related
        self.chess_role = None
        self.chinese_chess_role = None
        self.system_role_prompt = "You are a helpful assistant who provides concise and accurate information."

        # Initialize global variables
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
                "function_description": "Find a suitable person from the people list to communicate with. Use this when you need help or guidance. Do not filter people in multiple steps.",
                "status": "enabled"
            },
            {
                "function_name": "【activity_find_place_from_list_to_move】",
                "function_description": "Find a suitable destination from the place list. Use this when you need to go somewhere. Do not filter places in multiple steps.",
                "status": "enabled"
            },
            {
                "function_name": "【activity_find_tool_from_list_to_use】",
                "function_description": "Find an appropriate tool from the tool list to call system services or AI skills to solve problems that other functions cannot. Do not filter tools in multiple steps.",
                "status": "enabled"
            }
        ]
        self.skill_list = []
        self.started_flag = False

        # In-memory IQ tracking counters (not persisted)
        self._instruction_total_count = 0
        self._instruction_invalid_count = 0

    async def async_init(self):
        """
        Async initialization method.
        Used to perform additional async initialization after the instance is created.
        """
        logger.info("[Step-01],Init AISocialEngine...")
        logger.info("Async initializing AISocialEngine...")
        # Add any initialization code that must run in an async context here
        # Most initialization is already done in __init__
        logger.info("AISocialEngine async initialization complete")
        self.command_status = ""
        # Initialize the skill set required for the current task (example)
        self.required_skills = []
        # Initialize the set of skills available for exchange
        self.available_skills = []
        self.route_flag = False
        # Initialize token balance
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
        self.max_people_comm = 4  # Max number of people to communicate with
        self.max_rounds_per_person = 6  # Max rounds per person
        self.max_place_arrived = 3  # Max places to arrive
        self.min_place_move_score = 80  # Min score to move to a place
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

        self.active_conversation = None
        self.conversation_inbox = {}
        self.conversation_timeout_seconds = 60
        self._conversation_last_activity_ts = 0.0
        self._conversation_timeout_task = None

        self.contact_cooldown_seconds = 300
        self.contact_recent_limit = 3
        self._contact_last_time = {}
        self._recent_contacts = {
            "sell": [],
            "buy": [],
            "communication": [],
        }
        self._pending_talk_objective = ""
        self._pick_person_retry_count = {
            "sell": 0,
            "buy": 0,
            "communication": 0,
        }

        try:
            cfg = query_SystemCfg(is_delete=False)
            if cfg is not None:
                v = getattr(cfg, "conversation_timeout_seconds", None)
                if v is not None:
                    self.conversation_timeout_seconds = int(v)
                v = getattr(cfg, "contact_cooldown_seconds", None)
                if v is not None:
                    self.contact_cooldown_seconds = int(v)
                v = getattr(cfg, "contact_recent_limit", None)
                if v is not None:
                    self.contact_recent_limit = int(v)
        except Exception:
            pass

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

                self.taskmng.current_situation = f"Preparing to start the task"
                self.ability_list = [
                    {
                        "function_name": "【activity_find_people_from_list_to_talk】",
                        "function_description": "Find a suitable person from the people list to communicate with. Use this when you need help or guidance. Do not filter people in multiple steps.",
                        "status": "enabled"
                    },
                    {
                        "function_name": "【activity_find_place_from_list_to_move】",
                        "function_description": "Find a suitable destination from the place list. Use this when you need to go somewhere. Do not filter places in multiple steps.",
                        "status": "enabled"
                    },
                    {
                        "function_name": "【activity_find_tool_from_list_to_use】",
                        "function_description": "Find an appropriate tool from the tool list to call system services or AI skills to solve problems that other functions cannot. Do not filter tools in multiple steps.",
                        "status": "enabled"
                    }
                ]
                t = asyncio.create_task(self.taskmng.process_task(action="process_activity"))
                self._background_tasks.add(t)
                t.add_done_callback(lambda _t: self._background_tasks.discard(_t))
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

            # Set paused state
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

            # Set running state
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

    def stop_AI_process_finished(self):
        try:
            self.stopping_ai_process_flag = False
            self.agent_replying_flag = False
            self.pause_flag = False
            self.command_status = ""
        except Exception:
            pass

    async def stop_engine(self):
        """Stop the AI social engine"""
        try:
            logger.info("Stopping AI Social Engine...")

            try:
                for t in list(getattr(self, '_background_tasks', set()) or set()):
                    try:
                        if t and not t.done():
                            t.cancel()
                    except Exception:
                        pass
                await asyncio.sleep(0)
            except Exception:
                pass

            self.stopping_ai_process_flag = True
            self.started_flag = False
            self.pause_flag = False
            self.human_take_over = False
            self.map_task_status = "stopped"
            self.command_status = ""

            try:
                self.current_ongoing_content = ""
            except Exception:
                pass

            try:
                if hasattr(self, 'taskmng') and self.taskmng is not None:
                    self.taskmng.init_task_mng()
            except Exception:
                pass

            try:
                if hasattr(self, 'thinking_step_index'):
                    self.thinking_step_index = 0
                if hasattr(self, 'process_step_index'):
                    self.process_step_index = 0
            except Exception:
                pass

            await asyncio.sleep(0)
            self.stop_AI_process_finished()

            logger.info("AI Social Engine stopped successfully")
            return {
                "success": True,
                "message": "AI Social Engine stopped successfully",
                "status": "stopped"
            }

        except Exception as e:
            logger.error(f"Error in stop_engine(): {e}", exc_info=True)
            self.map_task_status = "error"
            self.stop_AI_process_finished()
            return {
                "success": False,
                "message": f"Failed to stop AI Social Engine: {str(e)}",
                "status": "error"
            }

    async def restart_engine(self):
        """Restart the AI social engine"""
        try:
            logger.info("Restarting AI Social Engine...")

            await self.stop_engine()

            try:
                if hasattr(self, 'thinking_step_index'):
                    self.thinking_step_index = 0
                if hasattr(self, 'process_step_index'):
                    self.process_step_index = 0
            except Exception:
                pass

            try:
                if hasattr(self, 'taskmng') and self.taskmng is not None:
                    self.taskmng.init_task_mng()
            except Exception:
                pass

            self.map_task_status = ""
            await self.start_engine()

            logger.info("AI Social Engine restarted successfully")
            return {
                "success": True,
                "message": "AI Social Engine restarted successfully",
                "status": "started"
            }

        except Exception as e:
            logger.error(f"Error in restart_engine(): {e}", exc_info=True)
            self.map_task_status = "error"
            return {
                "success": False,
                "message": f"Failed to restart AI Social Engine: {str(e)}",
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
        Get task processing history and return a formatted string.
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
        # question_to_llm = ask_content + "Please tell me what I should do next; pick specifically from the function list."
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
* Money: {money:.2f} CNY
* Life: {life_point}%
* Energy: {energy_point}%
* Action points: {move_point}%
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
        prompt = prompt.replace(f"__service_list__", json.dumps(self.get_service_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__people_list__", json.dumps(self.get_people_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__place_list__", json.dumps(self.get_place_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__question_to_llm__", question_to_llm)
        return prompt.strip()

    def parse_agent_instruction_for_process_activity(self, instruction):
        self.handle_parse_agent_instruction_for_process_activity(instruction)

    def _update_iq_point_from_counters(self):
        if self._instruction_total_count > 0:
            self.aichatcfg_record.iq_point = round(
                (1 - self._instruction_invalid_count / self._instruction_total_count) * 100
            )
        else:
            self.aichatcfg_record.iq_point = 100

    def handle_parse_agent_instruction_for_process_activity(self, instruction):
        print("llm return instruction:", instruction)
        instruction = instruction.strip()
        self.current_task_list = self.get_current_task_list(instruction)
        action_str = self.get_next_action(instruction)
        self.current_action = action_str

        print("current action_str:", action_str)

        # Increment exp_point by 1 on each call
        current_exp = int(self.aichatcfg_record.exp_point or 0)
        self.aichatcfg_record.exp_point = current_exp + 1

        # Increment in-memory instruction total count for IQ tracking
        self._instruction_total_count += 1

        if self.temp_index > 7:
            self.temp_index = 0
        else:
            self.temp_index = self.temp_index + 1

        if self.temp_index_2 > 3:
            self.temp_index_2 = 0
        else:
            self.temp_index_2 = self.temp_index_2 + 1

        if self.move_by_route_flag:
            self.write_on_going_process_to_pane(f"{action_str}(Changed to 'move by route' due to the movement setting.")
        else:
            self.write_on_going_process_to_pane(action_str)
        # self.loading_tab.stop_loading()

        if "1_EXPLORE_NEARBY" in action_str:

            if self.move_by_route_flag:
                action_result = self.move_by_route()
            elif self.target_position:
                action_result = self.move_ahead(self.aichatcfg_record.current_position, self.target_position, self.target_place)
            else:
                action_result = self.go_around()

        elif "2_WALK_TO" in action_str:

            if self.move_by_route_flag:
                action_result = self.move_by_route()
            else:
                # Extract the JSON part using regex
                json_match = re.search(r'\{.*\}', action_str)
                if not json_match:
                    self._instruction_invalid_count += 1
                    self._update_iq_point_from_counters()
                    return None, None

                # Parse JSON
                try:
                    data = json.loads(json_match.group(0))
                except Exception:
                    self._instruction_invalid_count += 1
                    self._update_iq_point_from_counters()
                    return None, None

                # Extract required fields
                place = data.get('place')
                position = data.get('position')
                target_position = position

                self.target_position = target_position
                self.target_place = place

                action_result = self.move_ahead(self.aichatcfg_record.current_position, target_position, place)

        elif "3_COMMUNICATE" in action_str:
            self.communicate_with_a_people(action_str, instruction)
            self._update_iq_point_from_counters()
            return

        elif "4_PROMOTE" in action_str:
            self.sell_to_a_people(action_str, instruction)
            self._update_iq_point_from_counters()
            return

        elif "5_PURCHASE" in action_str:
            self.buy_from_a_people(action_str, instruction)
            self._update_iq_point_from_counters()
            return

        elif "6_WEB_SERVICE" in action_str:
            self.use_service(action_str, instruction)
            self._update_iq_point_from_counters()
            return

        elif "7_NAVIGATION" in action_str:
            if self.move_by_route_flag:
                # If moving by route, navigation is not needed
                action_result = self.move_by_route()
            else:
                action_result = self.get_guidance()

        elif "8_FOOD_DELIVERY" in action_str:
            action_result = self.set_food_order()

        elif "9_CALL_TAXI" in action_str:
            if self.move_by_route_flag:
                action_result = self.move_by_route()
            else:
                # Extract the JSON part using regex
                json_match = re.search(r'\{.*\}', action_str)
                if not json_match:
                    self._instruction_invalid_count += 1
                    self._update_iq_point_from_counters()
                    return None, None

                # Parse JSON
                try:
                    data = json.loads(json_match.group(0))
                except Exception:
                    self._instruction_invalid_count += 1
                    self._update_iq_point_from_counters()
                    return None, None

                # Extract required fields
                place = data.get('place')
                position = data.get('position')

                target_position = position
                action_result = self.set_taxi_order(self.aichatcfg_record.current_position, target_position, place)

        elif "10_REMOTE_MEDICAL" in action_str:
            action_result = self.call_a_doctor()
        else:
            action_result = f"'{action_str}' is not in the list of valid actions."
            # Increment in-memory instruction invalid count for IQ tracking
            self._instruction_invalid_count += 1

        self._update_iq_point_from_counters()

        self.action_result = action_result
        self.taskmng.add_process_info_to_list(f"system:{action_result}")
        self.write_task_process_to_pane(action_result + "\n\n")
        self.show_alert_on_map(action_result)
        ask_content = instruction
        asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=ask_content))

    def get_next_action(self, instruction):
        # Define delimiter markers
        delimiter = "### Next Action"

        # Check whether delimiter exists
        if delimiter in instruction:
            # Split and take the last part (in case there are multiple identical markers)
            parts = instruction.split(delimiter, 1)
            return parts[1].strip() if len(parts) > 1 else ""
        delimiter = "Next Action"
        if delimiter in instruction:
            # Split and take the last part (in case there are multiple identical markers)
            parts = instruction.split(delimiter, 1)
            return parts[1].strip() if len(parts) > 1 else ""

        return ""

    def get_current_task_list(self, text):
        start_marker = "### Current Task List"
        end_marker = "### Next Action"
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
                    # TODO: Send a prompt to frontend: "Hint", "Agent is completing the previous task, please wait..."
                    return
                self.taskmng_js.show_information(lt(f"Human:{instruction}", f"Human:{instruction}"))
                self.write_on_going_process_to_pane(lt("Human take control...", "Human is in control..."))
                self.handle_human_instruction(instruction)
            else:
                self.sendMessage(instruction, True)

    async def ask_agent_instruction_to_process_human_instruction(self, ask_content):
        self.show_status_on_map("thinking")
        if not self.started_flag:
            logger.warning("Engine not started when processing human instruction, skipping")
            return

        role_prompt = get_prompt_by_title("__human_instruction_to_process_activity_role__")
        task_description = self.taskmng.get_task_summary()
        question_to_llm = ask_content
        full_ask_content = self.compose_full_ask_content_human(task_description,  question_to_llm)
        await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)

    def compose_full_ask_content_human(self, task_description,  question_to_llm):
        prompt = get_prompt_by_title("__human_instruction_to_process_activity_content__")
        prompt = prompt.replace(f"__human_instruction__", question_to_llm)
        prompt = prompt.replace(f"__service_list__", json.dumps(self.get_service_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__people_list__", json.dumps(self.get_people_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__place_list__", json.dumps(self.get_place_list(), indent=4, ensure_ascii=False))

        return prompt.strip()

    def parse_agent_instruction_for_process_human_instruction(self, instruction):
        self.parse_agent_instruction_for_process_activity(instruction)
        return

    async def _ensure_engine_ready_for_priority_action(self):
        """Ensure engine is in started state and cancel current background tasks.

        Used when a priority action (human instruction, talk_to_it from frontend)
        needs to execute immediately. This method will:
        1. Resume if paused, or start if stopped / not started.
        2. Cancel all running background tasks so the priority action is not blocked.
        3. Reset flags that might prevent the new action from executing.
        """
        status = getattr(self, "map_task_status", "")
        started = getattr(self, "started_flag", False)

        # --- bring engine to 'started' state ---
        if status == "paused":
            logger.info("Priority action: resuming paused engine")
            await self.resume_engine()
        elif status == "stopped" or not started:
            logger.info("Priority action: starting engine from stopped/uninitialised state")
            self.map_task_status = ""
            await self.start_engine()

        # --- cancel running background tasks so they don't compete ---
        try:
            for t in list(getattr(self, "_background_tasks", set()) or set()):
                try:
                    if t and not t.done():
                        t.cancel()
                except Exception:
                    pass
            self._background_tasks.clear()
        except Exception:
            pass

        # --- reset blocking flags ---
        self.stopping_ai_process_flag = False
        self.agent_replying_flag = False
        self.command_status = ""
        logger.info("Engine ready for priority action")

    def handle_human_instruction(self, human_instruction):
        if human_instruction:
            if human_instruction.startswith("@Memory:"):
                memory_content = human_instruction.split(':', 1)[1].strip()
                messages = [
                    {"role": "user", "content": f"{memory_content}"}
                ]
                add_memory_list(messages)
                return

            # Ensure engine is running and interrupt current tasks for priority execution
            asyncio.create_task(self._ensure_engine_ready_for_priority_action())

            # Merge human instructions into full_ask_content
            self.human_instruction = human_instruction
            asyncio.create_task(self.taskmng.process_task(action="process_human_instruction", ask_content=human_instruction, human_send_flag=True))

    def handle_aichatcfg_property_updated(self, property_name):
        """
        Handle AiChatCfg property updates.
        When specific properties change, update related UI elements.

        Args:
            property_name (str): Updated property name
        """
        # Properties that should trigger chart updates
        chart_related_properties = [
            'iq_point', 'energy_point', 'life_point',
            'move_point', 'exp_point', 'money',
            'credit', 'level'
        ]

        # Properties that should trigger ongoing process panel updates
        process_pane_related_properties = [
            'profession', 'current_position', 'money',
            'life_point', 'energy_point'
        ]

        # Update chart if the property is chart-related
        if property_name in chart_related_properties:
            self.update_map_charts()

        # Update panel if the property is ongoing-process-related
        if property_name in process_pane_related_properties:
            self.write_on_going_process_to_pane(self.current_ongoing_content or "")


class AiChatCfgManager:
    """
    Class for managing AiChatCfg DB records.
    Supports reading the latest values via attribute access and updating DB records via assignment.
    """

    def __init__(self, user_id=None):
        """
        Initialize AiChatCfgManager.

        Args:
            user_id (str, optional): User ID. Defaults to None and uses the first record.
        """
        self._user_id = user_id
        self._record = None
        self._callbacks = []  # Callback function list
        self._load_record()

    def connect(self, callback):
        """
        Register a callback, invoked when a property is updated.

        Args:
            callback: Callback function receiving one argument (property_name)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def disconnect(self, callback):
        """
        Unregister a callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _emit_property_updated(self, property_name):
        """
        Trigger property update callbacks.

        Args:
            property_name: Updated property name
        """
        for callback in self._callbacks:
            try:
                callback(property_name)
            except Exception as e:
                logger.error(f"Error in property update callback: {e}")

    def _load_record(self):
        """Load the DB record."""
        if self._user_id:
            self._record = query_AiChatCfg_map_setting(user_id=self._user_id)
        else:
            self._record = query_AiChatCfg_map()

    def _refresh_record(self):
        """Refresh the record to get the latest data."""
        self._load_record()

    def __getattr__(self, name):
        """
        Called when accessing an attribute that does not exist.
        Used to read a field value from the DB record.

        Args:
            name (str): Attribute name

        Returns:
            Field value
        """
        # Avoid calling this during __init__
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        # Refresh record to get latest data
        self._refresh_record()

        # Ensure record exists
        if self._record is None:
            raise AttributeError(f"No record found in database")

        # Special handling for current_position
        if name == 'current_position':
            raw_position = getattr(self._record, name, None)
            # Create a temporary instance to call _parse_position_data
            temp_instance = type('Temp', (object,), {})()
            temp_instance._parse_position_data = lambda pos_data: self._parse_position_data_impl(pos_data)
            return temp_instance._parse_position_data(raw_position)

        # Special handling for other position-related fields
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

        # Check attribute exists
        if hasattr(self._record, name):
            return getattr(self._record, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """
        Called when setting an attribute.
        Used to update a field value in the DB record.

        Args:
            name (str): Attribute name
            value: Value to set
        """
        # Handle internal attributes
        if name.startswith('_') or name in ['user_id']:
            super().__setattr__(name, value)
            return

        # Fields requiring special handling
        position_fields = ['current_position', 'last_position', 'home_position',
                           'route_start', 'route_end', 'route_current_position']

        # If it's a position field and value is list/dict, serialize to string
        if name in position_fields and isinstance(value, (list, dict)):
            import json
            value = json.dumps(value, ensure_ascii=False)

        # For other attributes, update DB record
        if '_record' in self.__dict__ and self._record is not None:
            # Update DB
            if self._user_id:
                update_AiChatCfg_by_user_id(self._user_id, **{name: value})
            else:
                update_AiChatCfg_map(**{name: value})

            # Update in-memory record
            setattr(self._record, name, value)

            # Trigger property update callbacks
            self._emit_property_updated(name)
        else:
            super().__setattr__(name, value)

    def __getitem__(self, key):
        """
        Support dict-style indexing to get attribute values.
        Example: value = obj["property_name"]

        Args:
            key (str): Attribute name

        Returns:
            Attribute value
        """
        return self.__getattr__(key)

    def __setitem__(self, key, value):
        """
        Support dict-style indexing to set attribute values.
        Example: obj["property_name"] = value

        Args:
            key (str): Attribute name
            value: Value to set
        """
        self.__setattr__(key, value)

    def _parse_position_data_impl(self, position_data):
        """
        Parse position data. Supports the following formats:
        1. JSON string: {"lat": 39.51783322503789, "lng": -76.20197639555775}
        2. JSON array: [116.31633245364759, 39.83663838626669]
        3. Already an array: [lng, lat]
        Returns a normalized numeric array: [lng, lat]
        """
        import json

        if not position_data:
            return []

        # If it's already a list, return it directly
        if isinstance(position_data, list):
            # Ensure [lng, lat] format
            if len(position_data) >= 2:
                return [float(position_data[0]), float(position_data[1])]
            else:
                return []

        # If it's a string, try to parse it
        if isinstance(position_data, str):
            try:
                # Try parsing as JSON
                parsed_data = json.loads(position_data)

                # Dict format: {"lat": ..., "lng": ...}
                if isinstance(parsed_data, dict):
                    lat = float(parsed_data.get("lat", 0))
                    lng = float(parsed_data.get("lng", 0))
                    return [lng, lat]

                # List format: [lng, lat] or [lat, lng]
                elif isinstance(parsed_data, list) and len(parsed_data) >= 2:
                    # Assume [lng, lat]
                    return [float(parsed_data[0]), float(parsed_data[1])]

            except json.JSONDecodeError:
                # If it's not valid JSON, return empty list
                return []

        # Otherwise return empty list
        return []
