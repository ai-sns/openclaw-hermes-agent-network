from sqlalchemy.orm import Session
from db.models.aisns import AISnsCfg
from runtime.apps.sns.map_task_manager import MapTaskManager
from runtime.apps.sns.js_task_manager import JsTaskManager
from runtime.apps.sns.xmpp_client import XMPPClientManager
from runtime.modules.agent.agent_manager import agent_manager
from runtime.shared.websocket_manager import manager as websocket_manager

# *********
import os
import math
# Mainly used for sending attachments
import asyncio
import zipfile
import shutil
import time
import uuid

import logging

import re

log = logging.getLogger(__name__)
from db.DBFactory import (query_AgentCfg, add_AIChatMessages, get_prompt_by_title, query_function_mng,
                          add_function_mng, get_key_value,
                          update_map_trade, add_map_trade, query_single_map_trade,
                          update_AISnsCfg_by_user_id, update_AISnsCfg_map, query_AISnsCfg_map, add_mcp_mng, query_mcp_mng,
                          delete_map_preset_msg, query_map_preset_msg_all, add_map_preset_msg, query_AISnsCfg_map_setting)
from db.DBFactory import query_SystemCfg, upsert_prompt_by_title_with_tags

from runtime.i18n import lt
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
from runtime.apps.sns.memory import MemoryManager, MemoryType, MemoryConfig

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
    LIFE_DECLINE_INTERVAL = 50    # Decline life every N rounds
    ENERGY_DECLINE_INTERVAL = 10   # Decline energy every N rounds

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
        self.config = self.db.query(AISnsCfg).filter(
            AISnsCfg.is_delete == False
        ).first()

        # Initialize aisns_cfg from database - get first record from aisns_cfg table
        self.aisns_cfg = self.config

        self.aisns_cfg_record = AISnsCfgManager()
        self.aisns_cfg_record.connect(self.handle_aisns_cfg_property_updated)
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

        # In-memory rebirth counter (not persisted to DB)
        self._rebirth_count = 0

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
        self.max_rounds_per_person = 10  # Max rounds per person
        self.max_place_arrived = 3  # Max places to arrive
        self.min_place_move_score = 80  # Min score to move to a place
        self.place_arrived_count = {}
        self.wait_for_trade_download_flag = False
        self.wait_for_trade_download_trade_id = ""
        self.command_list = []
        self.current_command_index = -1
        self.updown_message_index = -1
        self.life_decline_counter = 0
        self.energy_decline_counter = 0
        self.process_activity_counter = 0
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

        # Initialize memory manager
        agent_id = "default"
        try:
            agent_id = (getattr(self.aisns_cfg, 'account', None) or 'default').strip() or 'default'
        except Exception:
            pass
        self.memory_manager = MemoryManager(agent_id=agent_id)
        self.memory_enabled = True
        self._memory_session_id = None
        self.memory_embedding_enabled = False

        self.active_conversation = None
        self.conversation_inbox = {}
        self.conversation_timeout_seconds = 300
        self._conversation_last_activity_ts = 0.0
        self._conversation_timeout_task = None

        self.contact_cooldown_seconds = 300
        self.contact_recent_limit = 3
        self._contact_last_time = {}
        self._recent_contacts = {
            "sell": [],
            "communication": [],
        }
        self._pending_talk_objective = ""
        self._pick_person_retry_count = {
            "sell": 0,
            "buy": 0,
            "communication": 0,
        }

        self._human_command_inflight = False

        self.process_info_compact_every_n = 50
        self.process_info_plan_summary_every_n = 5
        self.tool_check_every_n = 0
        self.tool_check_before_review_enabled = False
        self.agent_card_before_review_enabled = False

        try:
            cfg = query_SystemCfg(is_delete=False)
            if cfg is not None:
                v = getattr(cfg, "contact_cooldown_seconds", None)
                if v is not None:
                    self.contact_cooldown_seconds = int(v)
                v = getattr(cfg, "contact_recent_limit", None)
                if v is not None:
                    self.contact_recent_limit = int(v)

                v = getattr(cfg, "process_info_compact_every_n", None)
                if v is not None:
                    self.process_info_compact_every_n = int(v)
                v = getattr(cfg, "process_info_plan_summary_every_n", None)
                if v is not None:
                    self.process_info_plan_summary_every_n = int(v)

                v = getattr(cfg, "tool_check_every_n", None)
                if v is not None:
                    self.tool_check_every_n = int(v)
                v = getattr(cfg, "tool_check_before_review_enabled", None)
                if v is not None:
                    self.tool_check_before_review_enabled = bool(int(v)) if isinstance(v, (int, float, str)) else bool(v)
                v = getattr(cfg, "agent_card_before_review_enabled", None)
                if v is not None:
                    self.agent_card_before_review_enabled = bool(int(v)) if isinstance(v, (int, float, str)) else bool(v)

                v = getattr(cfg, "memory_enabled", None)
                if v is not None:
                    self.memory_enabled = bool(int(v)) if isinstance(v, (int, float, str)) else bool(v)
                    MemoryConfig.ENABLED = self.memory_enabled

                v = getattr(cfg, "memory_embedding_enabled", None)
                if v is not None:
                    self.memory_embedding_enabled = bool(int(v)) if isinstance(v, (int, float, str)) else bool(v)
                    MemoryConfig.EMBEDDING_ENABLED = bool(self.memory_embedding_enabled) and bool(MemoryConfig.ENABLED)
        except Exception:
            pass

        try:
            MemoryConfig.ENABLED = bool(self.memory_enabled)
            MemoryConfig.EMBEDDING_ENABLED = bool(getattr(self, "memory_embedding_enabled", False)) and bool(MemoryConfig.ENABLED)
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

                try:
                    self._memory_session_id = str(uuid.uuid4())
                    if MemoryConfig.ENABLED:
                        self.memory_manager.start_session(
                            self._memory_session_id,
                            metadata={
                                "engine": "AISocialEngine",
                                "current_place": getattr(self, "current_place", None),
                                "map_mode": getattr(self, "map_mode", None),
                            },
                        )
                except Exception as _mem_err:
                    logger.warning("Memory session start failed: %s", _mem_err)

                self.taskmng.reviewing_task = True
                self.process_list = []
                self.taskmng.current_process = None
                self.taskmng.add_process(current_place=self.current_place, current_position=self.aisns_cfg_record.current_position)

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
                # Preload recent memories into cache on engine start
                try:
                    if MemoryConfig.ENABLED:
                        self.memory_manager.preload()
                except Exception as _mem_err:
                    logger.warning("Memory preload failed: %s", _mem_err)

                # Seed default SNS prompts if they do not exist yet
                try:
                    self._ensure_sns_prompts()
                except Exception as _prompt_err:
                    logger.warning("SNS prompt seeding failed: %s", _prompt_err)

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

    # ------------------------------------------------------------------
    # Prompt seeding – ensure default SNS prompts exist in the DB
    # ------------------------------------------------------------------
    _SNS_PROMPT_SEEDS = {
        "__tool_check_before_activity__": (
            "You are an AI agent playing a virtual social life game on Google Maps.\n"
            "You are about to decide your next action in the game.\n"
            "Before proceeding, review the current situation below and determine "
            "if any of your available tools could help you make a better decision.\n\n"
            "If you find a useful tool, call it now and return the result.\n"
            "If no tool is needed, simply reply with the single phrase: NO_TOOL_NEEDED\n\n"
            "Keep your response concise. Do NOT plan or choose the next game action "
            "— just focus on whether a tool call would provide useful information right now."
        ),
        "__tool_check_before_review__": (
            "You are an AI agent playing a virtual social life game on Google Maps.\n"
            "You are currently in a conversation with another player.\n"
            "Before reviewing this conversation, check if any of your available tools "
            "could provide useful context (e.g., price lookup, information search, "
            "knowledge retrieval).\n\n"
            "If you find a useful tool, call it now and return the result.\n"
            "If no tool is needed, simply reply with the single phrase: NO_TOOL_NEEDED\n\n"
            "Keep your response concise. Do NOT evaluate or continue the conversation "
            "— just focus on whether a tool call would be helpful."
        ),
        "__plan_summary_output_requirements__": (
            "Output requirements:\n"
            "- Provide updated goals only.\n"
            "- Include BOTH sections with these exact labels:\n"
            "  Long-Term Goals:\n"
            "  Short-Term Goals:\n"
            "- Do NOT include any other sections such as Changes Made/Reasoning/Next Recommended Actions."
        ),
        "__pick_people_strict_retry__": (
            "Your previous output was invalid. Output ONLY one JSON object (no markdown, no extra text) "
            "with EXACT keys: nation_id, account, nick_name, message. All values must be non-empty strings. "
            "Missing/invalid keys: __missing_keys__. Previous raw output: __raw_result__"
        ),
        "__remote_agent_tool_check_activity__": (
            "--- Instructions for Remote Agent ---\n"
            "Based on the context above, use any tools or capabilities you have "
            "to gather information that would help decide the next action.\n"
            "Return only the result. If no tool call is needed, respond with NO_TOOL_NEEDED."
        ),
        "__remote_agent_tool_check_review__": (
            "--- Instructions for Remote Agent ---\n"
            "Review the conversation above. If you have tools that can enrich "
            "your analysis (e.g., lookup, search, query), use them and return the result.\n"
            "If no tool call is needed, respond with NO_TOOL_NEEDED."
        ),
        "__ask_agent_use_service_question__": (
            "The current objective is: __objective__. Based on the task requirements, "
            "select the appropriate services. If no suitable service is available, return an empty list."
        ),
        "__review_conversation_question__": (
            "Please evaluate strictly according to the requirements and output strictly in the required format.\n"
            "## Chat history \n__messages_history__"
        ),
        "__review_conversation_retry_question__": (
            "Please output a single JSON object only, with no explanations or extra text. \n"
            "## Conversation history \n__talk_history__"
        ),
        "__memory_recall_header__": (
            "## Memory Recall\n"
            "The following memories from your past experience may be relevant:\n"
            "\n"
            "__memory_entries__\n"
            "Use these memories to inform your decision, but prioritize current context."
        ),
    }

    def _ensure_sns_prompts(self):
        """Seed default SNS prompts into the DB if they do not already exist."""
        for title, content in self._SNS_PROMPT_SEEDS.items():
            try:
                existing = get_prompt_by_title(title)
                if existing is None:
                    upsert_prompt_by_title_with_tags(title, content, tags="SNS")
                    logger.info("Seeded SNS prompt: %s", title)
            except Exception as e:
                logger.warning("Failed to seed SNS prompt %s: %s", title, e)

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

            # Memory capture: save a reflection summary of this engine run
            try:
                mm = getattr(self, "memory_manager", None)
                info_list = getattr(self.taskmng, "process_info_list", []) if hasattr(self, "taskmng") else []
                if mm and info_list:
                    recent_items = info_list[-10:]
                    run_summary = "; ".join(str(item)[:80] for item in recent_items)
                    mm.capture(
                        MemoryType.REFLECTION,
                        key="Engine stop summary",
                        content=f"Engine stopped. Recent activity: {run_summary[:400]}",
                        metadata={"process_count": len(info_list)},
                        importance=55,
                    )
            except Exception as _mem_err:
                logger.warning("Memory capture failed on engine stop: %s", _mem_err)

            try:
                if MemoryConfig.ENABLED and getattr(self, "_memory_session_id", None):
                    info_list = getattr(self.taskmng, "process_info_list", []) if hasattr(self, "taskmng") else []
                    recent_items = info_list[-10:] if info_list else []
                    session_summary = "; ".join(str(item)[:120] for item in recent_items)
                    self.memory_manager.end_session(
                        summary=f"Engine stopped. Recent activity: {session_summary[:800]}",
                        metadata={"process_count": len(info_list or [])},
                    )
            except Exception as _mem_err:
                logger.warning("Memory session end failed: %s", _mem_err)
            finally:
                self._memory_session_id = None

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
                if hasattr(self, 'life_decline_counter'):
                    self.life_decline_counter = 0
                if hasattr(self, 'energy_decline_counter'):
                    self.energy_decline_counter = 0
                if hasattr(self, 'process_activity_counter'):
                    self.process_activity_counter = 0

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
                if hasattr(self, 'life_decline_counter'):
                    self.life_decline_counter = 0
                if hasattr(self, 'energy_decline_counter'):
                    self.energy_decline_counter = 0
                if hasattr(self, 'process_activity_counter'):
                    self.process_activity_counter = 0
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
        if self.life_decline_counter >= self.LIFE_DECLINE_INTERVAL:
            self.decline_life()
            self.life_decline_counter = 0

        if self.energy_decline_counter >= self.ENERGY_DECLINE_INTERVAL:
            self.decline_energy()
            self.energy_decline_counter = 0

        money = float(self.aisns_cfg_record.money or 0)
        life_point = int(self.aisns_cfg_record.life_point or 0)
        energy_point = int(self.aisns_cfg_record.energy_point or 0)
        move_point = int(self.aisns_cfg_record.move_point or 0)

        current_status = f"""
* Money: ${money:.2f}
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
        people_list = []
        try:
            people_list = self.get_people_list() or []
        except Exception:
            people_list = []
        prompt = prompt.replace(f"__people_list__", json.dumps(people_list, indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__place_list__", json.dumps(self.get_place_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__question_to_llm__", question_to_llm)

        # Memory recall: inject relevant memories into the prompt
        try:
            if MemoryConfig.ENABLED:
                memory_section = self.memory_manager.get_memory_prompt_section(
                    query=question_to_llm,
                    max_results=5,
                    max_chars=1500,
                )
                if memory_section:
                    prompt = prompt.strip() + "\n\n" + memory_section
        except Exception as _mem_err:
            logger.warning("Memory recall failed for compose_full_ask_content: %s", _mem_err)

        return prompt.strip()

    def parse_agent_instruction_for_process_activity(self, instruction):
        self.handle_parse_agent_instruction_for_process_activity(instruction)

    def _update_iq_point_from_counters(self):
        if self._instruction_total_count > 0:
            self.aisns_cfg_record.iq_point = round(
                (1 - self._instruction_invalid_count / self._instruction_total_count) * 100
            )
        else:
            self.aisns_cfg_record.iq_point = 100

    def _iter_json_objects_from_text(self, text: str):
        if not isinstance(text, str) or not text:
            return []

        objects = []
        try:
            for m in re.finditer(r"\{.*?\}", text, flags=re.DOTALL):
                chunk = m.group(0)
                try:
                    obj = json.loads(chunk)
                except Exception:
                    continue
                objects.append(obj)
        except Exception:
            objects = []

        if objects:
            return objects

        objects = []
        start = None
        depth = 0
        in_string = False
        escape = False
        for idx, ch in enumerate(text):
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
                continue

            if ch == '{':
                if depth == 0:
                    start = idx
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        chunk = text[start:idx + 1]
                        start = None
                        try:
                            obj = json.loads(chunk)
                        except Exception:
                            continue
                        objects.append(obj)

        return objects

    def _extract_place_position_from_action_str(self, action_str: str):
        for obj in (self._iter_json_objects_from_text(action_str) or []):
            if not isinstance(obj, dict):
                continue

            place = obj.get("place")
            position = obj.get("position")
            if place is None or position is None:
                params = obj.get("parameters")
                if isinstance(params, dict):
                    place = params.get("place")
                    position = params.get("position")

            if not isinstance(place, str) or not place.strip():
                continue
            if not isinstance(position, list) or len(position) < 2:
                continue

            try:
                lng = float(position[0])
                lat = float(position[1])
            except Exception:
                continue

            if not (math.isfinite(lng) and math.isfinite(lat)):
                continue
            return place.strip(), [lng, lat]

        return None, None

    def handle_parse_agent_instruction_for_process_activity(self, instruction):
        print("llm return instruction:", instruction)
        instruction = instruction.strip()
        self.current_task_list = self.get_current_task_list(instruction)
        action_str = self.get_next_action(instruction)

        action_str_clean = (action_str or "").strip()
        if not action_str_clean or all(ch in {".", ""} for ch in action_str_clean):
            self._instruction_total_count += 1
            self._instruction_invalid_count += 1
            self._update_iq_point_from_counters()
            self.taskmng_js.show_information(
                lt(
                    "<b>LLM returned invalid structure.</b>",
                    "<b>LLM returned invalid structure.</b>",
                )
            )
        else:
            self.taskmng_js.show_information(lt(f"<b>LLM recommended next action:</b><br>{action_str_clean}.", f"<b>LLM-recommended next action:</b><br>{action_str_clean}."))

        self.current_action = action_str_clean

        # Increment exp_point by 1 on each call
        current_exp = int(self.aisns_cfg_record.exp_point or 0)
        self.aisns_cfg_record.exp_point = current_exp + 1

        # Increment in-memory instruction total count for IQ tracking
        self._instruction_total_count += 1


        self.life_decline_counter += 1
        self.energy_decline_counter += 1

        if self.move_by_route_flag:
            self.write_on_going_process_to_pane(f"{action_str}(Changed to 'move by route' due to the movement setting.")
        else:
            self.write_on_going_process_to_pane(action_str)
        # self.loading_tab.stop_loading()

        if "1_EXPLORE_NEARBY" in action_str:

            if self.move_by_route_flag:
                action_result = self.move_by_route()
            elif self.target_position:
                action_result = self.move_ahead(self.aisns_cfg_record.current_position, self.target_position, self.target_place)
            else:
                action_result = self.go_around()

        elif "2_WALK_TO" in action_str:

            if self.move_by_route_flag:
                action_result = self.move_by_route()
            else:
                place, target_position = self._extract_place_position_from_action_str(action_str)
                if not place or not target_position:
                    self._instruction_invalid_count += 1
                    self._update_iq_point_from_counters()
                    msg = "Failed to parse WALK_TO payload from LLM output. Expected JSON with place and position."
                    try:
                        self.show_alert_on_map(msg, is_error=True)
                    except Exception:
                        pass
                    action_result = msg
                else:
                    self.target_position = target_position
                    self.target_place = place
                    action_result = self.move_ahead(self.aisns_cfg_record.current_position, target_position, place)

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
                place, target_position = self._extract_place_position_from_action_str(action_str)
                if not place or not target_position:
                    self._instruction_invalid_count += 1
                    self._update_iq_point_from_counters()
                    msg = "Failed to parse CALL_TAXI payload from LLM output. Expected JSON with place and position."
                    try:
                        self.show_alert_on_map(msg, is_error=True)
                    except Exception:
                        pass
                    action_result = msg
                else:
                    action_result = self.set_taxi_order(self.aisns_cfg_record.current_position, target_position, place)

        elif "10_REMOTE_MEDICAL" in action_str:
            action_result = self.call_a_doctor()
        else:
            action_result = f"'{action_str}' is not in the list of valid actions."
            # Increment in-memory instruction invalid count for IQ tracking
            self._instruction_invalid_count += 1

        self._update_iq_point_from_counters()

        self.action_result = action_result
        invalid_action_msg = f"'{action_str}' is not in the list of valid actions."
        if action_result == invalid_action_msg:
            if (action_str or "").strip():
                self.taskmng_js.show_information(lt(invalid_action_msg, invalid_action_msg))
        else:
            skip_show_information_for_action_result = (
                "8_FOOD_DELIVERY" in (action_str or "")
                or "10_REMOTE_MEDICAL" in (action_str or "")
            )
            self.taskmng.add_process_info_to_list(f"system:{action_result}")
            if not skip_show_information_for_action_result:
                self.taskmng_js.show_information(f"<b>{action_result}</b>")

        self.write_task_process_to_pane()
        self.show_alert_on_map(action_result)

        # Memory capture: record completed action as episode memory
        try:
            pos = getattr(self.aisns_cfg_record, 'current_position', [])
            self.memory_manager.capture_async(
                MemoryType.EPISODE,
                key=f"Action: {action_str[:80]}",
                content=action_result,
                metadata={
                    "action": action_str[:120],
                    "position": pos if isinstance(pos, list) else [],
                    "money": float(self.aisns_cfg_record.money or 0),
                    "life": int(self.aisns_cfg_record.life_point or 0),
                    "energy": int(self.aisns_cfg_record.energy_point or 0),
                },
            )
        except Exception as _mem_err:
            logger.warning("Memory capture failed after action: %s", _mem_err)

        ask_content = instruction
        try:
            if bool(getattr(self, "_human_command_inflight", False)):
                self._maybe_finish_human_command_if_idle(ask_content=ask_content)
                return
        except Exception:
            pass

        asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=ask_content))

    def get_next_action(self, instruction):
        delimiter = "### Next Action"
        action_text = ""
        if delimiter in instruction:
            parts = instruction.split(delimiter, 1)
            action_text = parts[1].strip() if len(parts) > 1 else ""
        else:
            delimiter = "Next Action"
            if delimiter in instruction:
                parts = instruction.split(delimiter, 1)
                action_text = parts[1].strip() if len(parts) > 1 else ""
            else:
                return ""

        if not action_text:
            return ""

        candidates = [
            "1_EXPLORE_NEARBY",
            "2_WALK_TO",
            "3_COMMUNICATE",
            "4_PROMOTE",
            "5_PURCHASE",
            "6_WEB_SERVICE",
            "7_NAVIGATION",
            "8_FOOD_DELIVERY",
            "9_CALL_TAXI",
            "10_REMOTE_MEDICAL",
        ]

        pattern = r"(?:【\s*)?(" + "|".join(re.escape(c) for c in candidates) + r")(?:\s*】)?"
        found_actions = re.findall(pattern, action_text)
        if len(set(found_actions)) >= 2:
            return ""
        return action_text

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
                if self.is_busy_for_human_command():
                    try:
                        self.taskmng_js.show_information(
                            lt(
                                "<b>Previous command is still running. Please wait.</b>",
                                "<b>Previous command is still running. Please wait.</b>",
                            )
                        )
                    except Exception:
                        pass
                    return
                self.taskmng_js.show_information(lt(f"<b>Human:</b><br>{instruction}", f"<b>Human:</b><br>{instruction}"))
                self.write_on_going_process_to_pane(lt("Human take control...", "Human is in control..."))
                self.handle_human_instruction(instruction)
            else:
                self.sendMessage(instruction, True)

    def is_busy_for_human_command(self) -> bool:
        try:
            if bool(getattr(self, "_human_command_inflight", False)):
                return True
        except Exception:
            pass

        return False

    def is_idle_for_auto_activity(self) -> bool:
        if not self._is_idle_except_human_command_inflight():
            return False
        try:
            return not bool(getattr(self, "_human_command_inflight", False))
        except Exception:
            return False

    def _is_idle_except_human_command_inflight(self) -> bool:
        try:
            if bool(getattr(self, "agent_replying_flag", False)):
                return False
        except Exception:
            pass

        try:
            if bool(getattr(self, "command_status", "") or ""):
                return False
        except Exception:
            pass

        try:
            if getattr(self, "active_conversation", None):
                return False
        except Exception:
            pass

        return True

    def _maybe_resume_process_activity_if_idle(self, ask_content: str = "") -> None:
        try:
            if bool(getattr(self, "human_take_over", False)):
                return
        except Exception:
            return

        try:
            if not bool(getattr(self, "started_flag", False)):
                return
        except Exception:
            return

        if not self.is_idle_for_auto_activity():
            return

        try:
            asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=ask_content or ""))
        except Exception:
            pass

    def _maybe_finish_human_command_if_idle(self, *, ask_content: str = "") -> None:
        if not self._is_idle_except_human_command_inflight():
            return

        try:
            self._human_command_inflight = False
        except Exception:
            pass

        self._maybe_resume_process_activity_if_idle(ask_content=ask_content)

    def _terminate_active_conversation_for_priority_action(self) -> None:
        active = None
        try:
            active = getattr(self, "active_conversation", None)
        except Exception:
            active = None

        if not active:
            return

        try:
            acct = (active.get("account") or "").strip() if isinstance(active, dict) else ""
        except Exception:
            acct = ""

        try:
            if acct:
                logger.info("End the Conversation.Send TERMINATE by frontend.")
                # self.sendMessage("TERMINATE", False, acct, (active.get("nick_name") if isinstance(active, dict) else None), back_ground=True)
        except Exception:
            pass

        try:
            self.end_active_conversation(
                reason="priority_action",
                message="",
                resume_activity=False,
            )
        except TypeError:
            try:
                self.end_active_conversation(
                    reason="priority_action",
                    message="",
                    resume_activity=False,
                    resume_ask_content="",
                )
            except Exception:
                pass
        except Exception:
            pass

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
        if self.life_decline_counter >= self.LIFE_DECLINE_INTERVAL:
            logger.info(
                "Life decline triggered (human control). counter=%s interval=%s",
                self.life_decline_counter,
                self.LIFE_DECLINE_INTERVAL,
            )
            self.decline_life()
            self.life_decline_counter = 0

        if self.energy_decline_counter >= self.ENERGY_DECLINE_INTERVAL:
            logger.info(
                "Energy decline triggered (human control). counter=%s interval=%s",
                self.energy_decline_counter,
                self.ENERGY_DECLINE_INTERVAL,
            )
            self.decline_energy()
            self.energy_decline_counter = 0

        prompt = get_prompt_by_title("__human_instruction_to_process_activity_content__")
        prompt = prompt.replace(f"__human_instruction__", question_to_llm)
        prompt = prompt.replace(f"__service_list__", json.dumps(self.get_service_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__people_list__", json.dumps(self.get_people_list(), indent=4, ensure_ascii=False))
        prompt = prompt.replace(f"__place_list__", json.dumps(self.get_place_list(), indent=4, ensure_ascii=False))

        # Memory recall: inject relevant memories for human instruction context
        try:
            if MemoryConfig.ENABLED:
                memory_section = self.memory_manager.get_memory_prompt_section(
                    query=question_to_llm,
                    max_results=5,
                    max_chars=1500,
                )
                if memory_section:
                    prompt = prompt.strip() + "\n\n" + memory_section
        except Exception as _mem_err:
            logger.warning("Memory recall failed for compose_full_ask_content_human: %s", _mem_err)

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

                # Memory capture: save human note to local memory system
                try:
                    self.memory_manager.capture_async(
                        MemoryType.HUMAN_NOTE,
                        key=f"Human note: {memory_content[:60]}",
                        content=memory_content,
                        importance=80,
                    )
                except Exception as _mem_err:
                    logger.warning("Memory capture failed for human note: %s", _mem_err)

                return

            try:
                self._human_command_inflight = True
            except Exception:
                pass

            try:
                self._terminate_active_conversation_for_priority_action()
            except Exception:
                pass

            # Merge human instructions into full_ask_content
            self.human_instruction = human_instruction
            asyncio.create_task(self.taskmng.process_task(action="process_human_instruction", ask_content=human_instruction, human_send_flag=True))

    def _mark_human_command_complete(self, *, ask_content: str = "") -> None:
        try:
            self._human_command_inflight = False
        except Exception:
            pass

    def check_and_handle_rebirth(self):
        """
        Check if rebirth should trigger.
        Condition: life <= 0 OR energy <= 0 OR money <= 0.
        On rebirth: increment counter, reset life=100, energy=100, move=100, money=1000.
        Uses re-entrancy guard to prevent cascading callback increments.
        """
        if getattr(self, '_rebirth_in_progress', False):
            return False

        life = float(self.aisns_cfg_record.life_point or 0)
        energy = float(self.aisns_cfg_record.energy_point or 0)
        money = float(self.aisns_cfg_record.money or 0)

        if life <= 0 or energy <= 0 or money <= 0:
            self._rebirth_in_progress = True
            try:
                self._rebirth_count += 1
                life_before = life
                energy_before = energy
                money_before = money
                self.aisns_cfg_record.life_point = 100
                self.aisns_cfg_record.energy_point = 100
                self.aisns_cfg_record.move_point = 100
                self.aisns_cfg_record.money = 1000
                logger.info(f"Rebirth triggered (#{self._rebirth_count}). Stats reset: life=100, energy=100, move=100, money=1000")

                try:
                    msg = (
                        f"Rebirth triggered (#{self._rebirth_count}). "
                        f"❤️Life: {life_before:.0f}% -> {float(self.aisns_cfg_record.life_point or 0):.0f}%. "
                        f"⚡Energy: {energy_before:.0f}% -> {float(self.aisns_cfg_record.energy_point or 0):.0f}%. "
                        f"💰Money: ${money_before:.2f} -> ${float(self.aisns_cfg_record.money or 0):.2f}."
                    )
                    try:
                        if hasattr(self, "show_alert_on_map"):
                            self.show_alert_on_map(msg, is_error=True)
                    except Exception:
                        pass

                    try:
                        if hasattr(self, "taskmng_js"):
                            self.taskmng_js.show_information(f"<b>{msg}</b>")
                    except Exception:
                        pass
                except Exception:
                    pass

                # Memory capture: record rebirth event
                try:
                    self.memory_manager.capture_async(
                        MemoryType.EPISODE,
                        key=f"Rebirth #{self._rebirth_count}",
                        content=f"Rebirth triggered (#{self._rebirth_count}). Cause: life={life:.0f}, energy={energy:.0f}, money={money:.0f}. Stats reset to defaults.",
                        metadata={
                            "rebirth_count": self._rebirth_count,
                            "pre_life": life,
                            "pre_energy": energy,
                            "pre_money": money,
                        },
                        importance=90,
                    )
                except Exception as _mem_err:
                    logger.warning("Memory capture failed for rebirth: %s", _mem_err)
            finally:
                self._rebirth_in_progress = False
            return True
        return False

    def handle_aisns_cfg_property_updated(self, property_name):
        """
        Handle AISnsCfg property updates.
        When specific properties change, update related UI elements.

        Args:
            property_name (str): Updated property name
        """
        # Check rebirth for money changes via callback.
        # For life_point/energy_point, rebirth is checked explicitly at end of
        # decline_energy()/decline_life() to avoid move_point overwrite bug.
        if property_name == 'money':
            self.check_and_handle_rebirth()

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

        if property_name == 'current_position':
            try:
                self._invalidate_position_caches()
            except Exception:
                pass
            try:
                self._schedule_resource_refresh_after_position_change()
            except Exception:
                pass

    def _invalidate_position_caches(self) -> None:
        try:
            for k in (
                "_cached_service_list_pos_key",
                "_cached_service_list_value",
                "_cached_people_list_pos_key",
                "_cached_people_list_value",
                "_cached_place_list_pos_key",
                "_cached_place_list_value",
            ):
                if hasattr(self, k):
                    try:
                        setattr(self, k, None)
                    except Exception:
                        pass
        except Exception:
            pass

    def _schedule_resource_refresh_after_position_change(self, *, debounce_ms: int = 500) -> None:
        try:
            if getattr(self, "_resource_refresh_timer", None):
                return
        except Exception:
            pass

        async def _do_refresh():
            try:
                await asyncio.sleep(max(0.05, float(debounce_ms) / 1000.0))
            except Exception:
                pass
            try:
                self.update_resource_display()
            except Exception as e:
                logger.warning("Failed to refresh Resource tab after position change: %s", e)
            finally:
                try:
                    self._resource_refresh_timer = None
                except Exception:
                    pass

        try:
            self._resource_refresh_timer = asyncio.create_task(_do_refresh())
        except Exception:
            self._resource_refresh_timer = None


class AISnsCfgManager:
    """
    Class for managing AISnsCfg DB records.
    Supports reading the latest values via attribute access and updating DB records via assignment.
    """

    def __init__(self, user_id=None):
        """
        Initialize AISnsCfgManager.

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
            self._record = query_AISnsCfg_map_setting(user_id=self._user_id)
        else:
            self._record = query_AISnsCfg_map()

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
                update_AISnsCfg_by_user_id(self._user_id, **{name: value})
            else:
                update_AISnsCfg_map(**{name: value})

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
