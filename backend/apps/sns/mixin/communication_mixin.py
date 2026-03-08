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

from backend.shared.utils import robust_json_loads

logger = logging.getLogger(__name__)


class CommunicationMixin:
    def _now_ts(self) -> float:
        return float(time.time())

    def _get_active_account(self) -> str:
        active = getattr(self, "active_conversation", None) or {}
        return (active.get("account") or "").strip()

    def _get_active_nation_id(self) -> str:
        active = getattr(self, "active_conversation", None) or {}
        return (active.get("nation_id") or "").strip()

    def _touch_conversation_activity(self, account: str) -> None:
        if not account:
            return
        active_account = self._get_active_account()
        if active_account and active_account != account:
            return
        self._conversation_last_activity_ts = self._now_ts()
        self._ensure_conversation_timeout_task()

    def _ensure_conversation_timeout_task(self) -> None:
        try:
            task = getattr(self, "_conversation_timeout_task", None)
            if isinstance(task, asyncio.Task) and not task.done():
                return
            self._conversation_timeout_task = asyncio.create_task(self._conversation_timeout_guard())
        except Exception as e:
            logger.error(f"Failed to start conversation timeout guard: {e}")

    async def _conversation_timeout_guard(self) -> None:
        while True:
            try:
                active_account = self._get_active_account()
                if not active_account:
                    return
                last_ts = float(getattr(self, "_conversation_last_activity_ts", 0.0) or 0.0)
                timeout_s = int(getattr(self, "conversation_timeout_seconds", 60) or 60)
                if last_ts > 0 and (self._now_ts() - last_ts) >= timeout_s:
                    self.end_active_conversation(
                        reason="timeout",
                        message=f"Conversation timed out after {timeout_s}s with {active_account}.",
                        resume_activity=True,
                    )
                    return
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Conversation timeout guard error: {e}", exc_info=True)
                return

    def _format_inbox_message(self, account: str, content: str) -> str:
        preview = (content or "").strip()
        if len(preview) > 160:
            preview = preview[:160] + "..."
        return f"[Inbox] {account}: {preview}"

    def enqueue_inbox_message(self, account: str, content: str) -> None:
        if not account:
            return
        inbox = getattr(self, "conversation_inbox", None)
        if inbox is None or not isinstance(inbox, dict):
            self.conversation_inbox = {}
            inbox = self.conversation_inbox
        inbox.setdefault(account, []).append({"ts": self._now_ts(), "content": content})
        try:
            self.send_msg_to_map(("show_information_chat", self._format_inbox_message(account, content), ""))
        except Exception as e:
            logger.error(f"Failed to notify inbox message: {e}")

    def _get_people_by_account(self, account: str) -> Optional[dict]:
        if not account:
            return None
        try:
            for p in (self.get_people_list() or []):
                if (p.get("account") or "").strip() == account:
                    return p
        except Exception:
            return None
        return None

    def _record_contact(self, talk_type: str, account: str) -> None:
        if not account:
            return
        now_ts = self._now_ts()
        last_time = getattr(self, "_contact_last_time", None)
        if last_time is None or not isinstance(last_time, dict):
            self._contact_last_time = {}
            last_time = self._contact_last_time
        last_time[account] = now_ts

        recent = getattr(self, "_recent_contacts", None)
        if recent is None or not isinstance(recent, dict):
            self._recent_contacts = {"sell": [], "buy": [], "communication": []}
            recent = self._recent_contacts
        bucket = recent.setdefault(talk_type, [])
        bucket[:] = [a for a in bucket if a != account]
        bucket.append(account)
        limit = int(getattr(self, "contact_recent_limit", 3) or 3)
        if limit > 0 and len(bucket) > limit:
            del bucket[:-limit]

    def _is_contact_allowed(self, talk_type: str, account: str) -> bool:
        if not account:
            return False
        cooldown_s = int(getattr(self, "contact_cooldown_seconds", 300) or 300)
        now_ts = self._now_ts()
        last_time = getattr(self, "_contact_last_time", None) or {}
        last_ts = float(last_time.get(account, 0.0) or 0.0)
        if cooldown_s > 0 and last_ts > 0 and (now_ts - last_ts) < cooldown_s:
            return False

        recent = getattr(self, "_recent_contacts", None) or {}
        bucket = recent.get(talk_type, []) if isinstance(recent, dict) else []
        if account in (bucket or []):
            return False
        return True

    def _get_filtered_people_list_for_talk_type(self, talk_type: str) -> List[dict]:
        people = list(self.get_people_list() or [])
        cooldown_s = int(getattr(self, "contact_cooldown_seconds", 300) or 300)
        now_ts = self._now_ts()
        last_time = getattr(self, "_contact_last_time", None) or {}
        recent = getattr(self, "_recent_contacts", None) or {}
        bucket = set(recent.get(talk_type, []) if isinstance(recent, dict) else [])

        filtered = []
        for p in people:
            account = (p.get("account") or "").strip()
            if not account:
                continue
            last_ts = float(last_time.get(account, 0.0) or 0.0)
            if cooldown_s > 0 and last_ts > 0 and (now_ts - last_ts) < cooldown_s:
                continue
            if account in bucket:
                continue
            filtered.append(p)
        return filtered or people

    def start_active_conversation(self, *, talk_type: str, person: dict, objective: str = "") -> None:
        account = (person or {}).get("account")
        account = (account or "").strip()
        nation_id = (person or {}).get("nation_id")
        nation_id = (nation_id or "").strip() or account
        nick_name = (person or {}).get("nick_name")
        nick_name = (nick_name or "").strip() or account

        if not account:
            return

        active_account = self._get_active_account()
        if active_account and active_account != account:
            self.end_active_conversation(
                reason="switched",
                message=f"Conversation switched from {active_account} to {account}.",
                resume_activity=False,
            )

        self.active_conversation = {
            "talk_type": talk_type,
            "account": account,
            "nation_id": nation_id,
            "nick_name": nick_name,
            "objective": (objective or "").strip(),
            "started_at": self._now_ts(),
        }
        self._conversation_last_activity_ts = self._now_ts()
        self._record_contact(talk_type, account)
        self._ensure_conversation_timeout_task()

    def end_active_conversation(
        self,
        *,
        reason: str,
        message: str = "",
        resume_activity: bool,
        resume_ask_content: str = "",
    ) -> None:
        nation_id = ""
        account = ""
        try:
            active = getattr(self, "active_conversation", None) or {}
            account = (active.get("account") or "").strip()
            nation_id = (active.get("nation_id") or "").strip()
        except Exception:
            pass

        try:
            if nation_id:
                self.send_msg_to_map(("stop_talk_to_it", nation_id, ""))
        except Exception as e:
            logger.error(f"Failed to send stop_talk_to_it: {e}")

        try:
            self.show_status_on_map("idle")
        except Exception:
            pass

        self.active_conversation = None
        self._conversation_last_activity_ts = 0.0

        try:
            self.current_talk_people = None
        except Exception:
            pass

        try:
            self.current_talk_history = []
        except Exception:
            pass

        try:
            self.talk_type = ""
        except Exception:
            pass

        if message:
            try:
                self.taskmng.add_process_info_to_list(f"system:{message}")
            except Exception:
                pass

        if resume_activity:
            try:
                asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=resume_ask_content or ""))
            except Exception as e:
                logger.error(f"Failed to resume activity after conversation end: {e}")

    def talk_to_a_people(self, content, nationid, account, user_name):
        title_str = "Choose a person to talk"
        content_str = f"""🟪 *The function is*:

talk_to_a_people

🟩 *The Content is*:

{lt(f"Talk to a people with {user_name} acount:{account},nationid:{nationid},content:{content}", f"Talk to a people with {user_name} acount:{account},nationid:{nationid},content:{content}")}
            """

        self.write_thinking_process_to_pane(title_str, content_str)

        self.start_active_conversation(
            talk_type=(getattr(self, "talk_type", "") or "communication"),
            person={"nation_id": nationid, "account": account, "nick_name": user_name},
            objective=(getattr(self, "_pending_talk_objective", "") or ""),
        )
        self._touch_conversation_activity(account)

        try:
            current_talk_people = self.current_talk_people
            if not isinstance(current_talk_people, dict):
                current_talk_people = {
                    "nation_id": nationid,
                    "account": account,
                    "nick_name": user_name,
                }
                self.current_talk_people = current_talk_people

            round = current_talk_people.get("talk_round", 0) + 1
            self.current_talk_people["talk_round"] = round
        except Exception:
            pass
        command = ("start_talk_to_it", nationid, content)
        self.send_msg_to_map(command)
        self.sendMessage(content, False, account, user_name)

        if account not in self.talk_history:
            self.talk_history[account] = []
        self.talk_history[account].append("Me:" + content)
        self.current_talk_history.append("Me:" + content)

    def communicate_with_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "communication"
        self.ask_agent_start_to_talk_to_a_people_sync(action_str, human_object)

        # self.taskmng.process_task(action="process_activity", ask_content=ask_content)

    def ask_agent_start_to_talk_to_a_people_sync(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = self._get_filtered_people_list_for_talk_type("communication")
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_talk_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_talk_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_talk_to_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    async def ask_agent_start_to_talk_to_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = self._get_filtered_people_list_for_talk_type("communication")
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_talk_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_talk_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_talk_to_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    def handle_ask_agent_start_to_talk_to_a_people_result(self, content):
        result = robust_json_loads(content, default=None)
        if not isinstance(result, dict):
            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))
            return
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]

            if not self._is_contact_allowed("communication", account):
                retry_count = int(getattr(self, "_pick_person_retry_count", {}).get("communication", 0) or 0)
                if retry_count < 2:
                    self._pick_person_retry_count["communication"] = retry_count + 1
                    hint = " Please choose a different person than the recently contacted ones."
                    self.ask_agent_start_to_talk_to_a_people_sync(self._pending_talk_objective + hint, "")
                    return
                self._pick_person_retry_count["communication"] = 0
            else:
                self._pick_person_retry_count["communication"] = 0

            self.current_talk_people = result
            self.start_active_conversation(talk_type="communication", person=result, objective=self._pending_talk_objective)

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "Target person not found."

            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))

    async def ask_agent_to_review_conversation(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation__")
        # role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
        # role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "## 聊天记录 \n" + messages_history
        await   self.ask_agent_and_get_instruction(question, role_prompt)

    def handle_agent_review_conversation_result(self, content):

        self.handle_agent_review_conversation_result_final(content)

    def handle_agent_review_conversation_result_final(self, content):
        content = content.strip()
        result = robust_json_loads(content, default=None)
        if not isinstance(result, dict):
            retry_count = getattr(self, "_review_comm_retry_count", 0)
            if retry_count < 1:
                setattr(self, "_review_comm_retry_count", retry_count + 1)
                talk_history_str = json.dumps(self.current_talk_history, ensure_ascii=False)
                role_prompt = get_prompt_by_title("__review_conversation__")
                question = "请只输出一个JSON对象，不要输出任何解释或额外文字。\n## 聊天记录 \n" + talk_history_str
                asyncio.create_task(self.ask_agent_and_get_instruction(question, role_prompt))
            else:
                setattr(self, "_review_comm_retry_count", 0)
            return
        setattr(self, "_review_comm_retry_count", 0)
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]

        buy_score = result.get("buy_score", False)
        price = result.get("price", 0)

        if buy_score >= 80 and price >= 0:
            self.send_pay(price)
            self.end_active_conversation(
                reason="pay",
                message="Payment initiated.",
                resume_activity=True,
                resume_ask_content="",
            )
            return

        if not continue_chat:
            self.taskmng.add_process_info_to_list(f"After communicating with a friend, got the following: {current_chat_summary}")
            self.write_task_process_to_pane(f"After communicating with a friend, got the following: {current_chat_summary}\n\n")
            self.taskmng.current_situation = f"After communicating with someone, got the following: {current_chat_summary}"
            resume_ask_content = f"- Current objective\n{self.taskmng.current_objective}\n- Current progress\nAfter communicating with someone, got the following: {current_chat_summary}"
            self.end_active_conversation(
                reason="completed",
                message="Conversation completed.",
                resume_activity=True,
                resume_ask_content=resume_ask_content,
            )

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
                    "nick_name": "W Bao",
                    "avatar": "img_woman_hi",
                    "avatar_3d": "smallofficewoman_0_0_0_0_1_0.glb",
                    "profile": "I am a doctor",
                    "sns_url": "x.com"
                }

            if self.taskmng.current_process["rounds_current_person"] < self.max_rounds_per_person:
                self.taskmng.current_process["rounds_current_person"] = self.taskmng.current_process["rounds_current_person"] + 1
                self.talk_to_a_people(message, self.current_talk_people["nation_id"], self.current_talk_people["account"], self.current_talk_people["nick_name"])
            else:
                self.taskmng.add_process_info_to_list(f"After communicating with a friend, got the following: {current_chat_summary}")
                self.taskmng.current_situation = f"After communicating with someone, got the following: {current_chat_summary}"
                resume_ask_content = f"- Current objective\n{self.taskmng.current_objective}\n- Current progress\nAfter communicating with someone, got the following: {current_chat_summary}"
                self.end_active_conversation(
                    reason="max_rounds",
                    message="Conversation reached max rounds.",
                    resume_activity=True,
                    resume_ask_content=resume_ask_content,
                )
