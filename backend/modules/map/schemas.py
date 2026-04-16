# -*- coding: utf-8 -*-
"""
Map module - Pydantic schemas
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class MapConfig(BaseModel):
    """Map configuration"""
    id: Optional[int] = None
    map_type: Optional[str] = "baidu"  # "baidu" or "google"
    map_api_key: Optional[str] = ""
    map_id: Optional[str] = ""
    current_position: Optional[Dict[str, Any]] = None
    home_position: Optional[Dict[str, Any]] = None
    route_status: Optional[str] = "stopped"  # "playing" or "stopped"
    route_start: Optional[str] = ""
    route_end: Optional[str] = ""
    route_current_position: Optional[Dict[str, Any]] = None
    route_distance: Optional[float] = 0.0


class MapMarker(BaseModel):
    """Map marker"""
    id: Optional[str] = None
    location: Dict[str, float]
    type: Optional[str] = "person"
    data: Optional[Dict[str, Any]] = None
    visible: Optional[bool] = True


class RouteRequest(BaseModel):
    """Route planning request"""
    start: str  # Address or coordinate string
    end: str    # Address or coordinate string
    position_type: Optional[str] = "address"  # "address" or "coordinates"


class RouteControl(BaseModel):
    """Route control"""
    action: str  # "start", "stop", "pause", "resume"


class ChatMessageMap(BaseModel):
    """Map chat message"""
    from_user: str
    to_user: str
    content: str
    location: Optional[Dict[str, float]] = None
