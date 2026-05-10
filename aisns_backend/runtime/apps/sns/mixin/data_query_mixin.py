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

import logging

import re

log = logging.getLogger(__name__)
from db.DBFactory import (query_AgentCfg, add_AIChatMessages, get_prompt_by_title, query_function_mng,
                          add_function_mng, add_map_visit, get_key_value,
                          update_map_trade, add_map_trade, query_single_map_trade, update_AISnsCfg_by_user_id, update_AISnsCfg_map, query_AISnsCfg_map, add_mcp_mng, query_mcp_mng,
                          delete_map_preset_msg, query_map_preset_msg_all, add_map_preset_msg, query_AISnsCfg_map_setting)

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

logger = logging.getLogger(__name__)

class DataQueryMixin:

    def _get_ai_sns_server_base(self):
        try:
            from db.DBFactory import query_SystemCfg
            cfg = query_SystemCfg(is_delete=False)
            v = getattr(cfg, 'ai_sns_server', None)
            v = (v or '').strip()
            return v.rstrip('/') if v else ''
        except Exception:
            return ''

    def get_place_list(self):
        url = f"{self._get_ai_sns_server_base()}/api/get_place_list/"

        pos = self.aisns_cfg_record.current_position
        try:
            lng_val = float(pos[0])
            lat_val = float(pos[1])
            pos_key = f"{round(lng_val, 6)},{round(lat_val, 6)}"
        except Exception:
            pos_key = ""

        try:
            cached_key = getattr(self, "_cached_place_list_pos_key", None)
            cached_value = getattr(self, "_cached_place_list_value", None)
            if pos_key and cached_key == pos_key and cached_value is not None:
                return cached_value
        except Exception:
            pass

        params = {
            "lng": pos[0],
            "lat": pos[1]
        }
        place_list = self.http_request(url, params)

        if isinstance(place_list, list) and pos_key:
            try:
                setattr(self, "_cached_place_list_pos_key", pos_key)
                setattr(self, "_cached_place_list_value", place_list)
            except Exception:
                pass
        return place_list

    def get_people_list(self):
        url = f"{self._get_ai_sns_server_base()}/api/get_people_list/"

        pos = self.aisns_cfg_record.current_position
        try:
            lng_val = float(pos[0])
            lat_val = float(pos[1])
            pos_key = f"{round(lng_val, 6)},{round(lat_val, 6)}"
        except Exception:
            pos_key = ""

        try:
            cached_key = getattr(self, "_cached_people_list_pos_key", None)
            cached_value = getattr(self, "_cached_people_list_value", None)
            if pos_key and cached_key == pos_key and cached_value is not None:
                data = cached_value
            else:
                data = None
        except Exception:
            data = None

        params = {
            "lng": pos[0],
            "lat": pos[1]
        }
        if data is None:
            data = self.http_request(url, params)
            if isinstance(data, list) and pos_key:
                try:
                    setattr(self, "_cached_people_list_pos_key", pos_key)
                    setattr(self, "_cached_people_list_value", data)
                except Exception:
                    pass
        logger.info("loading pesons in get_people_list")
        """
        You can print the full data list here.
        logger.info(data)
        """


        remove_id = ((self.user_map_setting or {}).get("nationid") or "").strip()
        if not remove_id:
            remove_id = ((self.user_map_setting or {}).get("nation_id") or "").strip()

        if not isinstance(data, list):
            return []

        people_list = []
        for item in data:
            if not isinstance(item, dict):
                continue
            nation_id = (item.get("nation_id") or item.get("nationid") or "").strip()
            if remove_id and nation_id == remove_id:
                continue
            people_list.append(item)

        return people_list

    def get_nearest_people_by_profession(self, profession: str, max_distance: Optional[int] = None):
        url = f"{self._get_ai_sns_server_base()}/api/get_nearest_people_by_profession/"
        remove_id = (self.user_map_setting or {}).get("nationid", "")
        params = {
            "profession": profession,
            "exclude_nation_id": remove_id,
            "lng": self.aisns_cfg_record.current_position[0],
            "lat": self.aisns_cfg_record.current_position[1],
        }
        if max_distance is not None:
            params["max_distance"] = max_distance

        data = self.http_request(url, params)
        if not isinstance(data, dict):
            return None
        nation_id = (data.get("nation_id") or "").strip()
        account = (data.get("account") or "").strip()
        nick_name = (data.get("nick_name") or "").strip()
        if not nation_id or not account:
            return None
        return data

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

    def add_friend(self):
        pass

    def get_dict_by_id(self, dict_list, target_id):
        """
        Find and return the dict by target id from a list of dicts.

        :param dict_list: List containing dicts
        :param target_id: Target id string
        :return: Dict for the given id, or None if not found
        """
        # Convert list to map keyed by id for O(1) lookup
        dict_map = {d['id']: d for d in dict_list}

        # Use get() to return target dict; return None if id does not exist
        return dict_map.get(target_id)

    def http_request(self, url, params=None, method="POST"):
        """
        # GET request
        res = http_request("http://example.com/api", {"key": "value"}, method="GET")

        # POST request
        res = http_request("http://example.com/api", {"username": "tom", "password": "123"}, method="POST")

        """
        try:
            method = method.upper()
            if method == "GET":
                response = requests.get(url, params=params)
            elif method == "POST":
                response = requests.post(url, data=params)
            else:
                raise ValueError(f"Unsupported request method: {method}")

            response.raise_for_status()  # Check HTTP status code
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
        except ValueError as json_err:
            print(f"JSON parse error: {json_err}")

        return None

    def save_all_user_data(self):
        data = {
            "current_place": self.current_place,
            "current_position": json.dumps(self.aisns_cfg_record.current_position, ensure_ascii=False),
            "last_position": json.dumps(self.aisns_cfg_record.last_position, ensure_ascii=False),
            "life_point": self.aisns_cfg_record.life_point,
            "energy_point": self.aisns_cfg_record.energy_point,
            "move_point": self.aisns_cfg_record.move_point,
            "exp_point": self.aisns_cfg_record.exp_point,
            "iq_point": self.aisns_cfg_record.iq_point,
            "money": self.aisns_cfg_record.money,
            "credit": self.aisns_cfg_record.credit,
            "level": self.aisns_cfg_record.level,
        }
        update_AISnsCfg_map(**data)

    def load_all_user_data(self):
        record = query_AISnsCfg_map()
        self.current_place = record.current_place

        # Handle current_position, supports multiple formats
        self.aisns_cfg_record.current_position = self._parse_position_data(record.current_position)
        self.aisns_cfg_record.last_position = self._parse_position_data(record.last_position)

        if record.life_point is None:
            self.aisns_cfg_record.life_point = 100
        if record.energy_point is None:
            self.aisns_cfg_record.energy_point = 100
        if record.move_point is None:
            self.aisns_cfg_record.move_point = 100
        if record.exp_point is None:
            self.aisns_cfg_record.exp_point = 0
        if record.iq_point is None:
            self.aisns_cfg_record.iq_point = 60
        if record.money is None:
            self.aisns_cfg_record.money = 1000
        if record.credit is None:
            self.aisns_cfg_record.credit = 0
        if record.level is None:
            self.aisns_cfg_record.level = 1

        if record.route_status == "playing":
            self.move_by_route_flag = True
        else:
            self.move_by_route_flag = False

        user_map_setting = query_AISnsCfg_map_setting()
        self.user_map_setting = user_map_setting


        # Check rebirth condition for existing negative data loaded from DB
        self.check_and_handle_rebirth()

        # Update resource display and charts after all data is loaded
        self.update_resource_display()
        self.update_map_charts()

    def _parse_position_data(self, position_data):
        """
        Parse position data. Supports the following formats:
        1. JSON string: {"lat": 39.51783322503789, "lng": -76.20197639555775}
        2. JSON array: [-76.20197639555775, 39.51783322503789]
        3. Already an array: [lng, lat]
        Returns a normalized numeric array: [lng, lat]
        """
        if not position_data:
            return []

        # If already a list, return directly
        if isinstance(position_data, list):
            # Ensure [lng, lat] format
            if len(position_data) >= 2:
                return [float(position_data[0]), float(position_data[1])]
            else:
                return []

        # If it's a string, try to parse
        if isinstance(position_data, str):
            try:
                # Try parsing as JSON
                parsed_data = json.loads(position_data)

                # Dict format {"lat": ..., "lng": ...}
                if isinstance(parsed_data, dict):
                    lat = float(parsed_data.get("lat", 0))
                    lng = float(parsed_data.get("lng", 0))
                    return [lng, lat]

                # List format [lng, lat] or [lat, lng]
                elif isinstance(parsed_data, list) and len(parsed_data) >= 2:
                    # Assume [lng, lat]
                    return [float(parsed_data[0]), float(parsed_data[1])]

            except json.JSONDecodeError:
                # If not valid JSON, return empty list
                return []

        # Otherwise return empty list
        return []

    def decline_energy(self):

        decline_point = 25
        energy_before = float(self.aisns_cfg_record.energy_point or 0)
        energy_point = energy_before - decline_point
        self.aisns_cfg_record.energy_point = energy_point
        life_point = float(self.aisns_cfg_record.life_point or 0)
        self.aisns_cfg_record.move_point = round(
            100 * (life_point / 100) * (energy_point / 100),
            1,
        )

        try:
            msg = f"⚡Energy: {energy_before:.0f}% -> {float(self.aisns_cfg_record.energy_point or 0):.0f}%"
            if hasattr(self, "show_alert_on_map"):
                self.show_alert_on_map(msg, is_error=True)
            if hasattr(self, "taskmng_js"):
                self.taskmng_js.show_information(f"<b>Energy changed</b><br>{msg}")
        except Exception:
            pass

        # Check rebirth after all calculations are done
        self.check_and_handle_rebirth()

    def decline_life(self):

        decline_point = 25
        life_before = float(self.aisns_cfg_record.life_point or 0)
        life_point = life_before - decline_point
        self.aisns_cfg_record.life_point = life_point
        energy_point = float(self.aisns_cfg_record.energy_point or 0)
        self.aisns_cfg_record.move_point = round(
            100 * (life_point / 100) * (energy_point / 100),
            1,
        )

        try:
            msg = f"❤️Life: {life_before:.0f}% -> {float(self.aisns_cfg_record.life_point or 0):.0f}%"
            if hasattr(self, "show_alert_on_map"):
                self.show_alert_on_map(msg, is_error=True)
            if hasattr(self, "taskmng_js"):
                self.taskmng_js.show_information(f"<b>Life changed</b><br>{msg}")
        except Exception:
            pass

        # Check rebirth after all calculations are done
        self.check_and_handle_rebirth()
