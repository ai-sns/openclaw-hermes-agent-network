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

logger = logging.getLogger(__name__)


class MapMovementMixin:

    def _finish_route_and_switch_to_free_mode(self) -> None:
        try:
            self.move_by_route_flag = False
            self.route_total_distance = 0
            self.route_move_distance = 0
            self.route_target_place = ""
            self.route_target_position = None
            self.route_position_list = []
        except Exception:
            self.move_by_route_flag = False

        try:
            update_AiChatCfg_map(
                route_status="stopped",
                route_start="",
                route_end="",
                route_current_position="",
                route="",
            )
        except Exception as e:
            logger.warning(f"Failed to persist route reset to database: {e}")

        try:
            command = ("route_mode_free", "", "")
            self.send_msg_to_map(command)
        except Exception as e:
            logger.warning(f"Failed to notify frontend to switch to Free mode: {e}")

    def _get_ai_sns_server_base(self):
        try:
            from db.DBFactory import query_SystemCfg
            cfg = query_SystemCfg(is_delete=False)
            v = getattr(cfg, 'ai_sns_server', None)
            v = (v or '').strip()
            return v.rstrip('/') if v else ''
        except Exception:
            return ''

    def go_around(self):
        radius = 500  # Radius (meters)
        # Initialize current and last position
        current_position = Point(self.aichatcfg_record.current_position[1], self.aichatcfg_record.current_position[0])
        last_position = Point(self.aichatcfg_record.last_position[1], self.aichatcfg_record.last_position[0])

        # If positions are the same, skip quadrant exclusion
        if current_position == last_position:
            excluded_quadrant = None
        else:
            # Determine the quadrant of last_position relative to current_position
            last_lon_diff = last_position.longitude - current_position.longitude
            last_lat_diff = last_position.latitude - current_position.latitude

            # Determine excluded quadrant based on diffs
            if last_lon_diff > 0 and last_lat_diff > 0:
                excluded_quadrant = 1  # Quadrant I
            elif last_lon_diff < 0 and last_lat_diff > 0:
                excluded_quadrant = 2  # Quadrant II
            elif last_lon_diff < 0 and last_lat_diff < 0:
                excluded_quadrant = 3  # Quadrant III
            else:
                excluded_quadrant = 4  # Quadrant IV

        def generate_random_point(excluded_quadrant):
            while True:
                bearing = random.uniform(0, 360)
                candidate_position = distance(meters=radius).destination(current_position, bearing)

                if abs(candidate_position.latitude) >= 90:
                    candidate_position = Point(89.999 if candidate_position.latitude > 0 else -89.999,
                                               current_position.longitude)

                candidate_position = Point(candidate_position.latitude,
                                           (candidate_position.longitude + 180) % 360 - 180)

                if excluded_quadrant is None:  # Skip quadrant exclusion
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

        result = f"You moved 500 meters."
        self.update_after_moving()
        return result

    def initial_bearing(self, p1: Point, p2: Point) -> float:
        """
        Calculate the initial bearing from p1 to p2 (degrees, 0-360).
        """
        lon1, lat1 = math.radians(p1.longitude), math.radians(p1.latitude)
        lon2, lat2 = math.radians(p2.longitude), math.radians(p2.latitude)
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360

    def move_ahead(self, current_position, target_position, target_place):
        move_distance = 500  # Move distance (meters)

        # Convert to geopy.Point (Point takes lat, lon)
        if not isinstance(current_position, Point):
            current_position = Point(current_position[1], current_position[0])

        if not isinstance(target_position, Point):
            target_position = Point(target_position[1], target_position[0])

            # Calculate actual distance
        actual_distance = distance(current_position, target_position).m

        try:
            # Case 1: Already at target (zero distance)
            if actual_distance == 0:
                self.aichatcfg_record.last_position = self.aichatcfg_record.current_position
                self.aichatcfg_record.current_position = [current_position.longitude, current_position.latitude]
                self.target_position = None
                return f"You are already at the destination {target_place}."

            # Case 2: Remaining distance less than one step
            if actual_distance <= move_distance:
                self.aichatcfg_record.last_position = self.aichatcfg_record.current_position
                self.aichatcfg_record.current_position = [target_position.longitude, target_position.latitude]
                new_pos = self.aichatcfg_record.current_position
                command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
                self.send_msg_to_map(command)
                self.target_position = None
                return f"You have arrived at the destination {target_place} (remaining 0 km)."

                # Case 3: Need to compute bearing

            if abs(current_position.latitude) == 90:
                # Pole: direction not unique -> default towards equator
                bearing = 180 if current_position.latitude > 0 else 0
            else:
                inv = Geodesic.WGS84.Inverse(
                    current_position.latitude, current_position.longitude,
                    target_position.latitude, target_position.longitude
                )
                bearing = inv['azi1'] % 360

            # Move move_distance along that bearing
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

            # Recalculate remaining distance
            remaining_distance = distance(next_position, target_position).km

            self.update_after_moving()

            return f"You moved {move_distance} meters toward {target_place}. Remaining distance: {remaining_distance:.2f} km."


        except Exception as e:
            return f"Error while calculating movement coordinates: {str(e)}"

    def move_by_route(self):
        target_place = getattr(self, "route_target_place", "")
        total_distance = float(getattr(self, "route_total_distance", 0) or 0)
        moved_distance = float(getattr(self, "route_move_distance", 0) or 0)

        remaining_distance = total_distance - moved_distance
        if remaining_distance < 0:
            remaining_distance = 0

        if remaining_distance <= 1e-9:
            self._finish_route_and_switch_to_free_mode()
            return f"Arrived at destination '{target_place}'. Switched to Free mode."

        command = ("route_move_action", "", "")
        self.send_msg_to_map(command)
        return f"You moved {moved_distance} meters toward {target_place}. Remaining distance: {remaining_distance:.2f} km."

    def update_after_moving(self):
        lng = self.aichatcfg_record.current_position[0]
        lat = self.aichatcfg_record.current_position[1]
        url = f"{self._get_ai_sns_server_base()}/api/update-location/"
        params = {
            "nation_id": "AI123451234567890ABCDEF7890",
            "password": "securePassword123!",
            "longitude": lng,
            "latitude": lat,
        }
        response = requests.post(url, data=params)
        print(response)
