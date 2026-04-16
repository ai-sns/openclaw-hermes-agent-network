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

logger = logging.getLogger(__name__)


class MapMovementMixin:

    def _calc_allowed_distance_m(self, base_distance_m: int = 500) -> int:
        try:
            move_point = float(getattr(self.aichatcfg_record, "move_point", 0) or 0)
        except Exception:
            move_point = 0.0

        if move_point <= 0:
            return 0

        if move_point > 100:
            move_point = 100.0

        try:
            allowed = int(round(float(base_distance_m) * (move_point / 100.0)))
        except Exception:
            allowed = 0

        return max(0, allowed)

    @staticmethod
    def _haversine_distance_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)
        a = (
            math.sin(dphi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2)
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def _parse_route_points(self, raw: object) -> List[Dict[str, float]]:
        if not raw:
            return []

        parsed = raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except Exception:
                return []

        if isinstance(parsed, dict):
            parsed = parsed.get("points")

        if not isinstance(parsed, list):
            return []

        points: List[Dict[str, float]] = []
        for p in parsed:
            if not isinstance(p, dict):
                continue
            try:
                lng = float(p.get("lng"))
                lat = float(p.get("lat"))
            except Exception:
                continue
            if not (-180.0 <= lng <= 180.0 and -90.0 <= lat <= 90.0):
                continue
            points.append({"lng": lng, "lat": lat})

        return points

    def _compute_route_total_distance_m(self, points: List[Dict[str, float]]) -> float:
        if not points or len(points) < 2:
            return 0.0

        total = 0.0
        for i in range(1, len(points)):
            p1 = points[i - 1]
            p2 = points[i]
            try:
                total += self._haversine_distance_m(p1["lng"], p1["lat"], p2["lng"], p2["lat"])
            except Exception:
                continue

        return float(total)

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
        radius = self._calc_allowed_distance_m()  # Radius (meters)
        if radius <= 0:
            return "Move is blocked because move_point is 0."

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

        try:
            moved_m = int(round(distance(current_position, target_position).m))
        except Exception:
            moved_m = int(radius)
        result = f"You moved {moved_m} meters."
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
        move_distance = self._calc_allowed_distance_m()  # Move distance (meters)
        if move_distance <= 0:
            return "Move is blocked because move_point is 0."

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

        allowed_step_m = self._calc_allowed_distance_m()
        if allowed_step_m <= 0:
            return "Move is blocked because move_point is 0."

        cfg = None
        try:
            cfg = query_AiChatCfg_map()
        except Exception:
            cfg = None

        points: List[Dict[str, float]] = []
        route_distance_m = 0.0
        if cfg is not None:
            try:
                points = self._parse_route_points(getattr(cfg, "route_points", None))
            except Exception:
                points = []
            try:
                route_distance_m = float(getattr(cfg, "route", 0) or 0)
            except Exception:
                route_distance_m = 0.0

        total_distance_m = self._compute_route_total_distance_m(points)
        if total_distance_m <= 0:
            total_distance_m = float(getattr(self, "route_total_distance", 0) or 0)

        if total_distance_m > 10.0 and 0.0 <= route_distance_m <= 1.0:
            route_distance_m = float(route_distance_m) * float(total_distance_m)

        remaining_distance_m = max(0.0, float(total_distance_m) - float(route_distance_m))

        if remaining_distance_m < 1.0:
            self._finish_route_and_switch_to_free_mode()
            return f"Arrived at destination '{target_place}'. Switched to Free mode."

        step_m = min(int(allowed_step_m), int(math.floor(remaining_distance_m)))
        if step_m <= 0:
            self._finish_route_and_switch_to_free_mode()
            return f"Arrived at destination '{target_place}'. Switched to Free mode."

        try:
            self.route_total_distance = float(total_distance_m)
            self.route_move_distance = float(route_distance_m) + float(step_m)
        except Exception:
            pass

        command = ("route_move_action", str(int(step_m)), "")
        self.send_msg_to_map(command)

        next_remaining_km = max(0.0, (remaining_distance_m - float(step_m)) / 1000.0)
        return f"You moved {step_m} meters toward {target_place}. Remaining distance: {next_remaining_km:.2f} km."

    def update_after_moving(self):
        lng = self.aichatcfg_record.current_position[0]
        lat = self.aichatcfg_record.current_position[1]

        try:
            eps = 1e-9
            if abs(float(lng)) < eps and abs(float(lat)) < eps:
                logger.warning("Skip persisting current_position: (0,0) is not allowed")
                return
        except Exception:
            logger.warning("Skip persisting current_position: invalid lng/lat")
            return

        try:
            update_AiChatCfg_map(current_position=json.dumps({"lng": float(lng), "lat": float(lat)}, ensure_ascii=False))
        except Exception as e:
            logger.warning("Failed to persist current_position after moving: %s", e)

        try:
            cfg = query_AiChatCfg_map()
            if not cfg:
                logger.warning("Remote location sync skipped: aichat_cfg not found")
                return

            base = self._get_ai_sns_server_base()
            if not base:
                logger.warning("Remote location sync skipped: ai_sns_server is not configured")
                return

            nation_id = (getattr(cfg, "nationid", None) or "").strip()
            password = (getattr(cfg, "nationpassword", None) or "").strip()
            if not nation_id or not password:
                logger.warning("Remote location sync skipped: nationid/nationpassword is not configured")
                return

            url = f"{base}/api/update-location/"
            params = {
                "nation_id": nation_id,
                "password": password,
                "longitude": float(lng),
                "latitude": float(lat),
            }
            resp = requests.post(url, data=params, timeout=8)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to sync location to remote ai_sns_server: %s", e)
