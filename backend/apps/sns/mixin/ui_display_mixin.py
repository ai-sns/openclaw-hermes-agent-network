from sqlalchemy.orm import Session
from backend.database.models.chat import AiChatCfg
from backend.apps.sns.map_task_manager import MapTaskManager
from backend.apps.sns.js_task_manager import JsTaskManager
from backend.apps.sns.xmpp_client import XMPPClientManager
from backend.modules.agent.agent_manager import agent_manager
from backend.shared.websocket_manager import manager as websocket_manager
from backend.apps.sns.message_formatter import format_internal_xmpp_message_for_storage

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

logger = logging.getLogger(__name__)

class UIDisplayMixin:


    def write_on_going_process_to_pane(self, new_ongoing_content: str):
        # Define markers
        self.current_ongoing_content = new_ongoing_content
        # Get ongoing process and task process history content
        ongoing_process = self.get_on_going_process()
        task_process_history = self.get_task_process_history()

        # Merge content and update plan_edit
        combined_content = f"{ongoing_process}\n{task_process_history}"

        # Send to the frontend Process tab (On Going section)
        asyncio.create_task(self._send_to_frontend('process', ongoing_process, section='ongoing'))

        # self.plan_edit.setPlainText(combined_content)
        print("write_on_going_process_to_pane")

    def get_on_going_process(self):
        """
        Return formatted ongoing process text (plain text).
        """
        # Get base info
        profession = self.aichatcfg_record.profession
        lng = f"{self.aichatcfg_record.current_position[0]}" if self.aichatcfg_record.current_position and len(self.aichatcfg_record.current_position) >= 2 else "0"
        lat = f"{self.aichatcfg_record.current_position[1]}" if self.aichatcfg_record.current_position and len(self.aichatcfg_record.current_position) >= 2 else "0"

        # Build formatted text
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

    async def _send_to_frontend(self, tab_type, content, section=None):
        """
        Send content to the specified frontend tab.

        Args:
            tab_type: Tab type ('think' or 'process')
            content: Content to send
            section: Optional section identifier ('ongoing' or 'history')
        """
        try:
            message = {
                "type": "sns_update",
                "tab": tab_type,
                "content": content
            }
            if section:
                message["section"] = section
            # Broadcast to all connected clients
            await websocket_manager.broadcast(message)
            logger.info(f"Sent {tab_type} update to frontend (section: {section})")
        except Exception as e:
            logger.error(f"Failed to send to frontend: {e}")

    def write_thinking_process_to_pane(self, title, content):
        # Assume self.thinking_edit is an instance of QTextEdit
        self.thinking_step_index += 1

        # Compose new content
        new_content = f"\n🔶【{self.thinking_step_index}】{title}\n"
        new_content += f"━━━━━━━━━━━━━━━━━━\n"
        new_content += f"{content}\n"

        # Send to the frontend Think tab
        asyncio.create_task(self._send_to_frontend('think', new_content))

        # self.thinking_edit.append(new_content)

    def write_task_process_to_pane(self, content=""):
        # Get ongoing process and task process history content
        ongoing_process = self.get_on_going_process()
        task_process_history = self.get_task_process_history()

        # Merge content and update plan_edit
        combined_content = f"{ongoing_process}\n{task_process_history}"

        # Send to the frontend Process tab
        asyncio.create_task(self._send_to_frontend('process', combined_content))

        # self.plan_edit.setPlainText(combined_content)
        print("write_task_process_to_pane")

    def write_process_history_to_pane(self):
        task_process_history = self.get_task_process_history()
        lines = (task_process_history or "").split("\n")
        if len(lines) >= 2 and ("📜 Process history" in lines[0]) and ("━" in lines[1]):
            history_body = "\n".join(lines[2:]).strip()
        else:
            history_body = (task_process_history or "").strip()
        asyncio.create_task(self._send_to_frontend('process', history_body, section='history'))


    def get_ai_model_display_name(self):
        """
        Get the AI model display name, formatted as "🧠 {provider} {model_name}".
        """
        try:
            from db.DBFactory import query_AgentCfg

            # Get account info
            snsaccount = self.aichatcfg_record.account
            agent_cfg = query_AgentCfg(snsaccount=snsaccount)

            # Get default model
            if agent_cfg and agent_cfg.defaultmodel:
                defaultmodel = agent_cfg.defaultmodel
                return f"🧠 {defaultmodel}"
            else:
                return "🧠 OpenAI gpt-4o-mini"  # Default
        except Exception as e:
            print(f"Error while getting AI model name: {e}")
            return "🧠 OpenAI gpt-4o-mini"  # Default on error

    def update_resource_display(self):
        """
        Update resource display content, including tool list, people list, and place list.
        """
        # Get resource data
        service_list = self.get_service_list()
        people_list = self.get_people_list()
        place_list = self.get_place_list()

        # Format content
        formatted_content = self._format_resource_content(service_list, people_list, place_list)+"\n"

        # Send to the frontend Resource tab
        import asyncio
        asyncio.create_task(self._send_to_frontend('resource', formatted_content))

    def _format_resource_content(self, service_list, people_list, place_list):
        """
        Format resource content for display.
        """
        content = ""

        def _format_coord(value, decimals: int = 8) -> str:
            try:
                num = float(value)
            except Exception:
                return str(value)

            s = f"{num:.{decimals}f}".rstrip('0').rstrip('.')
            if s == "-0":
                s = "0"
            return s

        # Format tool list
        if service_list:
            content += f"☁️ Services List (total {len(service_list)} items)\n"
            content += "══════════════════════════\n\n"

            for i, service in enumerate(service_list):
                # Tool ID and name
                content += f"🌐 #{i+1} {service.get('name', '')}\n"


                # Geo coordinates (if lng/lat are present and non-zero)
                lng = service.get('lng', 0)
                lat = service.get('lat', 0)
                if lng and lat and lng != 0 and lat != 0:
                    formatted_lng = _format_coord(lng, 8)
                    formatted_lat = _format_coord(lat, 8)
                    content += f"📍  {formatted_lng}, {formatted_lat}\n"
                elif 'place' in service and service['place']:
                    content += f"🌍  {service['place']}\n"

                # Description
                if 'description' in service and service['description']:
                    content += f"💬 Description: {service['description']}\n"

                # Address
                if 'address' in service and service['address'] and service['address'] != "Not needed":
                    content += f"🔗 Address: {service['address']}\n"

                # Type and method
                type_info = service.get('type', '')
                method_info = service.get('method', '')

                # Params
                param_info = ""
                if 'parameter' in service and service['parameter']:
                    if isinstance(service['parameter'], dict):
                        param_strs = [f"{k}={v}" for k, v in service['parameter'].items()]
                        param_info = f"({', '.join(param_strs)})" if param_strs else ""
                    else:
                        param_info = f"({service['parameter']})" if service['parameter'] != "None" else ""

                content += f"⚙️ Type: {type_info} ｜ Method: {method_info}{param_info}\n"

                # Separator line (except for the last tool)
                if i < len(service_list) - 1:
                    content += "\n──────────────────────────\n\n"

            content += "\n\n"

        # Format people list
        if people_list:
            content += f"🧑‍🤝‍🧑 People List (total {len(people_list)} people)\n"
            content += "══════════════════════════\n"

            for i, person in enumerate(people_list):
                # Name and profession
                nick_name = person.get('nick_name', '')
                profession = person.get('profession', '')
                content += f"🧑‍ #{i+1} {nick_name} ｜ 👩‍💻 {profession}\n"

                # Location
                location = person.get('location', [])
                if location and len(location) >= 2:
                    lng, lat = location[0], location[1]
                    formatted_lng = _format_coord(lng, 8)
                    formatted_lat = _format_coord(lat, 8)
                    content += f"📍  {formatted_lng}, {formatted_lat}\n"

                # Account
                account = person.get('account', '')
                if account:
                    content += f"💬 account: {account}\n"

                # SNS
                sns_url = person.get('sns_url', '')
                if sns_url:
                    content += f"🔗 sns: {sns_url}\n"

                # ID
                nation_id = person.get('nation_id', '')
                if nation_id:
                    content += f"🆔 nation_id: {nation_id}\n"

                # Profile
                profile = person.get('profile', '')
                if profile:
                    content += f"📝 profile: {profile}\n"

                # Separator line (except for the last person)
                if i < len(people_list) - 1:
                    content += "\n──────────────────────────\n\n"

            content += "\n\n"

        # Format place list
        if place_list:
            content += f"🗺️ Place List (total {len(place_list)} places)\n"
            content += "══════════════════════════\n"

            for i, place in enumerate(place_list):
                # Place name
                place_name = place.get('place_name', '')
                content += f"🏞️ #{i+1} {place_name}\n"

                # Coordinates
                position = place.get('place_position', [])
                if position and len(position) >= 2:
                    lng, lat = position[0], position[1]
                    formatted_lng = _format_coord(lng, 8)
                    formatted_lat = _format_coord(lat, 8)
                    content += f"📍 {formatted_lng}, {formatted_lat}\n"

                # Description
                description = place.get('description', '')
                if description:
                    content += f"📖 {description}\n"

                url = (place.get('url', '') or place.get('place_url', '') or '').strip()
                if url:
                    content += f"🔗 {url}\n"

                # Separator line (except for the last place)
                if i < len(place_list) - 1:
                    content += "\n──────────────────────────\n\n"

            content += "\n"

        return content.strip()

    def send_command_to_map(self, command, param_1, param_2):
        """
        Send a command to the map system.

        Args:
            command: Command type
            param_1: Param 1
            param_2: Param 2
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        import logging

        logger = logging.getLogger(__name__)

        # Build message
        message = {
            "type": "command",
            "command": command,
            "param_1": param_1,
            "param_2": param_2
        }

        # Send to frontend asynchronously
        async def send_message():
            try:
                await websocket_manager.broadcast(message)
                logger.info(f"Command sent to map: {command}, param_1={param_1}, param_2={param_2}")
            except Exception as e:
                logger.error(f"Failed to send command to map: {e}")

        asyncio.create_task(send_message())

    def send_talk_message(self, fromuser, touser, message):
        """
        Send chat messages to the frontend map.

        Args:
            fromuser: Sender account
            touser: Receiver account
            message: Message content
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)

        try:
            message = format_internal_xmpp_message_for_storage(message)
        except Exception:
            pass


        # Build map message (new format)
        map_msg = {
            "type": "map_chat_message",
            "from_user": fromuser,
            "to_user": touser,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }

        # Send both formats to frontend asynchronously
        async def send_messages():
            try:
                # Send to map
                await websocket_manager.broadcast(map_msg)
                logger.info(f"Chat messages sent from {fromuser} to {touser}: {message}")
            except Exception as e:
                logger.error(f"Failed to send chat messages: {e}")

        asyncio.create_task(send_messages())

    def show_status_on_map(self, status):
        """
        Show status information on the map.

        Args:
            status: Status string
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        import logging

        logger = logging.getLogger(__name__)

        # Build message
        msg = {
            "type": "status_update",
            "status": status
        }

        # Send to frontend asynchronously
        async def send_message():
            try:
                await websocket_manager.broadcast(msg)
                logger.info(f"Status update sent: {status}")
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")

        asyncio.create_task(send_message())

    def show_alert_on_map(self, message, is_error=False):
        """
        Show warning/info messages on the map.

        Args:
            message: Warning/info message
            is_error: Whether this is an error message (default: False)
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        import logging

        logger = logging.getLogger(__name__)

        # Build message
        is_error = False # set is_error = False，make the alert close after 1.5 sec
        msg = {
            "type": "alert",
            "message": message,
            "is_error": is_error
        }

        # Send to frontend asynchronously
        async def send_message():
            try:
                await websocket_manager.broadcast(msg)
                logger.info(f"Alert sent: {message} (is_error={is_error})")
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

        asyncio.create_task(send_message())



    def send_msg_to_map(self, command):
        """
        Send a command to the map system.
        """
        action, param_1, param_2 = command
        if action == "Use skills":
            print(f"Executing skill: {param_1}")

            self.send_command_to_map(action, param_1, param_2)
        else:
            print(f"Executing action: {action}")

            self.send_command_to_map(action, param_1, param_2)

    def update_map_charts(self):
        """
        Update map chart data and send to frontend.
        Called when user attributes (e.g., IQ, energy, life, etc.) change.
        """
        import asyncio

        # Prepare radar chart data
        radar_data = [
            self.aichatcfg_record.iq_point,
            self.aichatcfg_record.energy_point,
            self.aichatcfg_record.life_point,
            self.aichatcfg_record.move_point,
            self.aichatcfg_record.exp_point
        ]
        radar_categories = [
            f'{lt("IQ", "IQ")}:{self.aichatcfg_record.iq_point}',
            f'{lt("Energy", "Energy")}:{self.aichatcfg_record.energy_point}',
            f'{lt("Life", "Life")}:{self.aichatcfg_record.life_point}',
            f'{lt("Move", "Move")}:{self.aichatcfg_record.move_point}',
            f'{lt("Exp", "Exp")}:{self.aichatcfg_record.exp_point}'
        ]

        # Prepare bar chart data
        formatted_number = f"{self.aichatcfg_record.money:,.2f}"
        bar_indicators = [
            f'{lt("Money", "Money")}:{formatted_number}',
            f'{lt("Credit", "Credit")}:{self.aichatcfg_record.credit}',
            f'{lt("Level", "Level")}{self.aichatcfg_record.level}'
        ]
        bar_values = [100, self.aichatcfg_record.credit, self.aichatcfg_record.level * 10]
        bar_colors = ['#ffb676', '#c3f1d7', '#99d4ff']

        # Build user stats object (use explicit None checks to avoid 0 being treated as falsy)
        rebirth_count = getattr(self, '_rebirth_count', 0)
        user_stats = {
            "rebirth": rebirth_count,
            "level": int(self.aichatcfg_record.level) if self.aichatcfg_record.level is not None else 3,
            "credit": int(self.aichatcfg_record.credit) if self.aichatcfg_record.credit is not None else 0,
            "money": float(self.aichatcfg_record.money) if self.aichatcfg_record.money is not None else 0.0,
            "life": int(self.aichatcfg_record.life_point) if self.aichatcfg_record.life_point is not None else 100,
            "iq": int(self.aichatcfg_record.iq_point) if self.aichatcfg_record.iq_point is not None else 100,
            "energy": int(self.aichatcfg_record.energy_point) if self.aichatcfg_record.energy_point is not None else 100,
            "move": float(self.aichatcfg_record.move_point) if self.aichatcfg_record.move_point is not None else 100.0,
            "exp": int(self.aichatcfg_record.exp_point) if self.aichatcfg_record.exp_point is not None else 0
        }

        # Send updates to frontend via WebSocket
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_chart_update(user_stats))
        except RuntimeError:
            # Called from a sync context without a running event loop
            asyncio.run(self._send_chart_update(user_stats))

        logger.info(f"Chart data updated and sent to frontend: {user_stats}")

    async def _send_chart_update(self, user_stats: dict):
        """
        Send chart update data to the frontend.

        Args:
            user_stats: User stats dictionary
        """
        try:
            message = {
                "type": "user_stats_update",
                "data": user_stats
            }
            await websocket_manager.broadcast(message)
            logger.info(f"User stats update sent to frontend")
        except Exception as e:
            logger.error(f"Failed to send chart update: {e}")
