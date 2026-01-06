"""
WebSocket Handlers

Provides real-time bidirectional communication.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Optional, Any, List
import asyncio
import json
from datetime import datetime
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


logger = logging.getLogger(__name__)

websocket_router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    WebSocket Connection Manager

    Manages active WebSocket connections and message routing.
    """

    def __init__(self):
        # client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # client_id -> user_id (for authenticated connections)
        self.client_users: Dict[str, str] = {}
        # session_id -> [client_ids] (for session broadcasting)
        self.session_clients: Dict[str, List[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Accept and register a new connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if user_id:
            self.client_users[client_id] = user_id

        if session_id:
            if session_id not in self.session_clients:
                self.session_clients[session_id] = []
            self.session_clients[session_id].append(client_id)

        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        """Remove a connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if client_id in self.client_users:
            del self.client_users[client_id]

        # Remove from session clients
        for session_id, clients in self.session_clients.items():
            if client_id in clients:
                clients.remove(client_id)

        logger.info(f"WebSocket disconnected: {client_id}")

    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)

    async def send_to_session(self, message: dict, session_id: str):
        """Send message to all clients in a session"""
        client_ids = self.session_clients.get(session_id, [])
        for client_id in client_ids:
            await self.send_personal_message(message, client_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for client_id in self.active_connections:
            await self.send_personal_message(message, client_id)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

    def is_connected(self, client_id: str) -> bool:
        """Check if a client is connected"""
        return client_id in self.active_connections


# Global connection manager
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the connection manager instance"""
    return manager


@websocket_router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    api_key: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time communication.

    Protocol:
    - Client sends JSON messages with "type" field
    - Server responds with JSON messages

    Message types:
    - ping: Keep-alive
    - chat: Send chat message
    - subscribe: Subscribe to events

    Example:
    ```javascript
    const ws = new WebSocket('ws://host/ws/client123?api_key=xxx');

    ws.onopen = () => {
        ws.send(JSON.stringify({
            type: 'chat',
            agent_id: 'agent_001',
            message: 'Hello'
        }));
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);
    };
    ```
    """
    # Validate API key
    user_id = None
    if api_key:
        from agent_platform.security.api_key import get_api_key_manager
        api_key_manager = get_api_key_manager()
        key_info = api_key_manager.validate_key(api_key)
        if key_info:
            user_id = key_info.user_id
        else:
            await websocket.close(code=4001, reason="Invalid API key")
            return

    await manager.connect(websocket, client_id, user_id, session_id)

    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }, client_id)

        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                # Heartbeat
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, client_id)

            elif msg_type == "chat":
                # Handle chat message
                await handle_chat_message(client_id, data)

            elif msg_type == "subscribe":
                # Subscribe to events
                event_type = data.get("event")
                await manager.send_personal_message({
                    "type": "subscribed",
                    "event": event_type
                }, client_id)

            else:
                # Unknown message type
                await manager.send_personal_message({
                    "type": "error",
                    "error": f"Unknown message type: {msg_type}"
                }, client_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)


async def handle_chat_message(client_id: str, data: dict):
    """Handle incoming chat message"""
    agent_id = data.get("agent_id")
    message = data.get("message")
    session_id = data.get("session_id")

    if not agent_id or not message:
        await manager.send_personal_message({
            "type": "error",
            "error": "agent_id and message are required"
        }, client_id)
        return

    try:
        from globals import global_agent_list
        from db.DBFactory import query_AgentCfg
        from agent_platform.session import get_session_manager

        # Get or create session
        session_manager = get_session_manager()
        if session_id:
            session = session_manager.get_session(session_id)
        else:
            session = session_manager.create_session(agent_id=agent_id)
            session_id = session.session_id

        # Send session info
        await manager.send_personal_message({
            "type": "session",
            "session_id": session_id
        }, client_id)

        # Get agent
        agent_key = f"agent_{agent_id}"
        if agent_key not in global_agent_list:
            cfg = query_AgentCfg(user_id=agent_id)
            if not cfg:
                await manager.send_personal_message({
                    "type": "error",
                    "error": "Agent not found"
                }, client_id)
                return

            from Agent import Agent
            agent = Agent(cfg)
            global_agent_list[agent_key] = agent
        else:
            agent = global_agent_list[agent_key]

        # Add user message
        session_manager.add_message(session_id, {
            "role": "user",
            "content": message
        })

        # Send typing indicator
        await manager.send_personal_message({
            "type": "typing",
            "agent_id": agent_id
        }, client_id)

        # Get response
        messages = session.messages.copy() if session else []
        messages.append({"role": "user", "content": message})

        response = agent.ask_it(message, messages, None, session_id)

        # Add assistant message
        session_manager.add_message(session_id, {
            "role": "assistant",
            "content": response
        })

        # Send response
        await manager.send_personal_message({
            "type": "message",
            "role": "assistant",
            "content": response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, client_id)

    except Exception as e:
        await manager.send_personal_message({
            "type": "error",
            "error": str(e)
        }, client_id)
