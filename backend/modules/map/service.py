# -*- coding: utf-8 -*-
"""
Map module - Service layer
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import math
import random

import requests

from db.DBFactory import (
    query_AiChatCfg_map,
    query_AiChatCfg_map_setting,
    update_AiChatCfg_map,
    add_map_task,
    query_map_tasks,
    query_single_map_task,
    update_map_task,
    delete_map_task,
    add_map_tool,
    query_map_tools,
    query_single_map_tool,
    update_map_tool,
    delete_map_tool,
    add_map_trade,
    query_map_trades,
    query_single_map_trade,
    update_map_trade,
    delete_map_trade,
    add_map_visit,
    query_map_visits,
    query_single_map_visit,
    update_map_visit,
    delete_map_visit
)

logger = logging.getLogger(__name__)


class MapService:
    """Service for managing map functionality"""

    @staticmethod
    def _haversine_distance_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
        """Return great-circle distance in meters."""
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

    @classmethod
    def _fetch_place_list(cls, lng: float, lat: float) -> List[Dict[str, Any]]:
        remote_base = cls._get_ai_sns_server_base()
        if not remote_base:
            return []

        url = f"{remote_base}/api/get_place_list/"
        try:
            resp = requests.post(url, data={"lng": lng, "lat": lat}, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Failed to fetch place list from ai_sns_server: %s", e)
            return []

    @classmethod
    def update_location_and_get_nearest_place(
        cls,
        *,
        lng: float,
        lat: float,
        max_distance_m: int = 1000,
    ) -> Dict[str, Any]:
        """Persist the latest user location and return nearest place within max_distance_m."""
        try:
            lng_val = float(lng)
            lat_val = float(lat)
        except Exception:
            return {"success": False, "message": "Invalid lng/lat", "data": {}}

        if not (-180.0 <= lng_val <= 180.0 and -90.0 <= lat_val <= 90.0):
            return {"success": False, "message": "lng/lat out of range", "data": {}}

        try:
            update_AiChatCfg_map(current_position=json.dumps({"lng": lng_val, "lat": lat_val}, ensure_ascii=False))
        except Exception as e:
            logger.warning("Failed to persist current_position: %s", e)

        place_list = cls._fetch_place_list(lng_val, lat_val)
        if not place_list:
            return {"success": True, "data": {"url": "", "distance_m": None, "place": None}}

        best = None
        best_dist = None
        for place in place_list:
            if not isinstance(place, dict):
                continue
            pos = place.get("place_position")
            if not (isinstance(pos, (list, tuple)) and len(pos) >= 2):
                continue
            try:
                p_lng = float(pos[0])
                p_lat = float(pos[1])
            except Exception:
                continue
            dist_m = cls._haversine_distance_m(lng_val, lat_val, p_lng, p_lat)
            if best_dist is None or dist_m < best_dist:
                best_dist = dist_m
                best = place

        if best is None or best_dist is None:
            return {"success": True, "data": {"url": "", "distance_m": None, "place": None}}

        try:
            max_distance_m = int(max_distance_m)
        except Exception:
            max_distance_m = 1000

        if best_dist > max_distance_m:
            return {
                "success": True,
                "data": {
                    "url": "",
                    "distance_m": round(float(best_dist), 2),
                    "place": best,
                },
            }

        url = (best.get("url") or "").strip()
        return {
            "success": True,
            "data": {
                "url": url,
                "distance_m": round(float(best_dist), 2),
                "place": best,
            },
        }

    @staticmethod
    def _normalize_position(value: Any) -> Dict[str, float]:
        if not value:
            return {}

        parsed = value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except Exception:
                parsed = {}

        if isinstance(parsed, list) and len(parsed) >= 2:
            try:
                return {"lng": float(parsed[0]), "lat": float(parsed[1])}
            except Exception:
                return {}

        if isinstance(parsed, dict):
            try:
                lng = parsed.get("lng")
                lat = parsed.get("lat")
                if lng is None or lat is None:
                    return {}
                return {"lng": float(lng), "lat": float(lat)}
            except Exception:
                return {}

        return {}

    @staticmethod
    def _has_valid_lng_lat(pos: Dict[str, Any]) -> bool:
        try:
            if not isinstance(pos, dict):
                return False
            lng = float(pos.get("lng"))
            lat = float(pos.get("lat"))
            return -180.0 <= lng <= 180.0 and -90.0 <= lat <= 90.0
        except Exception:
            return False

    @staticmethod
    def _random_point_within_radius_m(lng: float, lat: float, radius_m: float) -> Dict[str, float]:
        earth_radius_m = 6371000.0
        bearing = random.random() * 2.0 * math.pi
        # sqrt for uniform area distribution
        distance_m = radius_m * math.sqrt(random.random())
        angular_distance = distance_m / earth_radius_m

        lat1 = math.radians(lat)
        lon1 = math.radians(lng)

        sin_lat1 = math.sin(lat1)
        cos_lat1 = math.cos(lat1)

        sin_ad = math.sin(angular_distance)
        cos_ad = math.cos(angular_distance)

        lat2 = math.asin(sin_lat1 * cos_ad + cos_lat1 * sin_ad * math.cos(bearing))
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * sin_ad * cos_lat1,
            cos_ad - sin_lat1 * math.sin(lat2),
        )

        lng2 = (math.degrees(lon2) + 540.0) % 360.0 - 180.0
        lat2d = math.degrees(lat2)
        lat2d = max(-89.999999, min(89.999999, lat2d))

        return {"lng": float(lng2), "lat": float(lat2d)}

    @staticmethod
    def _get_ai_sns_server_base() -> str:
        try:
            from db.DBFactory import query_SystemCfg
            cfg = query_SystemCfg(is_delete=False)
            v = getattr(cfg, "ai_sns_server", None)
            v = (v or "").strip()
            return v.rstrip("/") if v else ""
        except Exception:
            return ""

    @classmethod
    def _ensure_current_position(cls, cfg: Any) -> Dict[str, float]:
        current_position = cls._normalize_position(getattr(cfg, "current_position", None))
        if cls._has_valid_lng_lat(current_position):
            return current_position

        base_lng = 116.3974
        base_lat = 39.9093
        remote_base = cls._get_ai_sns_server_base()
        if remote_base:
            try:
                resp = requests.get(f"{remote_base}/api/get_initial_position/", timeout=8)
                resp.raise_for_status()
                payload = resp.json() if resp.content else {}
                if isinstance(payload, dict):
                    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
                    lng_val = data.get("lng")
                    lat_val = data.get("lat")
                    if lng_val is not None and lat_val is not None:
                        base_lng = float(lng_val)
                        base_lat = float(lat_val)
            except Exception as e:
                logger.warning("Failed to fetch initial position from ai_sns_server: %s", e)

        random_pos = cls._random_point_within_radius_m(base_lng, base_lat, 10000.0)
        try:
            from db.DBFactory import update_AiChatCfg_map
            update_AiChatCfg_map(current_position=json.dumps(random_pos, ensure_ascii=False))
        except Exception as e:
            logger.warning("Failed to persist auto-initialized current_position: %s", e)

        return random_pos

    @staticmethod
    def get_map_settings() -> Dict[str, Any]:
        """Get map configuration"""
        cfg = query_AiChatCfg_map()
        if cfg:
            normalized_current_position = MapService._ensure_current_position(cfg)
            return {
                "success": True,
                "data": {
                    "id": cfg.id,
                    "map_type": getattr(cfg, 'map_type', 'baidu'),
                    "map_api_key": getattr(cfg, 'map_api_key', ''),
                    "map_id": getattr(cfg, 'map_id', ''),
                    "current_position": normalized_current_position,
                    "home_position": json.loads(getattr(cfg, 'home_position', '{}')) if getattr(cfg, 'home_position', None) else {},
                    "route_status": getattr(cfg, 'route_status', 'stopped'),
                    "route_start": getattr(cfg, 'route_start', ''),
                    "route_end": getattr(cfg, 'route_end', ''),
                    "route_current_position": json.loads(getattr(cfg, 'route_current_position', '{}')) if getattr(cfg, 'route_current_position', None) else {},
                    "route_distance": getattr(cfg, 'route_distance', 0.0),
                    "avatar3d": getattr(cfg, 'avatar3d', 'default.glb'),
                    "nationid": getattr(cfg, 'nationid', '123456'),
                    "account": getattr(cfg, 'account', 'user@example.com'),
                    "nick_name": getattr(cfg, 'nickname', 'User nickname'),
                    "avatar": getattr(cfg, 'avatar', 'avatar.png'),
                    "profile": getattr(cfg, 'sign', 'Bio'),
                    "sns_url": getattr(cfg, 'sns_url', 'https://example.com'),
                    "status": getattr(cfg, 'status', 'online')
                }
            }

        # Default configuration
        return {
                "success": True,
                "data": {
                    "map_type": "baidu",
                    "map_api_key": "",
                    "map_id": "",
                    "current_position": {"lng": 116.3974, "lat": 39.9093},
                    "home_position": {},
                    "route_status": "stopped",
                    "route_start": "",
                    "route_end": "",
                    "route_current_position": {},
                    "route_distance": 0.0,
                    "avatar3d": "default.glb",
                    "nationid": "123456",
                    "account": "user@example.com",
                    "nick_name": "User nickname",
                    "avatar": "avatar.png",
                    "profile": "Bio",
                    "sns_url": "https://example.com",
                    "status": "online"
                }
        }

    @staticmethod
    def update_map_settings(config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Update map configuration"""
        cfg = query_AiChatCfg_map()
        if not cfg:
            raise ValueError("Map configuration not found")

        payload: Dict[str, Any] = {}
        if isinstance(config, dict):
            payload.update(config)
        if kwargs:
            payload.update(kwargs)

        updates: Dict[str, Any] = {}
        if "map_type" in payload:
            updates["map_type"] = payload.get("map_type")
        if "map_api_key" in payload:
            updates["map_api_key"] = payload.get("map_api_key")
        if "map_id" in payload:
            updates["map_id"] = payload.get("map_id")

        if "current_position" in payload:
            updates["current_position"] = json.dumps(payload.get("current_position"), ensure_ascii=False) if payload.get("current_position") else "{}"
        if "home_position" in payload:
            updates["home_position"] = json.dumps(payload.get("home_position"), ensure_ascii=False) if payload.get("home_position") else "{}"

        if "route_status" in payload:
            updates["route_status"] = payload.get("route_status")
        if "route_start" in payload:
            updates["route_start"] = payload.get("route_start")
        if "route_end" in payload:
            updates["route_end"] = payload.get("route_end")
        if "route_current_position" in payload:
            updates["route_current_position"] = json.dumps(payload.get("route_current_position"), ensure_ascii=False) if payload.get("route_current_position") else "{}"
        if "route_distance" in payload:
            updates["route_distance"] = payload.get("route_distance")

        if updates:
            update_AiChatCfg_map(**updates)
        return {"success": True}

    @staticmethod
    def get_home_position() -> Dict[str, Any]:
        """Get home position"""
        cfg = query_AiChatCfg_map()
        if cfg:
            return json.loads(getattr(cfg, 'home_position', '{}'))
        return {}

    @staticmethod
    def update_home_position(home_position: Dict[str, Any]) -> None:
        """Update home position"""
        cfg = query_AiChatCfg_map()
        if not cfg:
            raise ValueError("Map configuration not found")
        update_AiChatCfg_map(home_position=json.dumps(home_position, ensure_ascii=False))

    @staticmethod
    def plan_route(start: str, end: str, position_type: str = "address") -> Dict[str, Any]:
        """Plan route"""
        # TODO: Implement actual route planning logic
        distance = 5.2  # kilometers
        duration = 1200  # seconds
        return {
            "distance": distance,
            "duration": duration,
            "polyline": [],
            "status": "completed"
        }

    @staticmethod
    def control_route(route_id: str, action: str) -> Dict[str, Any]:
        """Control route simulation"""
        if action not in ["start", "stop", "pause", "resume"]:
            raise ValueError("Invalid action")
        # TODO: Implement route control logic
        return {"action": action, "status": "ok"}

    @staticmethod
    def get_map_markers() -> List[Dict[str, Any]]:
        """Get map markers"""
        # TODO: Get markers from database or other data source
        markers = []
        return markers

    @staticmethod
    def add_map_marker(marker: Dict[str, Any]) -> str:
        """Add map marker"""
        # TODO: Save marker to database
        marker_id = marker.get('id') or f"marker_{datetime.now().timestamp()}"
        return marker_id

    @staticmethod
    def update_map_marker(marker_id: str, marker: Dict[str, Any]) -> None:
        """Update map marker"""
        # TODO: Update marker information
        pass

    @staticmethod
    def delete_map_marker(marker_id: str) -> None:
        """Delete map marker"""
        # TODO: Delete marker
        pass

    @staticmethod
    def get_map_chat_history() -> List[Dict[str, Any]]:
        """Get map chat history"""
        # TODO: Get chat history from database
        messages = []
        return messages
