from sqlalchemy.orm import Session
from backend.database.models.chat import AiChatCfg, AIFriend, AIChatMessages
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
from datetime import datetime

from backend.apps.sns.message_formatter import format_internal_xmpp_message_for_storage

logger = logging.getLogger(__name__)



class XmppMixin:

    async def receiveMessage(self, event):
        """
        Receive and process XMPP messages.

        Args:
            event: XMPP message event, contains 'body' and 'from' fields
        """
        if event is None:
            logger.warning("Received None event in receiveMessage")
            return

        try:
            # Extract content and sender
            content = event.get('body', '')
            from_str = str(event.get('from', ''))

            if not content or not from_str:
                logger.warning(f"Invalid message event: content={content}, from={from_str}")
                return

            logger.info(f"Received message from {from_str}: {content[:50]}...")

            # Default message processing flow
            await self.handle_receiveMessage(content, from_str)

        except KeyError as e:
            logger.error(f"Missing required field in message event: {e}")
        except Exception as e:
            logger.error(f"Error in receiveMessage: {e}", exc_info=True)

    async def handle_receiveMessage(self, content, from_str):
        """
        Handle received XMPP message content.

        Args:
            content: Message content
            from_str: Sender JID
        """
        try:
            logger.info(f"Processing message from {from_str}, content length: {len(content)}")

            # Check map_mode; only process in org mode
            if self.map_mode != 'org':
                logger.debug(f"Skipping message processing, map_mode is '{self.map_mode}' (not 'org')")
                return

            # Extract account info
            account = from_str.split('/')[0]
            logger.debug(f"Extracted account: {account}")

            active_account = ""
            try:
                active = getattr(self, "active_conversation", None) or {}
                active_account = (active.get("account") or "").strip()
            except Exception:
                active_account = ""

            # Send chat message to UI
            try:
                self.send_talk_message(account, self.ai_chat_cfg.account, content)
            except Exception as e:
                logger.error(f"Failed to send talk message to UI: {e}")

            # Manage chat history
            if account not in self.talk_history:
                self.talk_history[account] = []
                logger.debug(f"Created new talk history for account: {account}")

            self.talk_history[account].append("Friend:" + content)

            is_active_peer = bool(active_account) and active_account == account
            if is_active_peer:
                self.current_talk_history.append("Friend:" + content)
                try:
                    if hasattr(self, "_touch_conversation_activity"):
                        self._touch_conversation_activity(account)
                except Exception as e:
                    logger.error(f"Failed to touch conversation activity: {e}")
            else:
                try:
                    if hasattr(self, "enqueue_inbox_message"):
                        self.enqueue_inbox_message(account, content)
                except Exception as e:
                    logger.error(f"Failed to enqueue inbox message: {e}")

            logger.debug(f"Updated talk history for {account}, total messages: {len(self.talk_history[account])}")

            # Message type routing - use walrus operator for conditional checks
            message_handled = False

            if (pay_received_str := self.check_pay_in_received(content)):
                logger.info(f"Detected payment received from {account}")
                self.handle_pay_received(pay_received_str)
                message_handled = True

            elif (good_received_str := self.check_good_in_received(content)):
                logger.info(f"Detected goods received from {account}")
                self.handle_good_received(good_received_str)
                message_handled = True

            else:
                # Check whether this is a buy inquiry (someone initiates a purchase request)
                if (buy_flag := self.check_buy_in_received(content)):
                    logger.info(f"Detected buy inquiry from {account}")
                    if is_active_peer or not active_account:
                        self.talk_type = "sell"
                    else:
                        pending = getattr(self, "_pending_peer_talk_type", None)
                        if pending is None or not isinstance(pending, dict):
                            pending = {}
                            setattr(self, "_pending_peer_talk_type", pending)
                        pending[account] = "sell"
                        logger.info(
                            "Recorded pending inquiry intent from %s (active_conversation=%s)",
                            account,
                            active_account,
                        )
                else:
                    logger.debug(f"Processing as general conversation message from {account}")

                if is_active_peer or not active_account:
                    # Process general conversation message only for active peer (or when no active session).
                    if self.human_take_over:
                        logger.info(
                            "Human takeover is enabled, skipping automated conversation review for %s",
                            account,
                        )
                    else:
                        asyncio.create_task(self.taskmng.process_task(
                            event="conversation_message_received",
                            talk_history_str=json.dumps(self.current_talk_history, ensure_ascii=False)
                        ))
                else:
                    logger.info(
                        "Message from %s queued to inbox because active conversation is with %s",
                        account,
                        active_account,
                    )
                message_handled = True

            # Save current received message
            self.current_received_msg = content

            # Check human takeover flag
            if not self.human_take_over:
                logger.debug("Human takeover is disabled, continuing automated processing")
            else:
                logger.info("Human takeover is enabled")

            logger.info(f"Message processing completed for {account}, handled: {message_handled}")

        except Exception as e:
            logger.error(f"Error in handle_receiveMessage: {e}", exc_info=True)
            # Save message content even if an error occurs
            try:
                self.current_received_msg = content
            except:
                pass


    def send_xmpp_message(self, to_jid: str, content: str) -> bool:
        """
        Send XMPP message via XMPPClientManager.

        Args:
            to_jid: Receiver JID
            content: Message content

        Returns:
            bool: True on success, False on failure
        """
        try:
            client = self.xmpp_manager.get_client()
            if not client or not client.is_client_connected():
                logger.error("XMPP client not connected")
                return False

            client.send_message_to_jid(to_jid, content)
            logger.debug(f"XMPP message sent to {to_jid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send XMPP message to {to_jid}: {e}")
            return False

    def sendMessage(self, content, by_click=False, to_jid=None, to_name=None, back_ground=False):
        """
        Send XMPP message.

        Args:
            content: Message content
            by_click: Whether triggered by click (default: False)
            to_jid: Receiver JID (default: None; read from current_talk_people)
            to_name: Receiver name (default: None; read from current_talk_people)
            back_ground: Whether to send in background (default: False)

        Returns:
            bool: True on success, False on failure
        """
        if not to_jid:
            if self.current_talk_people:
                current_talk_people = self.current_talk_people
                to_jid = current_talk_people["account"]
                to_name = current_talk_people["nick_name"]
            else:
                return
        try:
            # Validate message content
            if not content:
                logger.warning("Cannot send empty message")
                return False

            to_jid = (to_jid or "").strip()
            if (not to_jid) or ("@" not in to_jid):
                logger.warning("Refusing to send message to invalid XMPP account: %s", to_jid)
                return False

            # Resolve recipient info
            recipient = self._resolve_recipient(to_jid, to_name)
            if not recipient:
                return False

            to_jid = recipient['jid']
            to_name = recipient['name']

            logger.info(f"Sending message to {to_jid}: {content[:50]}...")
            stored_content = format_internal_xmpp_message_for_storage(content)
            self._save_message_to_database(stored_content, to_jid, to_name)

            # Send XMPP message
            if not self.send_xmpp_message(to_jid, content):
                logger.error(f"Failed to send XMPP message to {to_jid}")
                return False

            # Update UI (if not background)
            if not back_ground:
                self._update_ui_with_sent_message(to_jid, stored_content)

            try:
                if by_click and bool(getattr(self, "human_take_over", False)):
                    try:
                        if to_jid not in self.talk_history:
                            self.talk_history[to_jid] = []
                        self.talk_history[to_jid].append("Me:" + content)
                    except Exception:
                        pass

                    active_account = ""
                    try:
                        active = getattr(self, "active_conversation", None) or {}
                        active_account = (active.get("account") or "").strip()
                    except Exception:
                        active_account = ""

                    if bool(active_account) and active_account == to_jid:
                        try:
                            self.current_talk_history.append("Me:" + content)
                        except Exception:
                            pass
                        try:
                            if hasattr(self, "_touch_conversation_activity"):
                                self._touch_conversation_activity(to_jid)
                        except Exception:
                            pass
            except Exception:
                pass

            logger.info(f"Message sent successfully to {to_jid}")
            return True

        except Exception as e:
            logger.error(f"Error in sendMessage: {e}", exc_info=True)
            return False

    def _resolve_recipient(self, to_jid=None, to_name=None):
        """
        Resolve recipient info.

        Args:
            to_jid: Receiver JID
            to_name: Receiver name

        Returns:
            dict: Dict containing jid and name; returns None on failure
        """
        if to_jid:
            return {'jid': to_jid, 'name': to_name}

        if self.current_talk_people:
            current_talk_people = self.current_talk_people
            jid = current_talk_people.get("account")
            name = current_talk_people.get("nick_name")
            logger.debug(f"Resolved recipient from current_talk_people: {jid}")
            return {'jid': jid, 'name': name}

        logger.warning("No recipient specified and no current_talk_people available")
        return None

    def _save_message_to_database(self, content, to_jid, to_name):
        """
        Save message to database.

        Args:
            content: Message content
            to_jid: Receiver JID
            to_name: Receiver name
        """
        try:
            from db.write_queue import db_write

            owner_account = (getattr(self.ai_chat_cfg, "account", "") or "").strip()
            owner_name = getattr(self.ai_chat_cfg, "name", "") or owner_account
            conversation_id = getattr(self, "conversation_id", "") or f"{owner_account}_{to_jid}"
            _to_jid = (to_jid or "").strip()
            _to_name = (to_name or "").strip() or _to_jid
            _stored_content = content

            def _save_all(session):
                friend = session.query(AIFriend).filter(
                    AIFriend.is_delete == False,
                    AIFriend.owner_sns_account == owner_account,
                    AIFriend.account == _to_jid,
                ).first()
                if friend:
                    if not friend.nick_name:
                        friend.nick_name = _to_name or _to_jid
                else:
                    friend = AIFriend(
                        account=_to_jid,
                        nick_name=(_to_name or _to_jid),
                        groups="",
                        owner_sns_account=owner_account,
                        subscription="none",
                        new_message_flag=False,
                        last_message_time=datetime.now(),
                    )
                    session.add(friend)

                message = AIChatMessages(
                    conversation_id=conversation_id,
                    flag=0,
                    content=_stored_content,
                    owner_account=owner_account,
                    friend_account=_to_jid,
                    owner_name=owner_name,
                    friend_name=_to_name,
                )
                session.add(message)
                session.flush()

                friend.new_message_flag = False
                friend.last_message_time = datetime.now()

                contact_payload = {
                    'account': friend.account,
                    'nick_name': friend.nick_name or friend.account,
                    'new_message_flag': bool(friend.new_message_flag),
                    'last_message_time': friend.last_message_time.isoformat() if friend.last_message_time else None,
                }
                msg_payload = {
                    'id': message.id,
                    'from_account': _to_jid,
                    'content': message.content,
                    'flag': 0,
                    'create_time': message.create_time.isoformat() if message.create_time else None,
                    'contact': contact_payload,
                }

                return {
                    'contact': contact_payload,
                    'message': msg_payload,
                }

            result = db_write(_save_all, description="xmpp_mixin_save_outgoing")
            contact_payload = (result or {}).get('contact')
            msg_payload = (result or {}).get('message')

            if contact_payload:
                asyncio.create_task(websocket_manager.broadcast({
                    'type': 'contact_upserted',
                    'data': contact_payload
                }))

            if msg_payload:
                asyncio.create_task(websocket_manager.broadcast({
                    'type': 'new_message',
                    'data': msg_payload,
                }))

            logger.debug(f"Message saved to database for conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")

    def _update_ui_with_sent_message(self, to_jid, content):
        """
        Update UI to display sent message.

        Args:
            to_jid: Receiver JID
            content: Message content
        """
        if self.map_mode != 'org':
            logger.debug(f"Skipping UI update, map_mode is '{self.map_mode}' (not 'org')")
            return

        try:
            self.send_talk_message(self.ai_chat_cfg.account, to_jid, content)
            logger.debug(f"UI updated with sent message to {to_jid}")
        except Exception as e:
            logger.error(f"Failed to update UI with sent message: {e}")
