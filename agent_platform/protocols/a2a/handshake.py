"""
A2A Handshake Protocol

Implements the handshake protocol for Agent-to-Agent communication.
Handles capability negotiation and authentication between agents.
"""

import hmac
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


logger = logging.getLogger(__name__)


class HandshakeStatus(str, Enum):
    """Handshake status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class HandshakeRequest:
    """A2A Handshake request"""
    request_id: str
    caller_agent_id: str
    caller_agent_name: str
    caller_endpoint: str
    caller_capabilities: List[str]
    requested_capabilities: List[str] = field(default_factory=list)
    signature: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=5))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "caller_agent_id": self.caller_agent_id,
            "caller_agent_name": self.caller_agent_name,
            "caller_endpoint": self.caller_endpoint,
            "caller_capabilities": self.caller_capabilities,
            "requested_capabilities": self.requested_capabilities,
            "signature": self.signature,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class HandshakeResponse:
    """A2A Handshake response"""
    request_id: str
    status: HandshakeStatus
    responder_agent_id: str
    responder_agent_name: str
    responder_endpoint: str
    granted_capabilities: List[str] = field(default_factory=list)
    session_token: Optional[str] = None
    session_expires_at: Optional[datetime] = None
    signature: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "responder_agent_id": self.responder_agent_id,
            "responder_agent_name": self.responder_agent_name,
            "responder_endpoint": self.responder_endpoint,
            "granted_capabilities": self.granted_capabilities,
            "session_token": self.session_token,
            "session_expires_at": self.session_expires_at.isoformat() if self.session_expires_at else None,
            "signature": self.signature,
            "message": self.message,
            "metadata": self.metadata
        }


@dataclass
class A2ASession:
    """Active A2A session between agents"""
    session_id: str
    session_token: str
    caller_agent_id: str
    responder_agent_id: str
    granted_capabilities: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if session is still valid"""
        return datetime.now() < self.expires_at

    def refresh(self, hours: int = 24):
        """Refresh session expiration"""
        self.last_activity = datetime.now()
        self.expires_at = datetime.now() + timedelta(hours=hours)


