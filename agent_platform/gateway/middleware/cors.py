"""
CORS Middleware Configuration

Provides CORS configuration for FastAPI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional


def setup_cors(
    app: FastAPI,
    allow_origins: Optional[List[str]] = None,
    allow_credentials: bool = True,
    allow_methods: Optional[List[str]] = None,
    allow_headers: Optional[List[str]] = None,
    expose_headers: Optional[List[str]] = None,
    max_age: int = 600
) -> None:
    """
    Setup CORS middleware for FastAPI app.

    Args:
        app: FastAPI application
        allow_origins: List of allowed origins (default: ["*"])
        allow_credentials: Whether to allow credentials
        allow_methods: Allowed HTTP methods (default: ["*"])
        allow_headers: Allowed headers (default: ["*"])
        expose_headers: Headers to expose to browser
        max_age: Max age for preflight cache (seconds)
    """
    if allow_origins is None:
        # Default: allow all origins in development
        # In production, you should restrict this
        allow_origins = ["*"]

    if allow_methods is None:
        allow_methods = ["*"]

    if allow_headers is None:
        allow_headers = [
            "*",
            "X-API-Key",
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
        ]

    if expose_headers is None:
        expose_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Request-ID",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        expose_headers=expose_headers,
        max_age=max_age
    )


# Preset configurations
CORS_DEVELOPMENT = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

CORS_PRODUCTION = {
    "allow_origins": [
        "https://yourdomain.com",
        "https://app.yourdomain.com",
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": [
        "X-API-Key",
        "Authorization",
        "Content-Type",
        "Accept",
    ],
}
