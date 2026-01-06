"""
Authentication Middleware

Provides API Key authentication for FastAPI.
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional, List
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from agent_platform.security.api_key import APIKeyManager, APIKeyInfo, get_api_key_manager


logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_header = APIKeyHeader(name="Authorization", auto_error=False)


# Public paths that don't require authentication
PUBLIC_PATHS = [
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/.well-known/agent.json",
    "/.well-known/ai-plugin.json",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication Middleware

    Checks for valid API key in requests.
    Supports both X-API-Key header and Authorization: Bearer header.
    """

    def __init__(self, app, public_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.api_key_manager = get_api_key_manager()
        self.public_paths = public_paths or PUBLIC_PATHS

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)"""
        # Exact match
        if path in self.public_paths:
            return True

        # Prefix match for static files
        if path.startswith("/static/"):
            return True
        if path.startswith("/images/"):
            return True

        return False

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers"""
        # Try X-API-Key header first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # Try Authorization: Bearer header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]

        # Try query parameter (for SSE connections)
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key

        return None

    async def dispatch(self, request: Request, call_next):
        """Process request through authentication"""
        path = request.url.path

        # Skip auth for public paths
        if self._is_public_path(path):
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract API key
        api_key = self._extract_api_key(request)
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "API key required",
                    "error_code": "AUTH_REQUIRED"
                }
            )

        # Validate API key
        key_info = self.api_key_manager.validate_key(api_key)
        if not key_info:
            logger.warning(f"Invalid API key attempt from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "Invalid or expired API key",
                    "error_code": "INVALID_API_KEY"
                }
            )

        # Store key info in request state for later use
        request.state.api_key_info = key_info
        request.state.user_id = key_info.user_id

        # Continue to next handler
        response = await call_next(request)
        return response


async def get_current_api_key(
    x_api_key: Optional[str] = Depends(api_key_header),
    authorization: Optional[str] = Depends(bearer_header)
) -> APIKeyInfo:
    """
    Dependency to get current API key info.

    Usage:
        @app.get("/protected")
        async def protected_route(key_info: APIKeyInfo = Depends(get_current_api_key)):
            return {"user_id": key_info.user_id}
    """
    api_key = None

    # Check X-API-Key header
    if x_api_key:
        api_key = x_api_key

    # Check Authorization: Bearer header
    elif authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "API key required",
                "error_code": "AUTH_REQUIRED"
            }
        )

    # Validate key
    api_key_manager = get_api_key_manager()
    key_info = api_key_manager.validate_key(api_key)

    if not key_info:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid or expired API key",
                "error_code": "INVALID_API_KEY"
            }
        )

    return key_info


def require_scope(scope: str):
    """
    Dependency factory to require a specific scope.

    Usage:
        @app.post("/agents")
        async def create_agent(
            key_info: APIKeyInfo = Depends(require_scope("agent:write"))
        ):
            ...
    """
    async def check_scope(key_info: APIKeyInfo = Depends(get_current_api_key)) -> APIKeyInfo:
        api_key_manager = get_api_key_manager()
        if not api_key_manager.check_scope(key_info, scope):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": f"Insufficient permissions. Required scope: {scope}",
                    "error_code": "INSUFFICIENT_SCOPE"
                }
            )
        return key_info

    return check_scope


def get_optional_api_key(
    x_api_key: Optional[str] = Depends(api_key_header),
    authorization: Optional[str] = Depends(bearer_header)
) -> Optional[APIKeyInfo]:
    """
    Dependency to optionally get API key info (for public endpoints with optional auth).
    """
    api_key = None

    if x_api_key:
        api_key = x_api_key
    elif authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]

    if not api_key:
        return None

    api_key_manager = get_api_key_manager()
    return api_key_manager.validate_key(api_key)
