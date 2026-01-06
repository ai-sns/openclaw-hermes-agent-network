"""
AI Agent Open Platform Module

This module provides:
- API Gateway (REST, WebSocket, SSE)
- A2A Protocol (Agent-to-Agent)
- MCP Protocol (Model Context Protocol)
- Security (API Key, Rate Limiting)
- Media Handling (Upload, Download, Stream)
- Session Management
- Async Task Processing
"""

__version__ = "1.0.0"
__author__ = "AI-SNS Team"

from .gateway import PlatformRouter
from .security import APIKeyManager

__all__ = [
    "PlatformRouter",
    "APIKeyManager",
]
