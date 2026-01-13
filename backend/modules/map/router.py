# -*- coding: utf-8 -*-
"""
Map module - API router
"""
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends

# 导入全局WebSocket管理器
from backend.shared.websocket_manager import ConnectionManager as GlobalConnectionManager
from backend.shared.websocket_manager import manager as global_ws_manager

from backend.shared.websocket_manager import ConnectionManager
from .schemas import MapConfig, MapMarker, RouteRequest, RouteControl, ChatMessageMap
from .service import MapService
from .websocket import manager, handle_websocket_message
from .dependencies import get_map_service, get_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Map Settings ====================

@router.get("/settings", response_model=dict)
async def get_map_settings(service: MapService = Depends(get_map_service)):
    """
    Get map configuration

    Returns:
        Map configuration
    """
    try:
        data = service.get_map_settings()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error getting map settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings", response_model=dict)
async def update_map_settings(
    config: MapConfig,
    service: MapService = Depends(get_map_service)
):
    """
    Update map configuration

    Args:
        config: Map configuration

    Returns:
        Success status
    """
    try:
        service.update_map_settings(config.dict(exclude_unset=True))
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating map settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/home", response_model=dict)
async def get_home_position(service: MapService = Depends(get_map_service)):
    """
    Get home position

    Returns:
        Home position configuration
    """
    try:
        data = service.get_home_position()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error getting home position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/home", response_model=dict)
async def update_home_position(
    home_position: Dict[str, Any],
    service: MapService = Depends(get_map_service)
):
    """
    Update home position

    Args:
        home_position: Home position configuration

    Returns:
        Success status
    """
    try:
        service.update_home_position(home_position)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating home position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Route Planning ====================

@router.post("/route", response_model=dict)
async def plan_route(
    request: RouteRequest,
    service: MapService = Depends(get_map_service)
):
    """
    Plan route

    Args:
        request: Route planning request

    Returns:
        Route planning result
    """
    try:
        result = service.plan_route(
            request.start,
            request.end,
            request.position_type
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error planning route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route/{route_id}/control", response_model=dict)
async def control_route(
    route_id: str,
    request: RouteControl,
    service: MapService = Depends(get_map_service)
):
    """
    Control route simulation

    Args:
        route_id: Route ID
        request: Route control request

    Returns:
        Control result
    """
    try:
        result = service.control_route(route_id, request.action)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error controlling route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Map Markers ====================

@router.get("/markers", response_model=dict)
async def get_map_markers(service: MapService = Depends(get_map_service)):
    """
    Get map markers

    Returns:
        List of map markers
    """
    try:
        markers = service.get_map_markers()
        return {"success": True, "data": markers}
    except Exception as e:
        logger.error(f"Error getting map markers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/markers", response_model=dict)
async def add_map_marker(
    marker: MapMarker,
    service: MapService = Depends(get_map_service)
):
    """
    Add map marker

    Args:
        marker: Map marker

    Returns:
        Created marker ID
    """
    try:
        marker_id = service.add_map_marker(marker.dict(exclude_unset=True))
        return {"success": True, "data": {"id": marker_id}}
    except Exception as e:
        logger.error(f"Error adding map marker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/markers/{marker_id}", response_model=dict)
async def update_map_marker(
    marker_id: str,
    marker: MapMarker,
    service: MapService = Depends(get_map_service)
):
    """
    Update map marker

    Args:
        marker_id: Marker ID
        marker: Updated marker data

    Returns:
        Success status
    """
    try:
        service.update_map_marker(marker_id, marker.dict(exclude_unset=True))
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating map marker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/markers/{marker_id}", response_model=dict)
async def delete_map_marker(
    marker_id: str,
    service: MapService = Depends(get_map_service)
):
    """
    Delete map marker

    Args:
        marker_id: Marker ID

    Returns:
        Success status
    """
    try:
        service.delete_map_marker(marker_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting map marker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Map Chat ====================

@router.post("/chat", response_model=dict)
async def send_map_chat_message(
    message: ChatMessageMap,
    conn_manager: ConnectionManager = Depends(get_connection_manager)
):
    """
    Send map chat message

    Args:
        message: Chat message

    Returns:
        Success status
    """
    try:
        # Log the received message
        print(f"Received chat message: from={message.from_user}, to={message.to_user}, content={message.content}")
        
        # Log the number of active connections
        active_count = global_ws_manager.get_client_count()
        print(f"Active WebSocket connections: {active_count}")
        
        # TODO: Save chat message to database
        # Broadcast message via WebSocket using the GLOBAL manager to reach all connected clients
        print("About to broadcast message via global WebSocket manager")
        await global_ws_manager.broadcast({
            "type": "map_chat_message",
            "from_user": message.from_user,
            "to_user": message.to_user,
            "content": message.content,
            "location": message.location,
            "timestamp": datetime.now().isoformat()
        })
        print("Message broadcast successful")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error sending map chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history", response_model=dict)
async def get_map_chat_history(service: MapService = Depends(get_map_service)):
    """
    Get map chat history

    Returns:
        List of chat messages
    """
    try:
        messages = service.get_map_chat_history()
        return {"success": True, "data": messages}
    except Exception as e:
        logger.error(f"Error getting map chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket ====================

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    conn_manager: ConnectionManager = Depends(get_connection_manager)
):
    """
    WebSocket connection endpoint for real-time message push

    Args:
        websocket: WebSocket connection
        client_id: Client ID
    """
    await conn_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(data, client_id)

    except WebSocketDisconnect:
        conn_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        conn_manager.disconnect(client_id)
