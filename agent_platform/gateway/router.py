"""
Platform Router

Unified router that integrates all platform routes.
"""

from fastapi import FastAPI, APIRouter, UploadFile, File, Depends
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_platform.gateway.handlers.rest import rest_router
from agent_platform.gateway.handlers.sse import sse_router
from agent_platform.gateway.handlers.websocket import websocket_router
from agent_platform.gateway.handlers.webhook import webhook_router
from agent_platform.gateway.middleware.auth import AuthMiddleware, get_current_api_key
from agent_platform.gateway.middleware.rate_limiter import RateLimiterMiddleware
from agent_platform.gateway.middleware.cors import setup_cors
from agent_platform.media.download import download_router
from agent_platform.gateway.schemas.requests import FileUploadResponse, APIResponse
from agent_platform.protocols.a2a.router import a2a_router
from agent_platform.protocols.mcp.router import mcp_router


class PlatformRouter:
    """
    Platform Router

    Integrates all platform routes and middleware.

    Usage:
        from fastapi import FastAPI
        from agent_platform.gateway.router import PlatformRouter

        app = FastAPI()
        platform = PlatformRouter(app)
        platform.setup()
    """

    def __init__(
        self,
        app: FastAPI,
        enable_auth: bool = True,
        enable_rate_limit: bool = True,
        enable_cors: bool = True,
        rate_limit: int = 100,
        rate_window: int = 60
    ):
        """
        Initialize platform router.

        Args:
            app: FastAPI application
            enable_auth: Enable authentication middleware
            enable_rate_limit: Enable rate limiting middleware
            enable_cors: Enable CORS middleware
            rate_limit: Requests per window
            rate_window: Window in seconds
        """
        self.app = app
        self.enable_auth = enable_auth
        self.enable_rate_limit = enable_rate_limit
        self.enable_cors = enable_cors
        self.rate_limit = rate_limit
        self.rate_window = rate_window

        # Create main router
        self.main_router = APIRouter()

    def setup(self):
        """Setup all routes and middleware"""
        self._setup_middleware()
        self._setup_routes()
        self._setup_static_routes()
        self._setup_file_routes()

    def _setup_middleware(self):
        """Setup middleware stack"""
        # CORS must be added first
        if self.enable_cors:
            setup_cors(self.app)

        # Rate limiting (before auth to protect from abuse)
        if self.enable_rate_limit:
            self.app.add_middleware(
                RateLimiterMiddleware,
                rate=self.rate_limit,
                per=self.rate_window
            )

        # Authentication
        if self.enable_auth:
            self.app.add_middleware(AuthMiddleware)

    def _setup_routes(self):
        """Setup API routes"""
        # REST API routes
        self.app.include_router(rest_router)

        # SSE streaming routes
        self.app.include_router(sse_router)

        # WebSocket routes
        self.app.include_router(websocket_router)

        # Webhook routes
        self.app.include_router(webhook_router)

        # File download routes
        self.app.include_router(download_router)

        # A2A Protocol routes
        self.app.include_router(a2a_router)

        # MCP Protocol routes
        self.app.include_router(mcp_router)

    def _setup_static_routes(self):
        """Setup static file routes"""
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        # Base directory for static files
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        static_dir = os.path.join(base_dir, "static")
        well_known_dir = os.path.join(static_dir, ".well-known")

        # Mount static files
        if os.path.exists(static_dir):
            self.app.mount("/static", StaticFiles(directory=static_dir), name="static")

        # Serve .well-known files
        @self.app.get("/.well-known/agent.json")
        async def get_agent_json():
            """Serve Agent Card JSON"""
            file_path = os.path.join(well_known_dir, "agent.json")
            if os.path.exists(file_path):
                return FileResponse(file_path, media_type="application/json")
            return {"error": "agent.json not found"}

        @self.app.get("/.well-known/ai-plugin.json")
        async def get_ai_plugin_json():
            """Serve AI Plugin manifest"""
            file_path = os.path.join(well_known_dir, "ai-plugin.json")
            if os.path.exists(file_path):
                return FileResponse(file_path, media_type="application/json")
            return {"error": "ai-plugin.json not found"}

    def _setup_file_routes(self):
        """Setup file upload routes"""
        from agent_platform.media.upload import get_file_uploader
        from agent_platform.security.api_key import APIKeyInfo

        @self.app.post("/api/v1/files/upload", response_model=FileUploadResponse)
        async def upload_file(
            file: UploadFile = File(...),
            session_id: Optional[str] = None,
            expires_in_hours: int = 24,
            key_info: APIKeyInfo = Depends(get_current_api_key)
        ):
            """Upload a file"""
            uploader = get_file_uploader()
            result = await uploader.upload(
                file=file,
                user_id=key_info.user_id,
                session_id=session_id,
                expires_in_hours=expires_in_hours
            )

            return FileUploadResponse(
                file_id=result.file_id,
                filename=result.original_name,
                file_size=result.file_size,
                mime_type=result.mime_type,
                download_url=result.download_url,
                expires_at=result.expires_at
            )

    def register_routes(self):
        """Alias for setup() for backwards compatibility"""
        self.setup()


def create_platform_app(
    title: str = "AI Agent Open Platform",
    version: str = "1.0.0",
    description: str = "Open Platform for AI Agent Integration"
) -> FastAPI:
    """
    Create a new FastAPI app with platform features.

    Args:
        title: API title
        version: API version
        description: API description

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        version=version,
        description=description,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Setup platform
    platform = PlatformRouter(app)
    platform.setup()

    return app
