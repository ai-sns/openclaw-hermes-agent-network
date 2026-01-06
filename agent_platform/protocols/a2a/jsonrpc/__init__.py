"""
JSON-RPC 2.0 Module for A2A Protocol

Provides JSON-RPC 2.0 compliant interface for the A2A protocol,
compatible with Google's A2A specification.
"""

from .models import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    JSONRPCErrorCode,
    TaskSendParams,
    TaskGetParams,
    TaskCancelParams,
    PushNotificationParams,
)
from .handler import JSONRPCHandler, get_jsonrpc_handler
from .router import jsonrpc_router

__all__ = [
    # Models
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCError",
    "JSONRPCErrorCode",
    "TaskSendParams",
    "TaskGetParams",
    "TaskCancelParams",
    "PushNotificationParams",
    # Handler
    "JSONRPCHandler",
    "get_jsonrpc_handler",
    # Router
    "jsonrpc_router",
]
