"""
JSON-RPC 2.0 Router for A2A Protocol

FastAPI router providing JSON-RPC endpoint.
"""

import json
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from .handler import get_jsonrpc_handler, JSONRPCHandler
from .models import JSONRPCRequest, JSONRPCResponse, JSONRPCError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))


# Create router
jsonrpc_router = APIRouter(tags=["JSON-RPC 2.0"])


async def get_api_key(request: Request) -> Optional[str]:
    """Extract API key from request"""
    # Try header first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

    # Try Authorization header
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]

    return None


@jsonrpc_router.post("/rpc")
async def jsonrpc_endpoint(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key)
):
    """
    JSON-RPC 2.0 Endpoint

    Handles all A2A JSON-RPC requests. Supports both single requests
    and batch requests.

    Methods:
    - tasks/send: Send a task and wait for completion
    - tasks/sendSubscribe: Send a task with streaming updates
    - tasks/get: Get task status and history
    - tasks/cancel: Cancel a pending/running task
    - tasks/resubscribe: Resubscribe to task updates
    - tasks/pushNotification/set: Configure push notifications
    - tasks/pushNotification/get: Get push notification config
    """
    handler = get_jsonrpc_handler()

    # Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        return JSONResponse(
            content=JSONRPCResponse.failure(
                JSONRPCError.parse_error(str(e))
            ).model_dump(),
            status_code=200  # JSON-RPC always returns 200
        )

    # Check for streaming request
    accept = request.headers.get("Accept", "")
    is_streaming = "text/event-stream" in accept

    if is_streaming and isinstance(body, dict) and body.get("method") == "tasks/sendSubscribe":
        # Handle streaming request
        return StreamingResponse(
            handler.handle_streaming_request(body, api_key),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # Handle regular request(s)
    result = await handler.handle_request(body, api_key)

    # Handle notification (no response)
    if result is None:
        return JSONResponse(content=None, status_code=204)

    # Handle batch response
    if isinstance(result, list):
        return JSONResponse(
            content=[r.model_dump() for r in result],
            status_code=200
        )

    # Handle single response
    return JSONResponse(
        content=result.model_dump(),
        status_code=200
    )


@jsonrpc_router.get("/rpc/methods")
async def list_methods():
    """
    List available JSON-RPC methods

    Returns the list of supported JSON-RPC methods with their descriptions.
    """
    return {
        "methods": [
            {
                "name": "tasks/send",
                "description": "Send a task to the agent and wait for completion",
                "params": {
                    "id": "string (required) - Task ID",
                    "sessionId": "string (optional) - Session ID for context",
                    "message": "object (required) - Message with role and parts",
                    "acceptedOutputModes": "array (optional) - Accepted output types",
                    "pushNotification": "object (optional) - Webhook config",
                    "metadata": "object (optional) - Additional metadata"
                }
            },
            {
                "name": "tasks/sendSubscribe",
                "description": "Send a task with streaming updates (SSE)",
                "params": {
                    "id": "string (required) - Task ID",
                    "sessionId": "string (optional) - Session ID",
                    "message": "object (required) - Message with role and parts",
                    "acceptedOutputModes": "array (optional) - Accepted output types"
                },
                "notes": "Use Accept: text/event-stream header for streaming"
            },
            {
                "name": "tasks/get",
                "description": "Get task status and message history",
                "params": {
                    "id": "string (required) - Task ID",
                    "historyLength": "integer (optional) - Max history items"
                }
            },
            {
                "name": "tasks/cancel",
                "description": "Cancel a pending or running task",
                "params": {
                    "id": "string (required) - Task ID"
                }
            },
            {
                "name": "tasks/resubscribe",
                "description": "Resubscribe to task updates after disconnect",
                "params": {
                    "id": "string (required) - Task ID"
                }
            },
            {
                "name": "tasks/pushNotification/set",
                "description": "Configure webhook for task notifications",
                "params": {
                    "id": "string (required) - Task ID",
                    "pushNotificationConfig": {
                        "url": "string (required) - Webhook URL",
                        "token": "string (optional) - Auth token"
                    }
                }
            },
            {
                "name": "tasks/pushNotification/get",
                "description": "Get current webhook configuration",
                "params": {
                    "id": "string (required) - Task ID"
                }
            }
        ],
        "version": "2.0",
        "protocol": "JSON-RPC 2.0"
    }


@jsonrpc_router.post("/rpc/batch")
async def jsonrpc_batch_endpoint(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key)
):
    """
    JSON-RPC 2.0 Batch Endpoint

    Explicitly handles batch requests (array of requests).
    """
    handler = get_jsonrpc_handler()

    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        return JSONResponse(
            content=JSONRPCResponse.failure(
                JSONRPCError.parse_error(str(e))
            ).model_dump(),
            status_code=200
        )

    if not isinstance(body, list):
        return JSONResponse(
            content=JSONRPCResponse.failure(
                JSONRPCError.invalid_request("Batch endpoint expects array of requests")
            ).model_dump(),
            status_code=200
        )

    results = await handler.handle_request(body, api_key)

    if isinstance(results, list):
        return JSONResponse(
            content=[r.model_dump() for r in results],
            status_code=200
        )

    return JSONResponse(content=[], status_code=200)


# ============== Health Check ==============

@jsonrpc_router.get("/rpc/health")
async def jsonrpc_health():
    """Check JSON-RPC endpoint health"""
    return {
        "status": "healthy",
        "protocol": "JSON-RPC 2.0",
        "version": "1.0.0",
        "methods_count": len(get_jsonrpc_handler().SUPPORTED_METHODS)
    }
