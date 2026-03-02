"""
WebSocket Connection Manager

Manages WebSocket connections for real-time communication.
Extracted from api_server.py ConnectionManager class.
"""

from typing import Dict, List, Optional, Any
from fastapi import WebSocket
import logging
import json
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting

    Features:
    - Connect/disconnect clients
    - Send messages to specific clients
    - Broadcast messages to all connected clients
    - Room-based messaging (optional)
    """

    def __init__(self):
        # Store active connections: {client_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # Room support: {room_id: set(client_ids)}
        self.rooms: Dict[str, set] = {}

        # Client metadata: {client_id: metadata}
        self.client_metadata: Dict[str, dict] = {}

        self._on_zero_clients_callbacks = []
        self._zero_clients_task: Optional[asyncio.Task] = None

    def add_on_zero_clients_callback(self, callback):
        if callable(callback):
            self._on_zero_clients_callbacks.append(callback)

    def _schedule_zero_clients_callbacks(self):
        try:
            if self._zero_clients_task and not self._zero_clients_task.done():
                self._zero_clients_task.cancel()
        except Exception:
            pass

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        async def _runner():
            try:
                await asyncio.sleep(2.0)
                if self.get_client_count() != 0:
                    return
                for cb in list(self._on_zero_clients_callbacks):
                    try:
                        res = cb()
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as e:
                        logger.warning(f"on_zero_clients callback failed: {e}")
            except asyncio.CancelledError:
                return

        self._zero_clients_task = loop.create_task(_runner())

    async def connect(self, websocket: WebSocket, client_id: str, metadata: Optional[dict] = None):
        """
        Accept and register a new WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
            client_id: Unique identifier for the client
            metadata: Optional metadata about the client (user info, etc.)
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if metadata:
            self.client_metadata[client_id] = metadata

        logger.info(f"Client {client_id} connected (total: {len(self.active_connections)})")

        try:
            if self._zero_clients_task and not self._zero_clients_task.done():
                self._zero_clients_task.cancel()
        except Exception:
            pass

    def disconnect(self, client_id: str):
        """
        Remove a client from active connections

        Args:
            client_id: Client identifier to disconnect
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected (remaining: {len(self.active_connections)})")

        if len(self.active_connections) == 0:
            self._schedule_zero_clients_callbacks()

        # Remove from all rooms
        for room_id in list(self.rooms.keys()):
            if client_id in self.rooms[room_id]:
                self.rooms[room_id].remove(client_id)
                if not self.rooms[room_id]:
                    del self.rooms[room_id]

        # Remove metadata
        if client_id in self.client_metadata:
            del self.client_metadata[client_id]

    async def send_message(self, message: Any, client_id: str):
        """
        Send a message to a specific client

        Args:
            message: Message to send (will be converted to JSON)
            client_id: Target client identifier
        """
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]

                if isinstance(message, dict) or isinstance(message, list):
                    await websocket.send_json(message)
                elif isinstance(message, str):
                    await websocket.send_text(message)
                else:
                    await websocket.send_text(str(message))

            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                # Remove disconnected client
                self.disconnect(client_id)

    async def broadcast(self, message: Any, exclude: Optional[List[str]] = None):
        """
        Broadcast a message to all connected clients

        Args:
            message: Message to broadcast
            exclude: Optional list of client IDs to exclude
        """
        exclude = exclude or []
        disconnected = []

        for client_id, websocket in self.active_connections.items():
            if client_id in exclude:
                continue

            try:
                if isinstance(message, dict) or isinstance(message, list):
                    await websocket.send_json(message)
                elif isinstance(message, str):
                    await websocket.send_text(message)
                else:
                    await websocket.send_text(str(message))
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    def join_room(self, client_id: str, room_id: str):
        """
        Add a client to a room

        Args:
            client_id: Client identifier
            room_id: Room identifier
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(client_id)
        logger.info(f"Client {client_id} joined room {room_id}")

    def leave_room(self, client_id: str, room_id: str):
        """
        Remove a client from a room

        Args:
            client_id: Client identifier
            room_id: Room identifier
        """
        if room_id in self.rooms and client_id in self.rooms[room_id]:
            self.rooms[room_id].remove(client_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
            logger.info(f"Client {client_id} left room {room_id}")

    async def broadcast_to_room(self, message: Any, room_id: str, exclude: Optional[List[str]] = None):
        """
        Broadcast a message to all clients in a specific room

        Args:
            message: Message to broadcast
            room_id: Target room identifier
            exclude: Optional list of client IDs to exclude
        """
        if room_id not in self.rooms:
            return

        exclude = exclude or []
        disconnected = []

        for client_id in self.rooms[room_id]:
            if client_id in exclude or client_id not in self.active_connections:
                continue

            try:
                websocket = self.active_connections[client_id]
                if isinstance(message, dict) or isinstance(message, list):
                    await websocket.send_json(message)
                elif isinstance(message, str):
                    await websocket.send_text(message)
                else:
                    await websocket.send_text(str(message))
            except Exception as e:
                logger.error(f"Failed to send to {client_id} in room {room_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    def get_connected_clients(self) -> List[str]:
        """Get list of all connected client IDs"""
        return list(self.active_connections.keys())

    def get_room_clients(self, room_id: str) -> List[str]:
        """Get list of client IDs in a specific room"""
        return list(self.rooms.get(room_id, set()))

    def get_client_metadata(self, client_id: str) -> Optional[dict]:
        """Get metadata for a specific client"""
        return self.client_metadata.get(client_id)

    def get_client_count(self) -> int:
        """Get total number of connected clients"""
        return len(self.active_connections)


# Singleton instance
manager = ConnectionManager()
