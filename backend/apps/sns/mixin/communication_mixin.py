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
from typing import List, Dict, Optional, Tuple
import json
import logging
import requests
import geopy.distance
from geopy.distance import distance
from geopy.point import Point
from geographiclib.geodesic import Geodesic
import random

from backend.shared.utils import robust_json_loads
from backend.apps.sns.memory.memory_types import MemoryType

logger = logging.getLogger(__name__)


class CommunicationMixin:
    def _should_bypass_contact_limits(self) -> bool:
        try:
            if bool(getattr(self, "human_take_over", False)):
                return True
        except Exception:
            pass

        try:
            return bool(getattr(self, "_bypass_contact_limits", False))
        except Exception:
            return False

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

        try:
            if bool(getattr(self, "_human_command_inflight", False)):
                self._human_command_inflight = False
        except Exception:
            pass
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
                    msg_html = f"<b>Conversation timed out after {timeout_s}s. Unable to connect to {active_account}.</b>"
                    msg_map = f"Conversation timed out after {timeout_s}s. Unable to connect to {active_account}."

                    try:
                        self.taskmng_js.show_information(msg_html)
                    except Exception:
                        pass

                    try:
                        self.show_alert_on_map(msg_map)
                    except Exception:
                        pass

                    self.end_active_conversation(
                        reason="timeout",
                        message=f"Conversation timed out after {timeout_s}s. Unable to connect to {active_account}.",
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
            #Temporarily not displayed on the map,Temporarily commented out
            # self.send_msg_to_map(("show_information_chat", self._format_inbox_message(account, content), ""))
            logger.info("show_information_chat is canceled Temporarily")
        except Exception as e:
            logger.error(f"Failed to notify inbox message: {e}")

    async def maybe_auto_reply_from_inbox(self) -> bool:
        try:
            if bool(getattr(self, "human_take_over", False)):
                return False
        except Exception:
            return False

        inbox = getattr(self, "conversation_inbox", None)
        if inbox is None or not isinstance(inbox, dict) or (not inbox):
            return False

        now_ts = self._now_ts()
        cutoff = now_ts - 240.0

        per_account_candidate = []
        accounts_to_drop = []
        for account, items in list(inbox.items()):
            account = (account or "").strip()
            if not account:
                continue
            if items is None or not isinstance(items, list):
                accounts_to_drop.append(account)
                continue

            newest_ts = -1.0
            newest_content = None
            recent_items = []
            for item in items:
                if item is None or not isinstance(item, dict):
                    continue
                ts = float(item.get("ts", 0.0) or 0.0)
                if ts < cutoff:
                    continue
                content = item.get("content", "")
                if content is None:
                    content = ""
                content = str(content)
                recent_items.append({"ts": ts, "content": content})
                if ts >= newest_ts:
                    newest_ts = ts
                    newest_content = content

            if not recent_items:
                accounts_to_drop.append(account)
                continue

            inbox[account] = recent_items

            if newest_content is not None and newest_content.strip() == "TERMINATE":
                accounts_to_drop.append(account)
                continue

            if newest_content is None:
                continue

            per_account_candidate.append((account, newest_ts, newest_content))

        for account in accounts_to_drop:
            try:
                inbox.pop(account, None)
            except Exception:
                pass

        if not per_account_candidate:
            return False

        best = None
        best_key = None
        for account, ts, content in per_account_candidate:
            is_inquiry = "[AISNS_INT_003_INQUIRY]" in content
            key = (1 if is_inquiry else 0, float(ts or 0.0))
            if best is None or key > best_key:
                best = (account, ts, content)
                best_key = key

        if best is None:
            return False

        account, _, content = best

        try:
            inbox.pop(account, None)
        except Exception:
            pass

        try:
            return await self._auto_reply_from_inbox_message(account, content)
        except Exception:
            logger.exception("Inbox auto-reply failed")
            return False

    async def _auto_reply_from_inbox_message(self, account: str, content: str) -> bool:
        account = (account or "").strip()
        if not account:
            return False

        person = None
        try:
            if hasattr(self, "_get_people_by_account"):
                person = self._get_people_by_account(account)
        except Exception:
            person = None

        nation_id = account
        nick_name = account
        if isinstance(person, dict):
            nation_id = (person.get("nation_id") or "").strip() or nation_id
            nick_name = (person.get("nick_name") or "").strip() or nick_name

        talk_type = ""
        try:
            pending = getattr(self, "_pending_peer_talk_type", None)
            if isinstance(pending, dict):
                talk_type = (pending.get(account) or "").strip()
        except Exception:
            talk_type = ""

        if not talk_type:
            try:
                active = getattr(self, "active_conversation", None) or {}
                if isinstance(active, dict):
                    talk_type = (active.get("talk_type") or "").strip()
            except Exception:
                talk_type = ""

        if not talk_type:
            talk_type = (getattr(self, "talk_type", "") or "").strip() or "communication"

        objective = (getattr(self, "_pending_talk_objective", "") or "").strip()

        try:
            self.current_talk_history = []
        except Exception:
            pass

        try:
            self.current_talk_people = {
                "nation_id": nation_id,
                "account": account,
                "nick_name": nick_name,
                "talk_round": 0,
            }
        except Exception:
            pass

        try:
            self.start_active_conversation(
                talk_type=talk_type,
                person={"nation_id": nation_id, "account": account, "nick_name": nick_name},
                objective=objective,
            )
        except Exception:
            pass

        try:
            if nation_id and hasattr(self, "send_msg_to_map"):
                self.send_msg_to_map(("start_talk_to_it", nation_id, ""))
        except Exception:
            pass

        await asyncio.sleep(0)

        try:
            if hasattr(self, "handle_receiveMessage"):
                await self.handle_receiveMessage(content, account)
                return True
        except Exception:
            logger.exception("Failed to process inbox message")

        return False

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

    def _extract_recommended_contact_from_objective(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        raw = (text or "").strip()
        if not raw:
            return None, None

        try:
            m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw)
            if m:
                return (m.group(0) or "").strip(), None
        except Exception:
            pass

        recommended_account = None
        recommended_nick = None

        try:
            m = re.search(r"(?:^|\b)account\s*[:=]\s*([^\s,;]+)", raw, flags=re.IGNORECASE)
            if m:
                recommended_account = (m.group(1) or "").strip().strip('"\'')
        except Exception:
            pass

        try:
            m = re.search(r"(?:^|\b)nick_name\s*[:=]\s*([^\n,;]+)", raw, flags=re.IGNORECASE)
            if m:
                recommended_nick = (m.group(1) or "").strip().strip('"\'')
        except Exception:
            pass

        try:
            if not recommended_nick:
                m = re.search(r"['\"]([^'\"]{2,50})['\"]", raw)
                if m:
                    recommended_nick = (m.group(1) or "").strip()
        except Exception:
            pass

        recommended_account = (recommended_account or "").strip() or None
        recommended_nick = (recommended_nick or "").strip() or None
        return recommended_account, recommended_nick

    def _format_contact_who(self, *, account: Optional[str], nick_name: Optional[str]) -> str:
        parts = []
        acct = (account or "").strip()
        name = (nick_name or "").strip()
        if acct:
            parts.append(f"account={acct}")
        if name:
            parts.append(f"nick_name={name}")
        return " / ".join(parts)

    def _notify_llm_recommended_user_unavailable(
        self,
        *,
        account: Optional[str],
        nick_name: Optional[str],
    ) -> None:
        who = self._format_contact_who(account=account, nick_name=nick_name)
        if not who:
            return

        msg = (
            "Due to anti-harassment rules, the LLM-recommended user is unavailable "
            f"({who}). Selecting another user instead."
        )

        try:
            ui = getattr(self, "taskmng_js", None)
            if ui is not None:
                ui.show_information(f"<b>{msg}</b>")
        except Exception:
            pass

        try:
            if hasattr(self, "show_alert_on_map"):
                self.show_alert_on_map(msg, is_error=True)
        except Exception:
            pass

    def _maybe_notify_recommended_excluded_by_talk_type_filter(
        self,
        *,
        talk_type: str,
        objective_text: str,
        all_people: List[dict],
        filtered_people: List[dict],
    ) -> None:
        if (talk_type or "").strip().lower() == "buy":
            return

        recommended_account, recommended_nick = self._extract_recommended_contact_from_objective(objective_text)
        if not recommended_account and not recommended_nick:
            return

        filtered_accounts = {
            ((p or {}).get("account") or "").strip()
            for p in (filtered_people or [])
            if isinstance(p, dict)
        }

        excluded = [
            p
            for p in (all_people or [])
            if isinstance(p, dict)
            and ((p.get("account") or "").strip())
            and ((p.get("account") or "").strip() not in filtered_accounts)
        ]

        matched = None
        if recommended_account:
            ra = recommended_account.strip()
            for p in excluded:
                if ((p.get("account") or "").strip()) == ra:
                    matched = p
                    break

        if matched is None and recommended_nick:
            rn = recommended_nick.strip().lower()
            for p in excluded:
                if ((p.get("nick_name") or "").strip().lower()) == rn:
                    matched = p
                    break

        if matched is None:
            return

        self._notify_llm_recommended_user_unavailable(
            account=(matched.get("account") or recommended_account),
            nick_name=(matched.get("nick_name") or recommended_nick),
        )

    def _record_contact(self, talk_type: str, account: str) -> None:
        if not account:
            return
        if (talk_type or "").strip().lower() == "buy":
            return
        now_ts = self._now_ts()
        last_time = getattr(self, "_contact_last_time", None)
        if last_time is None or not isinstance(last_time, dict):
            self._contact_last_time = {}
            last_time = self._contact_last_time
        last_time[account] = now_ts

        recent = getattr(self, "_recent_contacts", None)
        if recent is None or not isinstance(recent, dict):
            self._recent_contacts = {"sell": [], "communication": []}
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
        if self._should_bypass_contact_limits():
            return True
        if (talk_type or "").strip().lower() == "buy":
            return True
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
        if self._should_bypass_contact_limits():
            return people
        if (talk_type or "").strip().lower() == "buy":
            return people
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
        return filtered

    def start_active_conversation(self, *, talk_type: str, person: dict, objective: str = "") -> None:
        account = (person or {}).get("account")
        account = (account or "").strip()
        nation_id = (person or {}).get("nation_id")
        nation_id = (nation_id or "").strip() or account
        nick_name = (person or {}).get("nick_name")
        nick_name = (nick_name or "").strip() or account
        a2a_endpoint = (person or {}).get("a2a_endpoint")
        a2a_endpoint = (a2a_endpoint or "").strip() if isinstance(a2a_endpoint, str) else ""

        if (not a2a_endpoint) and account:
            try:
                matched = self._get_people_by_account(account)
                if isinstance(matched, dict):
                    v = matched.get("a2a_endpoint")
                    if isinstance(v, str) and v.strip():
                        a2a_endpoint = v.strip()
            except Exception:
                pass

        if not account:
            return

        active_account = self._get_active_account()
        if active_account and active_account != account:
            try:
                self.show_alert_on_map(
                    "Due to anti-harassment rules, the selected user was contacted too frequently. A different user has been selected for you.",
                    is_error=False,
                )
            except Exception:
                pass

            try:
                time.sleep(3)
            except Exception:
                pass

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
            "a2a_endpoint": a2a_endpoint,
            "objective": (objective or "").strip(),
            "started_at": self._now_ts(),
        }

        try:
            self.talk_type = talk_type
        except Exception:
            pass

        try:
            pending = getattr(self, "_pending_peer_talk_type", None)
            if isinstance(pending, dict) and account:
                pending.pop(account, None)
        except Exception:
            pass

        self._conversation_last_activity_ts = self._now_ts()
        self._record_contact(talk_type, account)
        self._ensure_conversation_timeout_task()

        try:
            if getattr(self, "_bypass_contact_limits", False) and not bool(getattr(self, "human_take_over", False)):
                self._bypass_contact_limits = False
        except Exception:
            pass

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

        logger.info(
            "end_active_conversation called: reason=%s, account=%s, nation_id=%s",
            reason,
            account,
            nation_id,
        )

        # Memory capture: record conversation summary
        try:
            from backend.apps.sns.memory.memory_config import MemoryConfig
            active = getattr(self, "active_conversation", None) or {}
            talk_type = active.get("talk_type", "communication")
            nick_name = active.get("nick_name", account)
            objective = active.get("objective", "")
            history = list(getattr(self, "current_talk_history", []) or [])
            summary = message or f"Conversation with {nick_name} ended ({reason})"
            if history:
                summary += " Exchanges: " + "; ".join(h[:100] for h in history[-4:])

            mm = getattr(self, "memory_manager", None)
            if mm and MemoryConfig.ENABLED:
                mm.capture_async(
                    MemoryType.CONVERSATION,
                    key=f"Talked with {nick_name} ({talk_type})",
                    content=summary[:500],
                    metadata={
                        "account": account,
                        "nation_id": nation_id,
                        "nick_name": nick_name,
                        "talk_type": talk_type,
                        "reason": reason,
                        "objective": objective[:200] if objective else "",
                        "rounds": len(history),
                    },
                    importance=65 if talk_type == "communication" else 75,
                )
        except Exception as _mem_err:
            logger.warning("Memory capture failed for conversation end: %s", _mem_err)

        try:
            if nation_id:
                self.send_msg_to_map(("stop_talk_to_it", nation_id, ""))
        except Exception as e:
            logger.error(f"Failed to send stop_talk_to_it: {e}")

        try:
            self.show_status_on_map("idle")
        except Exception:
            pass

        try:
            t = getattr(self, "_conversation_timeout_task", None)
            if isinstance(t, asyncio.Task) and not t.done():
                t.cancel()
            self._conversation_timeout_task = None
        except Exception:
            pass

        try:
            t = getattr(self, "_conversation_first_message_task", None)
            if isinstance(t, asyncio.Task) and not t.done():
                t.cancel()
            self._conversation_first_message_task = None
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
                if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                    self._maybe_finish_human_command_if_idle(ask_content=resume_ask_content or "")
                else:
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

        account = (account or "").strip()
        if (not account) or ("@" not in account):
            warn_msg = f"Invalid XMPP account: {account}. Skipping this contact."
            try:
                self.taskmng.add_process_info_to_list(f"system:{warn_msg}")
            except Exception:
                pass
            try:
                if hasattr(self, "show_alert_on_map"):
                    self.show_alert_on_map(warn_msg, is_error=True)
            except Exception:
                pass
            try:
                self.taskmng_js.show_information(f"<b>{warn_msg}</b>")
            except Exception:
                pass

            resume_ask_content = ""
            try:
                resume_ask_content = self.taskmng.get_current_objective() or ""
            except Exception:
                resume_ask_content = ""

            try:
                self.end_active_conversation(
                    reason="invalid_account",
                    message=warn_msg,
                    resume_activity=True,
                    resume_ask_content=resume_ask_content,
                )
            except Exception:
                try:
                    if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                        self._maybe_finish_human_command_if_idle(ask_content=resume_ask_content or "")
                    else:
                        asyncio.create_task(
                            self.taskmng.process_task(action="process_activity", ask_content=resume_ask_content or "")
                        )
                except Exception:
                    pass
            return

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
            round = 1

        # First round of a new conversation: delay 3s so frontend has time to
        # move the 3D person model before the chat bubble appears.
        # Subsequent rounds (review replies) send immediately.
        command = ("start_talk_to_it", nationid, content)
        self.send_msg_to_map(command)
        if round <= 1:
            logger.info("First round of conversation with %s, delaying send_msg_to_map and sendMessage by 5s", account)

            async def _delayed_first_message():
                await asyncio.sleep(5)
                ok = self.sendMessage(content, False, account, user_name)
                if ok is False:
                    resume_ask_content = ""
                    try:
                        resume_ask_content = self.taskmng.get_current_objective() or ""
                    except Exception:
                        resume_ask_content = ""
                    try:
                        self.end_active_conversation(
                            reason="send_failed",
                            message="Failed to send message. Skipping.",
                            resume_activity=True,
                            resume_ask_content=resume_ask_content,
                        )
                    except Exception:
                        pass

            try:
                prev = getattr(self, "_conversation_first_message_task", None)
                if isinstance(prev, asyncio.Task) and not prev.done():
                    prev.cancel()
            except Exception:
                pass
            self._conversation_first_message_task = asyncio.create_task(_delayed_first_message())
        else:

            ok = self.sendMessage(content, False, account, user_name)
            if ok is False:
                resume_ask_content = ""
                try:
                    resume_ask_content = self.taskmng.get_current_objective() or ""
                except Exception:
                    resume_ask_content = ""
                try:
                    self.end_active_conversation(
                        reason="send_failed",
                        message="Failed to send message. Skipping.",
                        resume_activity=True,
                        resume_ask_content=resume_ask_content,
                    )
                except Exception:
                    pass

        if account not in self.talk_history:
            self.talk_history[account] = []
        self.talk_history[account].append("Me:" + content)
        self.current_talk_history.append("Me:" + content)

    def communicate_with_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "communication"
        # Reset talk state so talk_round starts fresh for the new conversation
        self.current_talk_people = None
        self.ask_agent_start_to_talk_to_a_people_sync(action_str, human_object)

        # self.taskmng.process_task(action="process_activity", ask_content=ask_content)

    def ask_agent_start_to_talk_to_a_people_sync(self, objective_to_achieve, human_objective_to_achieve=""):
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        all_people = []
        try:
            all_people = list(self.get_people_list() or [])
        except Exception:
            all_people = []

        filtered_people = []
        try:
            filtered_people = list(self._get_filtered_people_list_for_talk_type("communication") or [])
        except Exception:
            filtered_people = []

        try:
            self._maybe_notify_recommended_excluded_by_talk_type_filter(
                talk_type="communication",
                objective_text=objective_to_achieve,
                all_people=all_people,
                filtered_people=filtered_people,
            )
        except Exception:
            pass

        people_list = filtered_people or all_people
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        self._pending_talk_objective = objective_to_achieve

        role_prompt = get_prompt_by_title("__start_to_talk_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_talk_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        # Memory recall: append past interaction memories for candidate people
        try:
            from backend.apps.sns.memory.memory_config import MemoryConfig
            mm = getattr(self, "memory_manager", None)
            if mm and MemoryConfig.ENABLED:
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
            logger.warning("Memory recall failed for talk people selection: %s", _mem_err)

        self.command_status = "ask_agent_start_to_talk_to_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    async def ask_agent_start_to_talk_to_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        all_people = []
        try:
            all_people = list(self.get_people_list() or [])
        except Exception:
            all_people = []

        filtered_people = []
        try:
            filtered_people = list(self._get_filtered_people_list_for_talk_type("communication") or [])
        except Exception:
            filtered_people = []

        try:
            self._maybe_notify_recommended_excluded_by_talk_type_filter(
                talk_type="communication",
                objective_text=objective_to_achieve,
                all_people=all_people,
                filtered_people=filtered_people,
            )
        except Exception:
            pass

        people_list = filtered_people or all_people
        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
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
            required_keys = ["nation_id", "account", "message", "nick_name"]
            missing = []
            for k in required_keys:
                v = result.get(k, None)
                if not isinstance(v, str) or not v.strip():
                    missing.append(k)
            if missing:
                logger.warning(
                    f"Invalid people selection result in communication. missing={missing} raw={str(content)[:300]}"
                )
                asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))
                return

            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]

            try:
                if hasattr(self, "_is_contact_allowed") and not self._is_contact_allowed("communication", account):
                    retry_state = getattr(self, "_contact_pick_retry", None)
                    if not isinstance(retry_state, dict):
                        retry_state = {}
                    retry_count = int(retry_state.get("communication", 0) or 0)
                    if retry_count < 3:
                        retry_state["communication"] = retry_count + 1
                        self._contact_pick_retry = retry_state
                        try:
                            self._notify_llm_recommended_user_unavailable(account=account, nick_name=nick_name)
                        except Exception:
                            pass
                        objective = (getattr(self, "_pending_talk_objective", "") or "").strip()
                        self.ask_agent_start_to_talk_to_a_people_sync(objective, "")
                        return

                    retry_state["communication"] = 0
                    self._contact_pick_retry = retry_state
                    self.taskmng_js.show_information(
                        lt(
                            "<b>No eligible contacts are available due to anti-harassment rules.</b>",
                            "<b>No eligible contacts are available due to anti-harassment rules.</b>",
                        )
                    )
                    asyncio.create_task(
                        self.taskmng.process_task(
                            action="process_activity",
                            ask_content=self.taskmng.get_current_objective(),
                        )
                    )
                    return
            except Exception:
                pass

            self.current_talk_people = result
            # Explicitly reset talk_round for the new conversation
            result["talk_round"] = 0
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

        # Memory recall: inject past interactions with the current conversation partner
        try:
            from backend.apps.sns.memory.memory_config import MemoryConfig
            mm = getattr(self, "memory_manager", None)
            active = getattr(self, "active_conversation", None) or {}
            acct = (active.get("account") or "").strip()
            name = (active.get("nick_name") or acct)
            if mm and acct and MemoryConfig.ENABLED:
                person_section = mm.get_person_memory_prompt_section(acct, person_name=name, max_results=3, max_chars=600)
                if person_section:
                    question += "\n\n" + person_section
        except Exception as _mem_err:
            logger.warning("Memory recall failed for conversation review: %s", _mem_err)

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
            self.taskmng.add_process_info_to_list(f"After communicating with a friend, got the following: {current_chat_summary}")
            self.write_task_process_to_pane(f"After communicating with a friend, got the following: {current_chat_summary}\n\n")
            try:
                self.taskmng_js.show_information(f"<b>Conversation finished. Summary:</b><br> {current_chat_summary}")
            except Exception:
                pass

            try:
                if hasattr(self, "show_alert_on_map"):
                    self.show_alert_on_map(f"Conversation finished. Summary: {current_chat_summary}", is_error=False)
            except Exception:
                pass

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