class A2AHandshakeManager:
    """
    A2A Handshake Manager

    Manages handshake protocol for agent-to-agent communication:
    - Request/response handling
    - Capability negotiation
    - Session management
    - Signature verification
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        endpoint: str,
        capabilities: List[str],
        signing_secret: Optional[str] = None
    ):
        """
        Initialize handshake manager.

        Args:
            agent_id: This agent's ID
            agent_name: This agent's name
            endpoint: This agent's endpoint URL
            capabilities: This agent's capabilities
            signing_secret: Secret for signing handshakes
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.endpoint = endpoint
        self.capabilities = capabilities
        self.signing_secret = signing_secret or secrets.token_hex(32)

        self._pending_requests: Dict[str, HandshakeRequest] = {}
        self._sessions: Dict[str, A2ASession] = {}
        self._trusted_agents: Dict[str, str] = {}  # agent_id -> shared_secret

    def generate_request_id(self) -> str:
        """Generate unique request ID"""
        return f"hs_{secrets.token_hex(16)}"

    def generate_session_token(self) -> str:
        """Generate session token"""
        return secrets.token_urlsafe(32)

    def create_handshake_request(
        self,
        target_agent_id: str,
        requested_capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HandshakeRequest:
        """
        Create a handshake request to another agent.

        Args:
            target_agent_id: Target agent ID
            requested_capabilities: Capabilities to request
            metadata: Additional metadata

        Returns:
            HandshakeRequest
        """
        request = HandshakeRequest(
            request_id=self.generate_request_id(),
            caller_agent_id=self.agent_id,
            caller_agent_name=self.agent_name,
            caller_endpoint=self.endpoint,
            caller_capabilities=self.capabilities,
            requested_capabilities=requested_capabilities or [],
            metadata=metadata or {}
        )

        # Sign the request
        request.signature = self._sign_request(request)

        # Store pending request
        self._pending_requests[request.request_id] = request

        return request

    def process_handshake_request(
        self,
        request: HandshakeRequest,
        auto_accept: bool = False,
        allowed_capabilities: Optional[List[str]] = None
    ) -> HandshakeResponse:
        """
        Process an incoming handshake request.

        Args:
            request: Incoming handshake request
            auto_accept: Automatically accept the request
            allowed_capabilities: Capabilities to grant (None = all requested)

        Returns:
            HandshakeResponse
        """
        # Check if request is expired
        if datetime.now() > request.expires_at:
            return HandshakeResponse(
                request_id=request.request_id,
                status=HandshakeStatus.EXPIRED,
                responder_agent_id=self.agent_id,
                responder_agent_name=self.agent_name,
                responder_endpoint=self.endpoint,
                message="Handshake request has expired"
            )

        # Verify signature if trusted agent
        if request.caller_agent_id in self._trusted_agents:
            shared_secret = self._trusted_agents[request.caller_agent_id]
            if not self._verify_request_signature(request, shared_secret):
                return HandshakeResponse(
                    request_id=request.request_id,
                    status=HandshakeStatus.REJECTED,
                    responder_agent_id=self.agent_id,
                    responder_agent_name=self.agent_name,
                    responder_endpoint=self.endpoint,
                    message="Invalid signature"
                )

        # Determine granted capabilities
        if allowed_capabilities is None:
            # Grant intersection of requested and available
            granted = [
                cap for cap in request.requested_capabilities
                if cap in self.capabilities
            ]
        else:
            granted = [
                cap for cap in allowed_capabilities
                if cap in self.capabilities
            ]

        if not auto_accept and not granted:
            return HandshakeResponse(
                request_id=request.request_id,
                status=HandshakeStatus.REJECTED,
                responder_agent_id=self.agent_id,
                responder_agent_name=self.agent_name,
                responder_endpoint=self.endpoint,
                message="No matching capabilities"
            )

        # Create session
        session_token = self.generate_session_token()
        session_expires = datetime.now() + timedelta(hours=24)

        session = A2ASession(
            session_id=f"sess_{secrets.token_hex(8)}",
            session_token=session_token,
            caller_agent_id=request.caller_agent_id,
            responder_agent_id=self.agent_id,
            granted_capabilities=granted,
            expires_at=session_expires,
            metadata=request.metadata
        )

        self._sessions[session.session_id] = session
        self._sessions[session_token] = session  # Index by token too

        # Create response
        response = HandshakeResponse(
            request_id=request.request_id,
            status=HandshakeStatus.ACCEPTED,
            responder_agent_id=self.agent_id,
            responder_agent_name=self.agent_name,
            responder_endpoint=self.endpoint,
            granted_capabilities=granted,
            session_token=session_token,
            session_expires_at=session_expires,
            message="Handshake accepted"
        )

        # Sign response
        response.signature = self._sign_response(response)

        logger.info(
            f"Handshake accepted: {request.caller_agent_id} -> {self.agent_id}, "
            f"capabilities: {granted}"
        )

        return response

    def validate_session(
        self,
        session_token: str,
        required_capability: Optional[str] = None
    ) -> Optional[A2ASession]:
        """
        Validate a session token.

        Args:
            session_token: Session token to validate
            required_capability: Required capability for this operation

        Returns:
            A2ASession if valid, None otherwise
        """
        session = self._sessions.get(session_token)
        if not session:
            return None

        if not session.is_valid():
            # Clean up expired session
            self._sessions.pop(session.session_id, None)
            self._sessions.pop(session_token, None)
            return None

        if required_capability and required_capability not in session.granted_capabilities:
            return None

        # Update last activity
        session.last_activity = datetime.now()

        return session

    def revoke_session(self, session_token: str) -> bool:
        """Revoke a session"""
        session = self._sessions.get(session_token)
        if not session:
            return False

        self._sessions.pop(session.session_id, None)
        self._sessions.pop(session_token, None)
        return True

    def add_trusted_agent(self, agent_id: str, shared_secret: str):
        """Add a trusted agent with shared secret"""
        self._trusted_agents[agent_id] = shared_secret

    def remove_trusted_agent(self, agent_id: str):
        """Remove a trusted agent"""
        self._trusted_agents.pop(agent_id, None)

    def _sign_request(self, request: HandshakeRequest) -> str:
        """Sign a handshake request"""
        data = json.dumps({
            "request_id": request.request_id,
            "caller_agent_id": request.caller_agent_id,
            "timestamp": request.timestamp.isoformat()
        }, sort_keys=True)

        return hmac.new(
            self.signing_secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

    def _sign_response(self, response: HandshakeResponse) -> str:
        """Sign a handshake response"""
        data = json.dumps({
            "request_id": response.request_id,
            "responder_agent_id": response.responder_agent_id,
            "session_token": response.session_token
        }, sort_keys=True)

        return hmac.new(
            self.signing_secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_request_signature(
        self,
        request: HandshakeRequest,
        shared_secret: str
    ) -> bool:
        """Verify request signature"""
        if not request.signature:
            return False

        data = json.dumps({
            "request_id": request.request_id,
            "caller_agent_id": request.caller_agent_id,
            "timestamp": request.timestamp.isoformat()
        }, sort_keys=True)

        expected = hmac.new(
            shared_secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(request.signature, expected)

    def get_active_sessions(self) -> List[A2ASession]:
        """Get all active sessions"""
        active = []
        expired = []

        for key, session in self._sessions.items():
            if isinstance(session, A2ASession):
                if session.is_valid():
                    if session not in active:
                        active.append(session)
                else:
                    expired.append(key)

        # Clean up expired
        for key in expired:
            self._sessions.pop(key, None)

        return active

    def get_stats(self) -> Dict[str, Any]:
        """Get handshake manager statistics"""
        return {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "pending_requests": len(self._pending_requests),
            "active_sessions": len(self.get_active_sessions()),
            "trusted_agents": len(self._trusted_agents)
        }


# Singleton instance
_handshake_manager: Optional[A2AHandshakeManager] = None


def get_handshake_manager(
    agent_id: str = "default",
    agent_name: str = "AI-SNS Agent",
    endpoint: str = "http://localhost:8000",
    capabilities: Optional[List[str]] = None
) -> A2AHandshakeManager:
    """Get the handshake manager instance"""
    global _handshake_manager
    if _handshake_manager is None:
        _handshake_manager = A2AHandshakeManager(
            agent_id=agent_id,
            agent_name=agent_name,
            endpoint=endpoint,
            capabilities=capabilities or ["chat", "streaming"]
        )
    return _handshake_manager
