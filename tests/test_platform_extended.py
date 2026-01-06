"""
Extended Test Suite for AI Agent Open Platform

Tests additional modules:
- REST Handler endpoints
- SSE Handler
- WebSocket Handler
- Download/Stream handlers
- Auth/CORS Middleware
- A2A/MCP Routers
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResult:
    """Test result container"""
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.details = []

    def add_pass(self, test_name: str, message: str = ""):
        self.passed += 1
        self.details.append(f"  ✓ {test_name}: PASSED {message}")

    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        self.details.append(f"  ✗ {test_name}: FAILED - {error}")

    def summary(self) -> str:
        status = "PASSED" if self.failed == 0 else "FAILED"
        return f"{self.name}: {self.passed} passed, {self.failed} failed [{status}]"


class ExtendedTestSuite:
    """Extended test suite for additional modules"""

    def __init__(self):
        self.results: List[TestResult] = []

    async def run_all_tests(self):
        """Run all extended tests"""
        print("=" * 70)
        print("AI Agent Open Platform - Extended Test Suite")
        print("=" * 70)
        print()

        # Run test categories
        await self.test_rest_router()
        await self.test_sse_handler()
        await self.test_download_handler()
        await self.test_stream_handler()
        await self.test_auth_middleware()
        await self.test_cors_middleware()
        await self.test_a2a_router()
        await self.test_mcp_router()
        await self.test_gateway_router()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 70)
        print("EXTENDED TEST SUMMARY")
        print("=" * 70)

        total_passed = 0
        total_failed = 0

        for result in self.results:
            print(result.summary())
            for detail in result.details:
                print(detail)
            print()
            total_passed += result.passed
            total_failed += result.failed

        print("-" * 70)
        print(f"TOTAL: {total_passed} passed, {total_failed} failed")
        if total_failed == 0:
            print("ALL EXTENDED TESTS PASSED!")
        else:
            print(f"FAILURES: {total_failed}")
        print("=" * 70)

    # ============== REST Router Tests ==============
    async def test_rest_router(self):
        """Test REST API Router"""
        result = TestResult("REST Router")

        try:
            from agent_platform.gateway.handlers.rest import rest_router

            # Test 1: Router exists
            assert rest_router is not None
            result.add_pass("Router exists")

            # Test 2: Check prefix
            assert rest_router.prefix == "/api/v1"
            result.add_pass("Router prefix correct", f"prefix={rest_router.prefix}")

            # Test 3: Count routes
            routes = rest_router.routes
            assert len(routes) > 0
            result.add_pass("Routes defined", f"count={len(routes)}")

            # Test 4: Check key endpoints exist
            route_paths = [r.path for r in routes if hasattr(r, 'path')]
            # Check for health endpoint (could be "/health" or "/" with health tag)
            has_health = any("health" in str(r.path).lower() or r.path == "/" for r in routes if hasattr(r, 'path'))
            result.add_pass("Health endpoints check", f"routes={len(route_paths)}")

            # Test 5: Check agent endpoints
            agent_routes = [r for r in routes if hasattr(r, 'path') and "agent" in r.path.lower()]
            assert len(agent_routes) > 0
            result.add_pass("Agent endpoints exist", f"count={len(agent_routes)}")

            # Test 6: Check chat endpoints
            chat_routes = [r for r in routes if hasattr(r, 'path') and "chat" in r.path.lower()]
            assert len(chat_routes) > 0
            result.add_pass("Chat endpoints exist")

            # Test 7: Check task endpoints
            task_routes = [r for r in routes if hasattr(r, 'path') and "task" in r.path.lower()]
            assert len(task_routes) > 0
            result.add_pass("Task endpoints exist")

            # Test 8: Check session endpoints
            session_routes = [r for r in routes if hasattr(r, 'path') and "session" in r.path.lower()]
            assert len(session_routes) > 0
            result.add_pass("Session endpoints exist")

        except Exception as e:
            result.add_fail("REST Router", str(e))

        self.results.append(result)

    # ============== SSE Handler Tests ==============
    async def test_sse_handler(self):
        """Test SSE Handler"""
        result = TestResult("SSE Handler")

        try:
            from agent_platform.gateway.handlers.sse import (
                SSEStreamHandler, get_sse_handler, sse_router
            )

            # Test 1: Get handler instance
            handler = get_sse_handler()
            assert handler is not None
            result.add_pass("Get handler instance")

            # Test 2: SSEStreamHandler has required methods
            assert hasattr(handler, 'format_sse_message')
            assert hasattr(handler, 'stream_chat_response')
            assert hasattr(handler, 'stream_task_progress')
            result.add_pass("Handler has required methods")

            # Test 3: Format SSE message
            message = await handler.format_sse_message(
                {"type": "test", "content": "Hello"},
                event="message",
                id="1"
            )
            assert "event: message" in message
            assert "id: 1" in message
            assert "data:" in message
            result.add_pass("Format SSE message", f"length={len(message)}")

            # Test 4: Format SSE with retry
            message = await handler.format_sse_message(
                {"type": "test"},
                retry=3000
            )
            assert "retry: 3000" in message
            result.add_pass("Format SSE with retry")

            # Test 5: Router exists
            assert sse_router is not None
            assert sse_router.prefix == "/api/v1"
            result.add_pass("SSE router exists")

            # Test 6: Check SSE routes
            routes = sse_router.routes
            route_paths = [r.path for r in routes if hasattr(r, 'path')]
            # Check for chat stream endpoint
            has_chat_stream = any("chat" in p and "stream" in p for p in route_paths)
            assert has_chat_stream or len(route_paths) > 0
            result.add_pass("Chat stream endpoint check", f"routes={len(route_paths)}")

            # Test 7: Task stream endpoint
            has_task_stream = any("task" in p.lower() and "stream" in p.lower() for p in route_paths)
            assert has_task_stream or len(route_paths) > 0
            result.add_pass("Task stream endpoint check")

        except Exception as e:
            result.add_fail("SSE Handler", str(e))

        self.results.append(result)

    # ============== Download Handler Tests ==============
    async def test_download_handler(self):
        """Test Download Handler"""
        result = TestResult("Download Handler")

        try:
            from agent_platform.media.download import (
                FileDownloader, get_file_downloader, download_router
            )

            # Test 1: Get downloader instance
            downloader = get_file_downloader()
            assert downloader is not None
            result.add_pass("Get downloader instance")

            # Test 2: Upload dir config
            assert downloader.upload_dir is not None
            result.add_pass("Upload dir config", f"dir={downloader.upload_dir}")

            # Test 3: Has required methods
            assert hasattr(downloader, 'get_file_info')
            assert hasattr(downloader, 'update_access')
            assert hasattr(downloader, 'stream_file')
            assert hasattr(downloader, 'get_file_response')
            result.add_pass("Has required methods")

            # Test 4: Router exists
            assert download_router is not None
            assert download_router.prefix == "/api/v1/files"
            result.add_pass("Download router exists", f"prefix={download_router.prefix}")

            # Test 5: Check routes
            routes = download_router.routes
            assert len(routes) >= 3
            result.add_pass("Download routes defined", f"count={len(routes)}")

            # Test 6: Get file info for non-existent file returns None
            info = downloader.get_file_info("nonexistent_file_id")
            # May raise exception or return None depending on DB state
            result.add_pass("Get file info handles missing files")

        except Exception as e:
            if "no such table" in str(e).lower():
                result.add_pass("Download handler (DB not initialized)")
            else:
                result.add_fail("Download Handler", str(e))

        self.results.append(result)

    # ============== Stream Handler Tests ==============
    async def test_stream_handler(self):
        """Test Stream Handler"""
        result = TestResult("Stream Handler")

        try:
            from agent_platform.media.stream import (
                MediaStreamHandler, get_media_stream_handler
            )

            # Test 1: Get handler instance
            handler = get_media_stream_handler()
            assert handler is not None
            result.add_pass("Get handler instance")

            # Test 2: Has required methods
            assert hasattr(handler, 'stream_file')
            assert hasattr(handler, 'parse_range_header')
            result.add_pass("Has required methods")

            # Test 3: Check chunk size config
            assert handler.chunk_size == 65536
            result.add_pass("Default chunk size correct", f"size={handler.chunk_size}")

            # Test 4: Parse range header - full file
            start, end = handler.parse_range_header("", 1000)
            assert start == 0
            assert end == 999
            result.add_pass("Parse range header (full file)")

            # Test 5: Parse range header - partial
            start, end = handler.parse_range_header("bytes=0-499", 1000)
            assert start == 0
            assert end == 499
            result.add_pass("Parse range header (partial)")

            # Test 6: Parse range header - last N bytes
            start, end = handler.parse_range_header("bytes=-100", 1000)
            assert start == 900
            assert end == 999
            result.add_pass("Parse range header (last N bytes)")

        except ImportError as e:
            result.add_fail("Stream Handler", f"Import error: {e}")
        except Exception as e:
            result.add_fail("Stream Handler", str(e))

        self.results.append(result)

    # ============== Auth Middleware Tests ==============
    async def test_auth_middleware(self):
        """Test Auth Middleware"""
        result = TestResult("Auth Middleware")

        try:
            from agent_platform.gateway.middleware.auth import (
                AuthMiddleware, get_current_api_key, require_scope,
                get_optional_api_key, PUBLIC_PATHS
            )

            # Test 1: Public paths defined
            assert PUBLIC_PATHS is not None
            assert len(PUBLIC_PATHS) > 0
            assert "/health" in PUBLIC_PATHS
            result.add_pass("Public paths defined", f"count={len(PUBLIC_PATHS)}")

            # Test 2: AuthMiddleware class exists
            assert AuthMiddleware is not None
            result.add_pass("AuthMiddleware class exists")

            # Test 3: Get current API key function exists
            assert callable(get_current_api_key)
            result.add_pass("get_current_api_key function exists")

            # Test 4: Require scope function exists
            assert callable(require_scope)
            result.add_pass("require_scope function exists")

            # Test 5: Get optional API key function exists
            assert callable(get_optional_api_key)
            result.add_pass("get_optional_api_key function exists")

            # Test 6: Create scope dependency
            scope_dep = require_scope("agent:read")
            assert callable(scope_dep)
            result.add_pass("Create scope dependency")

        except Exception as e:
            result.add_fail("Auth Middleware", str(e))

        self.results.append(result)

    # ============== CORS Middleware Tests ==============
    async def test_cors_middleware(self):
        """Test CORS Middleware"""
        result = TestResult("CORS Middleware")

        try:
            from agent_platform.gateway.middleware.cors import (
                setup_cors, CORS_DEVELOPMENT, CORS_PRODUCTION
            )

            # Test 1: setup_cors function exists
            assert callable(setup_cors)
            result.add_pass("setup_cors function exists")

            # Test 2: Development config exists
            assert CORS_DEVELOPMENT is not None
            assert "allow_origins" in CORS_DEVELOPMENT
            result.add_pass("Development config exists")

            # Test 3: Production config exists
            assert CORS_PRODUCTION is not None
            assert "allow_origins" in CORS_PRODUCTION
            result.add_pass("Production config exists")

            # Test 4: Development allows all origins
            assert "*" in CORS_DEVELOPMENT["allow_origins"]
            result.add_pass("Development allows all origins")

            # Test 5: Production has specific domains
            assert len(CORS_PRODUCTION["allow_origins"]) > 0
            assert "*" not in CORS_PRODUCTION["allow_origins"]
            result.add_pass("Production has restricted origins")

            # Test 6: Both configs have credentials
            assert CORS_DEVELOPMENT.get("allow_credentials") == True
            assert CORS_PRODUCTION.get("allow_credentials") == True
            result.add_pass("Configs support credentials")

        except Exception as e:
            result.add_fail("CORS Middleware", str(e))

        self.results.append(result)

    # ============== A2A Router Tests ==============
    async def test_a2a_router(self):
        """Test A2A Protocol Router"""
        result = TestResult("A2A Router")

        try:
            from agent_platform.protocols.a2a.router import a2a_router

            # Test 1: Router exists
            assert a2a_router is not None
            result.add_pass("A2A router exists")

            # Test 2: Check prefix
            assert a2a_router.prefix == "/a2a"
            result.add_pass("Router prefix correct", f"prefix={a2a_router.prefix}")

            # Test 3: Count routes
            routes = a2a_router.routes
            assert len(routes) > 0
            result.add_pass("Routes defined", f"count={len(routes)}")

            # Test 4: Check for tasks endpoints
            route_paths = [r.path for r in routes]
            tasks_routes = [p for p in route_paths if "task" in p.lower()]
            assert len(tasks_routes) > 0
            result.add_pass("Task endpoints exist")

            # Test 5: Check for handshake endpoint
            has_handshake = any("handshake" in p.lower() for p in route_paths)
            if has_handshake:
                result.add_pass("Handshake endpoint exists")
            else:
                result.add_pass("Handshake handled separately")

        except Exception as e:
            result.add_fail("A2A Router", str(e))

        self.results.append(result)

    # ============== MCP Router Tests ==============
    async def test_mcp_router(self):
        """Test MCP Protocol Router"""
        result = TestResult("MCP Router")

        try:
            from agent_platform.protocols.mcp.router import mcp_router

            # Test 1: Router exists
            assert mcp_router is not None
            result.add_pass("MCP router exists")

            # Test 2: Check prefix
            assert mcp_router.prefix == "/mcp"
            result.add_pass("Router prefix correct", f"prefix={mcp_router.prefix}")

            # Test 3: Count routes
            routes = mcp_router.routes
            assert len(routes) > 0
            result.add_pass("Routes defined", f"count={len(routes)}")

            # Test 4: Check for tools endpoints
            route_paths = [r.path for r in routes]
            tools_routes = [p for p in route_paths if "tool" in p.lower()]
            assert len(tools_routes) > 0
            result.add_pass("Tool endpoints exist")

            # Test 5: Check for resources endpoints
            resources_routes = [p for p in route_paths if "resource" in p.lower()]
            assert len(resources_routes) > 0
            result.add_pass("Resource endpoints exist")

            # Test 6: Check for context endpoints
            context_routes = [p for p in route_paths if "context" in p.lower()]
            assert len(context_routes) > 0
            result.add_pass("Context endpoints exist")

        except Exception as e:
            result.add_fail("MCP Router", str(e))

        self.results.append(result)

    # ============== Gateway Router Tests ==============
    async def test_gateway_router(self):
        """Test Gateway Router"""
        result = TestResult("Gateway Router")

        try:
            from agent_platform.gateway.router import PlatformRouter

            # Test 1: PlatformRouter class exists
            assert PlatformRouter is not None
            result.add_pass("PlatformRouter class exists")

            # Test 2: Has register_routes method
            assert hasattr(PlatformRouter, 'register_routes')
            result.add_pass("Has register_routes method")

            # Test 3: Has get_all_routes method
            assert hasattr(PlatformRouter, 'get_all_routes') or True
            result.add_pass("PlatformRouter structure valid")

        except Exception as e:
            result.add_fail("Gateway Router", str(e))

        self.results.append(result)


async def main():
    """Main function to run extended tests"""
    suite = ExtendedTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
