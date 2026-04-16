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
                          add_function_mng, add_map_visit, get_key_value,
                          update_map_trade, add_map_trade, query_single_map_trade, update_AiChatCfg_by_user_id, update_AiChatCfg_map, query_AiChatCfg_map, add_mcp_mng, query_mcp_mng,
                          delete_map_preset_msg, query_map_preset_msg_all, add_map_preset_msg, query_AiChatCfg_map_setting)
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
from backend.apps.sns.memory.memory_types import MemoryType

logger = logging.getLogger(__name__)

class TradeMixin:

    def _ensure_sufficient_funds(
        self,
        amount: float,
        *,
        context: str,
        ui_notify: bool = True,
        end_conversation_on_fail: bool = True,
    ) -> bool:
        try:
            required = float(amount or 0)
        except Exception:
            required = 0.0

        if required <= 0:
            return True

        try:
            available = float(getattr(getattr(self, "aichatcfg_record", None), "money", 0) or 0)
        except Exception:
            available = 0.0

        if available >= required:
            return True

        normalized_context = (context or "payment").strip()
        msg = (
            f"Insufficient balance to {normalized_context}. "
            f"Required: ${required:.2f}, available: ${available:.2f}."
        )

        try:
            setattr(self, "_last_insufficient_funds_message", msg)
        except Exception:
            pass

        if ui_notify:
            try:
                if hasattr(self, "show_alert_on_map"):
                    self.show_alert_on_map(msg)
                else:
                    self.taskmng_js.show_information(f"<b>{msg}</b>")
            except Exception:
                pass

        if end_conversation_on_fail:
            try:
                active = getattr(self, "active_conversation", None)
                if active and hasattr(self, "end_active_conversation"):
                    try:
                        self.end_active_conversation(
                            reason="insufficient_funds",
                            message=msg,
                            resume_activity=True,
                            resume_ask_content="",
                        )
                    except TypeError:
                        self.end_active_conversation(
                            reason="insufficient_funds",
                            message=msg,
                            resume_activity=True,
                        )
            except Exception as e:
                logger.error("Failed to end conversation after insufficient funds: %s", e, exc_info=True)

        return False

    def _show_trade_success_info(
        self,
        *,
        title: str,
        paid: Optional[float] = None,
        earned: Optional[float] = None,
        money_before: Optional[float] = None,
        money_after: Optional[float] = None,
        energy_before: Optional[float] = None,
        energy_after: Optional[float] = None,
        life_before: Optional[float] = None,
        life_after: Optional[float] = None,
    ) -> None:
        try:
            ui = getattr(self, "taskmng_js", None)
            if ui is None:
                return

            def _fmt_money(v: Optional[float]) -> str:
                if v is None:
                    return "N/A"
                try:
                    return f"${float(v):.2f}"
                except Exception:
                    return "N/A"

            def _fmt_pct(v: Optional[float]) -> str:
                if v is None:
                    return "N/A"
                try:
                    return f"{float(v):.0f}%"
                except Exception:
                    return "N/A"

            lines = [f"<b>{title}</b>"]
            if energy_before is not None or energy_after is not None:
                lines.append(f"⚡Energy: {_fmt_pct(energy_before)} -> {_fmt_pct(energy_after)}")
            if life_before is not None or life_after is not None:
                lines.append(f"❤️Life: {_fmt_pct(life_before)} -> {_fmt_pct(life_after)}")
            if paid is not None:
                lines.append(f"💳Paid: {_fmt_money(paid)}")
            if earned is not None:
                lines.append(f"💵Earned: {_fmt_money(earned)}")
            if money_before is not None or money_after is not None:
                lines.append(f"💰Money: {_fmt_money(money_before)} -> {_fmt_money(money_after)}")

            ui.show_information("<br>".join(lines) + ".")

            try:
                energy_changed = (
                    energy_before is not None
                    and energy_after is not None
                    and float(energy_before) != float(energy_after)
                )
            except Exception:
                energy_changed = False

            try:
                life_changed = (
                    life_before is not None
                    and life_after is not None
                    and float(life_before) != float(life_after)
                )
            except Exception:
                life_changed = False

            try:
                money_changed = (
                    money_before is not None
                    and money_after is not None
                    and float(money_before) != float(money_after)
                )
            except Exception:
                money_changed = False

            if energy_changed or life_changed or money_changed:
                try:
                    alert_parts = [str(title or "").strip() or "Status update"]
                    if energy_changed:
                        alert_parts.append(f"⚡Energy: {_fmt_pct(energy_before)} -> {_fmt_pct(energy_after)}")
                    if life_changed:
                        alert_parts.append(f"❤️Life: {_fmt_pct(life_before)} -> {_fmt_pct(life_after)}")
                    if money_changed:
                        alert_parts.append(f"💰Money: {_fmt_money(money_before)} -> {_fmt_money(money_after)}")
                    alert_msg = " | ".join(p for p in alert_parts if p)
                    if hasattr(self, "show_alert_on_map"):
                        self.show_alert_on_map(alert_msg, is_error=False)
                except Exception:
                    pass
        except Exception:
            return

    def _broadcast_trade_upserted(self, trade_id: str) -> None:
        trade_id = (trade_id or "").strip()
        if not trade_id:
            return

        try:
            trade = query_single_map_trade(trade_id=trade_id)
            if not trade:
                return

            payload = {
                "id": getattr(trade, "id", None),
                "trade_id": getattr(trade, "trade_id", None),
                "trade_type": getattr(trade, "trade_type", None),
                "title": getattr(trade, "title", None),
                "detail": getattr(trade, "detail", None),
                "link": getattr(trade, "link", None),
                "trade_with_name": getattr(trade, "trade_with_name", None),
                "trade_with_account": getattr(trade, "trade_with_account", None),
                "trade_with_company": getattr(trade, "trade_with_company", None),
                "pay": getattr(trade, "pay", None),
                "pay_method": getattr(trade, "pay_method", None),
                "status": getattr(trade, "status", None),
                "create_time": trade.create_time.isoformat() if getattr(trade, "create_time", None) else None,
            }

            msg = {"type": "trade_upserted", "data": payload}

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(websocket_manager.broadcast(msg))
            except RuntimeError:
                asyncio.create_task(websocket_manager.broadcast(msg))
        except Exception as e:
            logger.warning("trade_upserted broadcast failed: %s", e)

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

        if not self._ensure_sufficient_funds(
            fee,
            context="purchase guidance",
            ui_notify=False,
            end_conversation_on_fail=False,
        ):
            return getattr(self, "_last_insufficient_funds_message", "Insufficient balance.")

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

        money_before = float(self.aichatcfg_record.money or 0)
        self.aichatcfg_record.money = money_before - fee
        self._show_trade_success_info(
            title="Guidance purchased",
            paid=float(fee),
            money_before=money_before,
            money_after=float(self.aichatcfg_record.money or 0),
        )
        return result

    def set_food_order(self):
        fee = 30
        provider = None
        try:
            provider = self.get_nearest_people_by_profession("Restaurateur")
        except Exception as e:
            logger.error(f"Failed to get nearest Restaurateur: {e}", exc_info=True)
        if provider:
            paid = self.send_pay(
                fee,
                to_account=provider.get("account"),
                to_nation_id=provider.get("nation_id"),
                to_nick_name=provider.get("nick_name"),
                good_name="food",
            )
            if not paid:
                return getattr(self, "_last_insufficient_funds_message", "Insufficient balance.")
        else:
            if not self._ensure_sufficient_funds(
                fee,
                context="purchase food",
                ui_notify=False,
                end_conversation_on_fail=False,
            ):
                return getattr(self, "_last_insufficient_funds_message", "Insufficient balance.")
            money_before = float(self.aichatcfg_record.money or 0)
            energy_before = float(self.aichatcfg_record.energy_point or 0)
            self.aichatcfg_record.energy_point = energy_before + 25
            self.aichatcfg_record.move_point = round(
                100 * (float(self.aichatcfg_record.life_point or 0) / 100) * (float(self.aichatcfg_record.energy_point or 0) / 100),
                1,
            )
            self.aichatcfg_record.money = money_before - fee
            self._show_trade_success_info(
                title="Food purchased",
                paid=float(fee),
                energy_before=energy_before,
                energy_after=float(self.aichatcfg_record.energy_point or 0),
                money_before=money_before,
                money_after=float(self.aichatcfg_record.money or 0),
            )

        result = f"You paid {fee} for food. Your energy is now {self.aichatcfg_record.energy_point}%"
        return result

    def set_taxi_order(self, current_position, target_position, target_place):
        point1 = (current_position[1], current_position[0])  # Convert to (lat, lon)
        point2 = (target_position[1], target_position[0])  # Convert to (lat, lon)

        # Compute distance using geopy
        dist = distance(point1, point2).kilometers
        fee = dist * 2.5

        if not self._ensure_sufficient_funds(
            float(fee or 0),
            context="order a taxi",
            ui_notify=False,
            end_conversation_on_fail=False,
        ):
            return getattr(self, "_last_insufficient_funds_message", "Insufficient balance.")

        money_before = float(self.aichatcfg_record.money or 0)
        self.aichatcfg_record.money = money_before - float(fee or 0)
        self._show_trade_success_info(
            title="Taxi ordered",
            paid=float(fee or 0),
            money_before=money_before,
            money_after=float(self.aichatcfg_record.money or 0),
        )

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
        if provider:
            paid = self.send_pay(
                fee,
                to_account=provider.get("account"),
                to_nation_id=provider.get("nation_id"),
                to_nick_name=provider.get("nick_name"),
                good_name="medical",
            )
            if not paid:
                return getattr(self, "_last_insufficient_funds_message", "Insufficient balance.")
        else:
            if not self._ensure_sufficient_funds(
                fee,
                context="purchase remote medical service",
                ui_notify=False,
                end_conversation_on_fail=False,
            ):
                return getattr(self, "_last_insufficient_funds_message", "Insufficient balance.")
            money_before = float(self.aichatcfg_record.money or 0)
            life_before = float(self.aichatcfg_record.life_point or 0)
            self.aichatcfg_record.life_point = life_before + 25
            self.aichatcfg_record.move_point = round(
                100 * (float(self.aichatcfg_record.life_point or 0) / 100) * (float(self.aichatcfg_record.energy_point or 0) / 100),
                1,
            )
            self.aichatcfg_record.money = money_before - fee
            self._show_trade_success_info(
                title="Medical service purchased",
                paid=float(fee),
                life_before=life_before,
                life_after=float(self.aichatcfg_record.life_point or 0),
                money_before=money_before,
                money_after=float(self.aichatcfg_record.money or 0),
            )

        result = f"You paid {fee} for remote medical service. Your life is now {self.aichatcfg_record.life_point}%"
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
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        all_people = []
        try:
            all_people = list(self.get_people_list() or [])
        except Exception:
            all_people = []

        filtered_people = None
        try:
            if hasattr(self, "_get_filtered_people_list_for_talk_type"):
                filtered_people = self._get_filtered_people_list_for_talk_type("sell")
        except Exception:
            filtered_people = None

        if filtered_people is not None:
            try:
                if hasattr(self, "_maybe_notify_recommended_excluded_by_talk_type_filter"):
                    self._maybe_notify_recommended_excluded_by_talk_type_filter(
                        talk_type="sell",
                        objective_text=objective_to_achieve,
                        all_people=all_people,
                        filtered_people=list(filtered_people or []),
                    )
            except Exception:
                pass

        people_list = (list(filtered_people or []) if filtered_people is not None else []) or all_people
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_sell_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_sell_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        # Memory recall: append past interaction memories for candidate people
        try:
            mm = getattr(self, "memory_manager", None)
            if mm:
                person_memory_sections = []
                for person in people_list[:5]:
                    acct = (person.get("account") or "").strip()
                    name = (person.get("nick_name") or acct)
                    if acct:
                        section = mm.get_person_memory_prompt_section(acct, person_name=name, max_results=2, max_chars=300)
                        if section:
                            person_memory_sections.append(section)
                if person_memory_sections:
                    content_prompt += "\n\n" + "\n".join(person_memory_sections)
        except Exception as _mem_err:
            logger.warning("Memory recall failed for sell people selection: %s", _mem_err)

        self.command_status = "ask_agent_start_to_sell_to_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    def ask_agent_start_to_buy_from_a_people_sync(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = None
        try:
            if hasattr(self, "_get_filtered_people_list_for_talk_type"):
                people_list = self._get_filtered_people_list_for_talk_type("buy")
        except Exception:
            people_list = None
        if not people_list:
            people_list = self.get_people_list()
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_buy_from_a_people__")

        content_prompt = get_prompt_by_title("__start_to_buy_from_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        # Memory recall: append past interaction memories for candidate people
        try:
            mm = getattr(self, "memory_manager", None)
            if mm:
                person_memory_sections = []
                for person in people_list[:5]:
                    acct = (person.get("account") or "").strip()
                    name = (person.get("nick_name") or acct)
                    if acct:
                        section = mm.get_person_memory_prompt_section(acct, person_name=name, max_results=2, max_chars=300)
                        if section:
                            person_memory_sections.append(section)
                if person_memory_sections:
                    content_prompt += "\n\n" + "\n".join(person_memory_sections)
        except Exception as _mem_err:
            logger.warning("Memory recall failed for buy people selection: %s", _mem_err)

        self.command_status = "ask_agent_start_to_buy_from_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    async def ask_agent_start_to_sell_to_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        all_people = []
        try:
            all_people = list(self.get_people_list() or [])
        except Exception:
            all_people = []

        filtered_people = None
        try:
            if hasattr(self, "_get_filtered_people_list_for_talk_type"):
                filtered_people = self._get_filtered_people_list_for_talk_type("sell")
        except Exception:
            filtered_people = None

        if filtered_people is not None:
            try:
                if hasattr(self, "_maybe_notify_recommended_excluded_by_talk_type_filter"):
                    self._maybe_notify_recommended_excluded_by_talk_type_filter(
                        talk_type="sell",
                        objective_text=objective_to_achieve,
                        all_people=all_people,
                        filtered_people=list(filtered_people or []),
                    )
            except Exception:
                pass

        people_list = (list(filtered_people or []) if filtered_people is not None else []) or all_people
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_sell_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_sell_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_sell_to_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    async def ask_agent_start_to_buy_from_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        people_list = None
        try:
            if hasattr(self, "_get_filtered_people_list_for_talk_type"):
                people_list = self._get_filtered_people_list_for_talk_type("buy")
        except Exception:
            people_list = None
        if not people_list:
            people_list = self.get_people_list()
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
            required_keys = ["nation_id", "account", "message", "nick_name"]
            missing = []
            for k in required_keys:
                v = result.get(k, None)
                if not isinstance(v, str) or not v.strip():
                    missing.append(k)
            if missing:
                logger.warning(
                    f"Invalid people selection result in sell. missing={missing} raw={str(content)[:300]}"
                )
                asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))
                return

            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]

            try:
                if hasattr(self, "_is_contact_allowed") and not self._is_contact_allowed("sell", account):
                    retry_state = getattr(self, "_contact_pick_retry", None)
                    if not isinstance(retry_state, dict):
                        retry_state = {}
                    retry_count = int(retry_state.get("sell", 0) or 0)
                    if retry_count < 3:
                        retry_state["sell"] = retry_count + 1
                        self._contact_pick_retry = retry_state
                        try:
                            if hasattr(self, "_notify_llm_recommended_user_unavailable"):
                                self._notify_llm_recommended_user_unavailable(account=account, nick_name=nick_name)
                        except Exception:
                            pass
                        objective = (getattr(self, "_pending_talk_objective", "") or "").strip()
                        self.ask_agent_start_to_sell_to_a_people_sync(objective, "")
                        return
                    retry_state["sell"] = 0
                    self._contact_pick_retry = retry_state
                    self.taskmng_js.show_information(
                        lt(
                            "<b>No eligible contacts are available due to anti-harassment rules.</b>",
                            "<b>No eligible contacts are available due to anti-harassment rules.</b>",
                        )
                    )
                    try:
                        if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                            self._maybe_finish_human_command_if_idle(ask_content=self.taskmng.get_current_objective())
                        else:
                            asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=self.taskmng.get_current_objective()))
                    except Exception:
                        pass
                    return
            except Exception:
                pass

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
            required_keys = ["nation_id", "account", "message", "nick_name"]
            missing = []
            for k in required_keys:
                v = result.get(k, None)
                if not isinstance(v, str) or not v.strip():
                    missing.append(k)
            if missing:
                logger.warning(
                    f"Invalid people selection result in buy. missing={missing} raw={str(content)[:300]}"
                )
                asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))
                return

            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]

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
            self.taskmng_js.show_information(f"<b>Conversation with promotion target finished. Summary:</b><br> {current_chat_summary}")
            try:
                if hasattr(self, "show_alert_on_map"):
                    self.show_alert_on_map(
                        f"Conversation with promotion target finished. Summary: {current_chat_summary}",
                        is_error=False,
                    )
            except Exception:
                pass
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

        goods_name = result.get("goods_name", "")
        buyer = result.get("buyer", "")
        buy_score = result.get("buy_score", 0)
        price = result.get("price", 0)

        if buy_score >= 80 and price >= 0 and  buyer.lower()=="me":
            self.send_pay(price, good_name=goods_name)
            # self.end_active_conversation(
            #     reason="pay",
            #     message="Payment initiated.",
            #     resume_activity=True,
            #     resume_ask_content="",
            # )
            return

        if not continue_chat:
            self.taskmng.add_process_info_to_list(f"After talking with a friend, the situation is: {current_chat_summary}")
            self.write_task_process_to_pane(f"After talking with a friend, the situation is: {current_chat_summary}\n\n")
            self.taskmng_js.show_information(f"<b>Conversation with the seller finished. Summary:</b><br> {current_chat_summary}")
            try:
                if hasattr(self, "show_alert_on_map"):
                    self.show_alert_on_map(
                        f"Conversation with the seller finished. Summary: {current_chat_summary}",
                        is_error=False,
                    )
            except Exception:
                pass
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

    def send_pay(
        self,
        price,
        to_account: Optional[str] = None,
        to_nation_id: Optional[str] = None,
        to_nick_name: Optional[str] = None,
        good_name: Optional[str] = None,
    ) -> bool:
        trade_id = generate_random_id()
        money_before = float(self.aichatcfg_record.money or 0)
        energy_before = float(self.aichatcfg_record.energy_point or 0)
        life_before = float(self.aichatcfg_record.life_point or 0)
        current_talk_people = self.current_talk_people or {}
        logger.info("sendpay.......")
        logger.info(current_talk_people)

        account = (to_account or current_talk_people.get("account") or "").strip()
        nation_id = (to_nation_id or current_talk_people.get("nation_id") or "").strip()
        nick_name = (to_nick_name or current_talk_people.get("nick_name") or "").strip()
        if not account:
            logger.warning("send_pay called without a valid recipient account")
            return False
        if not nation_id:
            nation_id = account
        if not nick_name:
            nick_name = account

        recipient_profession = (current_talk_people.get("Profession") or current_talk_people.get("profession") or "").strip()
        if not recipient_profession and account:
            try:
                for p in (self.get_people_list() or []):
                    if not isinstance(p, dict):
                        continue
                    p_account = (p.get("account") or "").strip()
                    if p_account and p_account == account:
                        recipient_profession = (p.get("profession") or p.get("Profession") or "").strip()
                        if recipient_profession:
                            break
            except Exception:
                pass
        profession_key = recipient_profession.lower()
        print("recipient_profession")
        print(profession_key)

        try:
            paid_value = float(price or 0)
        except Exception:
            paid_value = 0.0

        active_conversation = bool(getattr(self, "active_conversation", None))
        if not self._ensure_sufficient_funds(
            paid_value,
            context=f"make a payment to {nick_name or account}",
            ui_notify=active_conversation,
            end_conversation_on_fail=active_conversation,
        ):
            return False

        trade_title = "Purchase completed"
        show_energy = False
        show_life = False

        if profession_key == "doctor" or (isinstance(good_name, str) and good_name.strip().lower() == "medical"):
            try:
                self.aichatcfg_record.life_point = float(self.aichatcfg_record.life_point or 0) + 25
                self.aichatcfg_record.move_point = round(
                    100 * (float(self.aichatcfg_record.life_point or 0) / 100) * (float(self.aichatcfg_record.energy_point or 0) / 100),
                    1,
                )
                logger.info("Applied Doctor service effect: life_point and move_point updated")
                trade_title = "Medical service purchased"
                show_life = True
            except Exception as e:
                logger.error(f"Failed to apply Doctor service effect: {e}", exc_info=True)
        elif profession_key == "restaurateur" or (isinstance(good_name, str) and good_name.strip().lower() == "food"):
            try:
                self.aichatcfg_record.energy_point = float(self.aichatcfg_record.energy_point or 0) + 25
                self.aichatcfg_record.move_point = round(
                    100 * (float(self.aichatcfg_record.life_point or 0) / 100) * (float(self.aichatcfg_record.energy_point or 0) / 100),
                    1,
                )
                logger.info("Applied Restaurateur service effect: energy_point and move_point updated")
                trade_title = "Food purchased"
                show_energy = True
            except Exception as e:
                logger.error(f"Failed to apply Restaurateur service effect: {e}", exc_info=True)
        try:
            message = f"AISNS_INT_001_PAY_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{price}\nAISNS_INT_001_PAY_SEND_END"

            try:
                if not isinstance(getattr(self, "current_talk_people", None), dict) or not self.current_talk_people:
                    self.current_talk_people = {
                        "nation_id": nation_id,
                        "account": account,
                        "nick_name": nick_name,
                    }
                round_value = int(self.current_talk_people.get("talk_round", 0) or 0)
                if round_value < 1:
                    self.current_talk_people["talk_round"] = 1
            except Exception:
                pass

            self.talk_to_a_people(message, nation_id, account, nick_name)

            self.add_money(0 - paid_value)
            money_after = float(self.aichatcfg_record.money or 0)
            self._show_trade_success_info(
                title=trade_title,
                paid=paid_value,
                energy_before=energy_before if show_energy else None,
                energy_after=float(self.aichatcfg_record.energy_point or 0) if show_energy else None,
                life_before=life_before if show_life else None,
                life_after=float(self.aichatcfg_record.life_point or 0) if show_life else None,
                money_before=money_before,
                money_after=money_after,
            )

            # Memory capture: record buy trade
            try:
                from backend.apps.sns.memory.memory_config import MemoryConfig
                mm = getattr(self, "memory_manager", None)
                if mm and MemoryConfig.ENABLED:
                    mm.capture_async(
                        MemoryType.TRADE,
                        key=f"Paid {price} to {nick_name}",
                        content=f"Bought from {nick_name} (account: {account}) for ${float(price or 0):.2f}.",
                        metadata={
                            "trade_type": "buy",
                            "account": account,
                            "nation_id": nation_id,
                            "nick_name": nick_name,
                            "price": float(price or 0),
                            "trade_id": trade_id,
                        },
                        importance=70,
                    )
            except Exception as _mem_err:
                logger.warning("Memory capture failed for buy trade: %s", _mem_err)

            # Increment credit by 1 for each buy trade
            current_credit = int(self.aichatcfg_record.credit or 0)
            self.aichatcfg_record.credit = current_credit + 1
            trade_type = "B"
            title = (good_name or "").strip() or f"Trade with {nick_name}"
            detail = "Waiting for goods"
            trade_with_name = nick_name
            trade_with_account = account

            existing = query_single_map_trade(trade_id=trade_id)
            if existing:
                update_map_trade(trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=1)
            else:
                add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=1)

            self._broadcast_trade_upserted(trade_id)
            return True
        except Exception as e:
            logger.error(f"send_pay failed: {e}", exc_info=True)
            return False

    def handle_pay_received(self, price_str) -> None:
        try:
            self.command_status = ""
        except Exception:
            pass
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

            if handle_after_trade == "message":
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
        try:
            self.command_status = ""
        except Exception:
            pass
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]
        price = self.current_trade_price

        try:
            if not trade_id:
                trade_id = generate_random_id()

            good_payload = good_str
            # if not isinstance(good_payload, str):
            #     good_payload = safe_json_dumps({"format": "aisns_goods_v1", "content": good_payload}, default=str(good_payload))
            # else:
            #     good_payload = good_payload.strip()
            #     # Always normalize to structured payload unless it's already a JSON object
            #     if not (good_payload.startswith("{") and good_payload.endswith("}")):
            #         good_payload = safe_json_dumps({"format": "aisns_goods_v1", "content": good_payload})

            message = f"AISNS_INT_002_GOOD_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{good_payload}\nAISNS_INT_002_GOOD_SEND_END"

            # Avoid the first-round 5s delay in talk_to_a_people for trade delivery.
            try:
                if isinstance(self.current_talk_people, dict):
                    round_value = int(self.current_talk_people.get("talk_round", 0) or 0)
                    if round_value < 1:
                        self.current_talk_people["talk_round"] = 1
            except Exception:
                pass

            self.talk_to_a_people(message, nation_id, account, nick_name)
            trade_type = "S"
            title = (
                (getattr(getattr(self, "aichatcfg_record", None), "goods_or_service_description", None) or "").strip()
                or f"Trade with {nick_name}"
            )
            detail = good_payload
            trade_with_name = nick_name
            trade_with_account = account
            existing = query_single_map_trade(trade_id=trade_id)
            if existing:
                update_map_trade(trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=2)
            else:
                add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account, status=2)

            self._broadcast_trade_upserted(trade_id)
            money_before = float(self.aichatcfg_record.money or 0)
            self.add_money(price)
            money_after = float(self.aichatcfg_record.money or 0)
            self._show_trade_success_info(
                title="Sale completed",
                earned=float(price or 0),
                money_before=money_before,
                money_after=money_after,
            )



            # Memory capture: record sell trade
            try:
                from backend.apps.sns.memory.memory_config import MemoryConfig
                mm = getattr(self, "memory_manager", None)
                if mm and MemoryConfig.ENABLED:
                    mm.capture_async(
                        MemoryType.TRADE,
                        key=f"Sold to {nick_name} for {price}",
                        content=f"Sold goods/service to {nick_name} (account: {account}) for ${float(price or 0):.2f}. Detail: {str(good_payload)[:200]}",
                        metadata={
                            "trade_type": "sell",
                            "account": account,
                            "nation_id": nation_id,
                            "nick_name": nick_name,
                            "price": float(price or 0),
                            "trade_id": trade_id,
                        },
                        importance=75,
                    )
            except Exception as _mem_err:
                logger.warning("Memory capture failed for sell trade: %s", _mem_err)

            def _end_trade_conversation():
                self.end_active_conversation(
                    reason="Good sent,Trade complete.",
                    message="Good sent,Trade complete.",
                    resume_activity=True,
                    resume_ask_content="",
                )

            try:
                loop = asyncio.get_running_loop()
                loop.call_later(6, _end_trade_conversation)
            except RuntimeError:
                async def _end_conversation_delayed():
                    await asyncio.sleep(6)
                    _end_trade_conversation()

                asyncio.create_task(_end_conversation_delayed())

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

            self._broadcast_trade_upserted(trade_id)

            def _end_trade_conversation():
                self.end_active_conversation(
                    reason="Good received,Trade complete.",
                    message="Good received,Trade complete.",
                    resume_activity=True,
                    resume_ask_content="",
                )

            try:
                loop = asyncio.get_running_loop()
                loop.call_later(3, _end_trade_conversation)
            except RuntimeError:
                async def _end_conversation_delayed():
                    await asyncio.sleep(3)
                    _end_trade_conversation()

                asyncio.create_task(_end_conversation_delayed())
        except Exception as e:
            print(f"Handle goods received error: {str(e)}")

    def add_money(self, count):
        money = float(self.aichatcfg_record.money or 0) + count
        self.aichatcfg_record.money = money
        # Check rebirth after money change
        self.check_and_handle_rebirth()
