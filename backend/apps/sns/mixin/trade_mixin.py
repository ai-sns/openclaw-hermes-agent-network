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

from backend.shared.utils import robust_json_loads, safe_json_dumps

logger = logging.getLogger(__name__)

class TradeMixin:

    def _parse_trade_payment(self, price_str: str):
        trade_id = ""
        trade_price = "0"

        if price_str and "__AISNS_INT_SEPARATOR__" in price_str:
            price_str = price_str.strip()
            parts = price_str.split("__AISNS_INT_SEPARATOR__", 1)
            trade_id = (parts[0] or "").strip()
            trade_price = (parts[1] or "0").strip()
        else:
            trade_price = (price_str or "0").strip()

        return trade_id, trade_price

    def get_guidance(self):
        fee = 10
        people_list_str = ""
        place_list_str = ""

        try:
            base = (self._get_ai_sns_server_base() or "").rstrip("/")
            if base:
                url = f"{base}/api/get_guidance_lists/"


                params = {
                    "lng": self.aichatcfg_record.current_position[0],
                    "lat": self.aichatcfg_record.current_position[1]
                }

                data = self.http_request(url, params)
                if isinstance(data, dict):
                    people_list_str = (data.get("people_list_str") or "").strip()
                    place_list_str = (data.get("place_list_str") or "").strip()
        except Exception as e:
            logger.error(f"Failed to fetch guidance lists from remote server: {e}", exc_info=True)

        if not people_list_str:
            people_list_str = "- (no people found)\n"
        else:
            people_list_str = people_list_str + ("\n" if not people_list_str.endswith("\n") else "")

        if not place_list_str:
            place_list_str = "- (no places found)\n"
        else:
            place_list_str = place_list_str + ("\n" if not place_list_str.endswith("\n") else "")

        result = f"""
        You paid {fee} and received the following information:
        ### People List:
        {people_list_str}
        ### Place List:
        {place_list_str}
        """""

        self.aichatcfg_record.money = float(self.aichatcfg_record.money or 0) - fee
        return result

    def set_food_order(self):
        fee = 30
        provider = None
        try:
            provider = self.get_nearest_people_by_profession("Restaurateur")
        except Exception as e:
            logger.error(f"Failed to get nearest Restaurateur: {e}", exc_info=True)

        self.aichatcfg_record.energy_point = self.aichatcfg_record.energy_point + 25
        self.aichatcfg_record.move_point = round(
            100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100),
            1,
        )

        if provider:
            self.send_pay(fee, to_account=provider.get("account"), to_nation_id=provider.get("nation_id"), to_nick_name=provider.get("nick_name"))
        else:
            self.aichatcfg_record.money = self.aichatcfg_record.money - fee

        result = f"You paid {fee} for food. Your energy is now {self.aichatcfg_record.energy_point}%, and your move power is {self.aichatcfg_record.move_point}%"
        return result

    def set_taxi_order(self, current_position, target_position, target_place):
        point1 = (current_position[1], current_position[0])  # Convert to (lat, lon)
        point2 = (target_position[1], target_position[0])  # Convert to (lat, lon)

        # Compute distance using geopy
        dist = distance(point1, point2).kilometers
        fee = dist * 2.5


        self.aichatcfg_record.money = self.aichatcfg_record.money - fee

        self.aichatcfg_record.last_position = current_position
        self.aichatcfg_record.current_position = target_position
        new_pos = self.aichatcfg_record.current_position
        command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
        self.send_msg_to_map(command)

        result = f"You paid {fee:.2f} for the taxi. You have arrived at {target_place}, coordinates: {target_position}"
        return result

    def call_a_doctor(self):
        fee = 210
        provider = None
        try:
            provider = self.get_nearest_people_by_profession("Doctor")
        except Exception as e:
            logger.error(f"Failed to get nearest Doctor: {e}", exc_info=True)

        self.aichatcfg_record.life_point = self.aichatcfg_record.life_point + 25
        self.aichatcfg_record.move_point = round(
            100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100),
            1,
        )

        if provider:
            self.send_pay(fee, to_account=provider.get("account"), to_nation_id=provider.get("nation_id"), to_nick_name=provider.get("nick_name"))
        else:
            self.aichatcfg_record.money = self.aichatcfg_record.money - fee

        result = f"You paid {fee} for remote medical service. Your life is now {self.aichatcfg_record.life_point}%, and your move power is {self.aichatcfg_record.move_point}%"
        return result

    def sell_to_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "sell"
        # Reset talk state so talk_round starts fresh for the new conversation
        self.current_talk_people = None
        self._pending_talk_objective = f"{human_object}{action_str}".strip()
        self.ask_agent_start_to_sell_to_a_people_sync(action_str, human_object)

    def buy_from_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "buy"
        # Reset talk state so talk_round starts fresh for the new conversation
        self.current_talk_people = None
        self._pending_talk_objective = f"{human_object}{action_str}".strip()
        self.ask_agent_start_to_buy_from_a_people_sync(action_str, human_object)

    def ask_agent_start_to_sell_to_a_people_sync(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = self._get_filtered_people_list_for_talk_type("sell")
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_sell_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_sell_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_sell_to_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    def ask_agent_start_to_buy_from_a_people_sync(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = self._get_filtered_people_list_for_talk_type("buy")
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_buy_from_a_people__")

        content_prompt = get_prompt_by_title("__start_to_buy_from_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_buy_from_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    async def ask_agent_start_to_sell_to_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = self._get_filtered_people_list_for_talk_type("sell")
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_sell_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_sell_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_sell_to_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    async def ask_agent_start_to_buy_from_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = self._get_filtered_people_list_for_talk_type("buy")
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_buy_from_a_people__")

        content_prompt = get_prompt_by_title("__start_to_buy_from_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_buy_from_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    def handle_ask_agent_start_to_sell_to_a_people_result(self, content):
        result = robust_json_loads(content, default=None)
        if not isinstance(result, dict):
            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))
            return
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]

            if not self._is_contact_allowed("sell", account):
                retry_count = int(getattr(self, "_pick_person_retry_count", {}).get("sell", 0) or 0)
                if retry_count < 2:
                    self._pick_person_retry_count["sell"] = retry_count + 1
                    hint = " Please choose a different person than the recently contacted ones."
                    self.ask_agent_start_to_sell_to_a_people_sync(self._pending_talk_objective + hint, "")
                    return
                self._pick_person_retry_count["sell"] = 0
            else:
                self._pick_person_retry_count["sell"] = 0

            self.current_talk_people = result
            # Explicitly reset talk_round for the new conversation
            result["talk_round"] = 0
            self.start_active_conversation(talk_type="sell", person=result, objective=self._pending_talk_objective)

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "I could not find the target person."

            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))

    def handle_ask_agent_start_to_buy_from_a_people_result(self, content):
        result = robust_json_loads(content, default=None)
        if not isinstance(result, dict):
            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))
            return
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]

            if not self._is_contact_allowed("buy", account):
                retry_count = int(getattr(self, "_pick_person_retry_count", {}).get("buy", 0) or 0)
                if retry_count < 2:
                    self._pick_person_retry_count["buy"] = retry_count + 1
                    hint = " Please choose a different person than the recently contacted ones."
                    self.ask_agent_start_to_buy_from_a_people_sync(self._pending_talk_objective + hint, "")
                    return
                self._pick_person_retry_count["buy"] = 0
            else:
                self._pick_person_retry_count["buy"] = 0

            self.current_talk_people = result
            # Explicitly reset talk_round for the new conversation
            result["talk_round"] = 0
            self.start_active_conversation(talk_type="buy", person=result, objective=self._pending_talk_objective)

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            message = "[AISNS_INT_003_INQUIRY]" + message
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "I could not find the target person."

            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))

    async def ask_agent_to_review_conversation_sell(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation_sell__")
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "Please evaluate strictly according to the requirements and output strictly in the required format.\n## Chat history \n" + (messages_history or "")
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    async def ask_agent_to_review_conversation_buy(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation_buy__")
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "Please evaluate strictly according to the requirements and output strictly in the required format.\n## Chat history \n" + (messages_history or "")
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def handle_agent_review_conversation_sell_result(self, content):

        self.handle_agent_review_conversation_sell_result_final(content)

    def handle_agent_review_conversation_sell_result_final(self, content):
        content = content.strip()
        result = robust_json_loads(content, default=None)
        if not isinstance(result, dict):
            retry_count = getattr(self, "_review_sell_retry_count", 0)
            if retry_count < 1:
                setattr(self, "_review_sell_retry_count", retry_count + 1)
                talk_history_str = json.dumps(self.current_talk_history, ensure_ascii=False)
                role_prompt = get_prompt_by_title("__review_conversation_sell__")
                role_prompt = role_prompt.replace("__messages_history__", talk_history_str)
                question = "Only output a single JSON object. Do not output any explanations or extra text."
                asyncio.create_task(self.ask_agent_and_get_instruction(question, role_prompt))
            else:
                setattr(self, "_review_sell_retry_count", 0)
            return
        setattr(self, "_review_sell_retry_count", 0)
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]

        if not continue_chat:
            self.taskmng.add_process_info_to_list(f"After talking with a friend, the situation is: {current_chat_summary}")
            self.write_task_process_to_pane(f"After talking with a friend, the situation is: {current_chat_summary}\n\n")
            self.taskmng.current_situation = f"After talking with someone else, the situation is: {current_chat_summary}"
            resume_ask_content = f"- Current objective\n{self.taskmng.current_objective}\n- Current progress\nAfter talking with someone else, the situation is: {current_chat_summary}"
            self.end_active_conversation(
                reason="completed",
                message="Sell conversation completed.",
                resume_activity=True,
                resume_ask_content=resume_ask_content,
            )

        else:
            if self.taskmng.current_process["rounds_current_person"] < self.max_rounds_per_person:
                self.taskmng.current_process["rounds_current_person"] = self.taskmng.current_process["rounds_current_person"] + 1
                self.talk_to_a_people(message, self.current_talk_people["nation_id"], self.current_talk_people["account"], self.current_talk_people["nick_name"])
            else:
                self.taskmng.add_process_info_to_list(f"After talking with a friend, the situation is: {current_chat_summary}")
                self.taskmng.current_situation = f"After talking with someone else, the situation is: {current_chat_summary}"
                resume_ask_content = f"- Current objective\n{self.taskmng.current_objective}\n- Current progress\nAfter talking with someone else, the situation is: {current_chat_summary}"
                self.end_active_conversation(
                    reason="max_rounds",
                    message="Sell conversation reached max rounds.",
                    resume_activity=True,
                    resume_ask_content=resume_ask_content,
                )

    def handle_agent_review_conversation_buy_result(self, content):

        self.handle_agent_review_conversation_buy_result_final(content)

    def handle_agent_review_conversation_buy_result_final(self, content):
        content = content.strip()
        result = robust_json_loads(content, default=None)
        if not isinstance(result, dict):
            retry_count = getattr(self, "_review_buy_retry_count", 0)
            if retry_count < 1:
                setattr(self, "_review_buy_retry_count", retry_count + 1)
                talk_history_str = json.dumps(self.current_talk_history, ensure_ascii=False)
                role_prompt = get_prompt_by_title("__review_conversation_buy__")
                role_prompt = role_prompt.replace("__messages_history__", talk_history_str)
                question = "Only output a single JSON object. Do not output any explanations or extra text."
                asyncio.create_task(self.ask_agent_and_get_instruction(question, role_prompt))
            else:
                setattr(self, "_review_buy_retry_count", 0)
            return
        setattr(self, "_review_buy_retry_count", 0)
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
            self.taskmng.add_process_info_to_list(f"After talking with a friend, the situation is: {current_chat_summary}")
            self.write_task_process_to_pane(f"After talking with a friend, the situation is: {current_chat_summary}\n\n")
            self.taskmng.current_situation = f"After talking with someone else, the situation is: {current_chat_summary}"
            resume_ask_content = f"- Current objective\n{self.taskmng.current_objective}\n- Current progress\nAfter talking with someone else, the situation is: {current_chat_summary}"
            self.end_active_conversation(
                reason="completed",
                message="Buy conversation completed.",
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
                self.taskmng.add_process_info_to_list(f"After talking with a friend, the situation is: {current_chat_summary}")
                self.taskmng.current_situation = f"After talking with someone else, the situation is: {current_chat_summary}"
                resume_ask_content = f"- Current objective\n{self.taskmng.current_objective}\n- Current progress\nAfter talking with someone else, the situation is: {current_chat_summary}"
                self.end_active_conversation(
                    reason="max_rounds",
                    message="Buy conversation reached max rounds.",
                    resume_activity=True,
                    resume_ask_content=resume_ask_content,
                )

    def check_pay_in_received(self, msg):
        """
            Extract a JSON string from the input, located between specific start/end markers.

            :param msg: Raw input containing the JSON string
            :return: Extracted JSON string, or None if not found
            """
        # Define regex pattern (raw string avoids escape issues)
        pattern = r'AISNS_INT_001_PAY_SEND_START(.*?)AISNS_INT_001_PAY_SEND_END'

        # Use re.search to find the matching part
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL lets '.' match newlines

        # If matched, return extracted content
        if match:
            result = match.group(1).strip()  # Extract and trim whitespace
            return result
        else:
            return None  # No match

    def check_good_in_received(self, msg):
        """
            Extract a JSON string from the input, located between specific start/end markers.

            :param msg: Raw input containing the JSON string
            :return: Extracted JSON string, or None if not found
            """
        # Define regex pattern (raw string avoids escape issues)
        pattern = r'AISNS_INT_002_GOOD_SEND_START(.*?)AISNS_INT_002_GOOD_SEND_END'

        # Use re.search to find the matching part
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL lets '.' match newlines

        # If matched, return extracted content
        if match:
            result = match.group(1).strip()  # Extract and trim whitespace
            return result
        else:
            return None  # No match

    def check_buy_in_received(self, msg):
        return "AISNS_INT_003_INQUIRY" in (msg or "")

    def send_pay(self, price, to_account: Optional[str] = None, to_nation_id: Optional[str] = None, to_nick_name: Optional[str] = None) -> None:
        trade_id = generate_random_id()
        current_talk_people = self.current_talk_people or {}

        account = (to_account or current_talk_people.get("account") or "").strip()
        nation_id = (to_nation_id or current_talk_people.get("nation_id") or "").strip()
        nick_name = (to_nick_name or current_talk_people.get("nick_name") or "").strip()
        if not account:
            logger.warning("send_pay called without a valid recipient account")
            return
        if not nation_id:
            nation_id = account
        if not nick_name:
            nick_name = account

        recipient_profession = (
            (current_talk_people.get("Profession") or current_talk_people.get("profession") or "").strip()
        )
        profession_key = recipient_profession.lower()
        if profession_key == "doctor":
            try:
                self.aichatcfg_record.life_point = self.aichatcfg_record.life_point + 25
                self.aichatcfg_record.move_point = round(
                    100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100),
                    1,
                )
                logger.info("Applied Doctor service effect: life_point and move_point updated")
            except Exception as e:
                logger.error(f"Failed to apply Doctor service effect: {e}", exc_info=True)
        elif profession_key == "restaurateur":
            try:
                self.aichatcfg_record.energy_point = self.aichatcfg_record.energy_point + 25
                self.aichatcfg_record.move_point = round(
                    100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100),
                    1,
                )
                logger.info("Applied Restaurateur service effect: energy_point and move_point updated")
            except Exception as e:
                logger.error(f"Failed to apply Restaurateur service effect: {e}", exc_info=True)
        try:
            message = f"AISNS_INT_001_PAY_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{price}\nAISNS_INT_001_PAY_SEND_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

            self.add_money(0 - float(price or 0))
            # Increment credit by 1 for each buy trade
            current_credit = int(self.aichatcfg_record.credit or 0)
            self.aichatcfg_record.credit = current_credit + 1
            trade_type = "B"
            title = f"Trade with {nick_name}"
            detail = "Waiting for goods"
            trade_with_name = nick_name
            trade_with_account = account

            existing = query_single_map_trade(trade_id=trade_id)
            if existing:
                update_map_trade(trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=1)
            else:
                add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=1)
        except Exception as e:
            logger.error(f"send_pay failed: {e}", exc_info=True)

    def handle_pay_received(self, price_str) -> None:
        talk_history_str = json.dumps(self.current_talk_history, ensure_ascii=False)
        trade_id, trade_price = self._parse_trade_payment(price_str)

        try:
            self.current_trade_price = float(trade_price or 0)
        except Exception:
            self.current_trade_price = 0

        try:
            record = query_AiChatCfg_map()
            profession = record.profession
            handle_after_trade = record.handle_after_trade
            handle_content = record.handle_content

            force_tool_call = str(handle_after_trade or "").strip().lower() == "tool"
            logger.info(
                "handle_pay_received: profession=%s, handle_after_trade=%s, force_tool_call=%s, handle_content=%s",
                profession,
                handle_after_trade,
                force_tool_call,
                handle_content,
            )

            if profession in {"Doctor", "Restaurateur"}:
                self.handle_send_goods(handle_content, trade_id)
                return

            if handle_after_trade in {"发送消息", "Send message"}:
                self.handle_send_goods(handle_content, trade_id)
                return

            tool_name = handle_content
            what_to_do = (
                "You have confirmed that the buyer's payment has been received, and now you need to deliver the goods/service content to the buyer.\n"
                "Please infer what the buyer purchased based on the chat history below, and generate the delivery content.\n"
                "Output requirements: only output the delivery content itself, do not explain; if you cannot infer, output a short default delivery message (e.g., Payment received; detailed content will be sent later).\n\n"
                "## Chat history \n" + talk_history_str
            )
            tool_task = self.run_configured_tool_text_generation_sync(
                tool_name,
                what_to_do,
                conversation_suffix="trade_delivery",
                force_tool_call=force_tool_call,
            )

            if isinstance(tool_task, asyncio.Task):
                def _on_tool_done(t: asyncio.Task):
                    try:
                        result_text = t.result()
                    except Exception as e:
                        logger.error(f"ask agent to run tool before send goods failed: {e}", exc_info=True)
                        result_text = f"Tool execution failed: {str(e)}"
                    if isinstance(result_text, str):
                        normalized = result_text.strip()
                        if (
                            not normalized
                            or "无法从当前对话记录中找到" in normalized
                            or "请提供聊天记录" in normalized
                        ):
                            result_text = "Payment received. Delivery details will be sent shortly."
                    try:
                        self.handle_send_goods(result_text, trade_id)
                    except Exception as e:
                        logger.error(f"handle_send_goods failed after tool execution: {e}", exc_info=True)

                tool_task.add_done_callback(_on_tool_done)
            else:
                self.handle_send_goods(tool_task, trade_id)

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

            good_payload = good_str
            if not isinstance(good_payload, str):
                good_payload = safe_json_dumps({"format": "aisns_goods_v1", "content": good_payload}, default=str(good_payload))
            else:
                good_payload = good_payload.strip()
                # Always normalize to structured payload unless it's already a JSON object
                if not (good_payload.startswith("{") and good_payload.endswith("}")):
                    good_payload = safe_json_dumps({"format": "aisns_goods_v1", "content": good_payload})

            message = f"AISNS_INT_002_GOOD_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{good_payload}\nAISNS_INT_002_GOOD_SEND_END"
            self.talk_to_a_people(message, nation_id, account, nick_name)
            trade_type = "S"
            title = f"Trade with {nick_name}"
            detail = good_payload
            trade_with_name = nick_name
            trade_with_account = account
            existing = query_single_map_trade(trade_id=trade_id)
            if existing:
                update_map_trade(trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=2)
            else:
                add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=2)
            self.add_money(price)
            # Increment credit by 1 for each sell trade
            current_credit = int(self.aichatcfg_record.credit or 0)
            self.aichatcfg_record.credit = current_credit + 1

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
            update_map_trade(trade_id, detail=goods_detail, status=3)
        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def add_money(self, count):
        money = float(self.aichatcfg_record.money or 0) + count
        self.aichatcfg_record.money = money
