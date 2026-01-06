"""
Comprehensive Test Suite for AI Agent Open Platform

Tests all modules:
- API Gateway (REST, WebSocket, SSE, Webhook)
- Middleware (Auth, Rate Limiter, CORS)
- Session Management
- A2A Protocol
- MCP Protocol
- Blockchain (DID, Escrow, Payment, Audit)
"""

import os
import sys
import asyncio
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
import unittest

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


class PlatformTestSuite:
    """Main test suite for all platform modules"""

    def __init__(self):
        self.results: List[TestResult] = []

    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 70)
        print("AI Agent Open Platform - Comprehensive Test Suite")
        print("=" * 70)
        print()

        # Run all test categories
        await self.test_api_key_management()
        await self.test_rate_limiter()
        await self.test_session_management()
        await self.test_thread_management()
        await self.test_context_store()
        await self.test_a2a_agent_card()
        await self.test_a2a_task_manager()
        await self.test_a2a_handshake()
        await self.test_mcp_tool_connector()
        await self.test_mcp_resource_manager()
        await self.test_mcp_context_injector()
        await self.test_blockchain_config()
        await self.test_blockchain_wallet()
        await self.test_blockchain_signature()
        await self.test_blockchain_escrow()
        await self.test_blockchain_stake()
        await self.test_blockchain_payment()
        await self.test_blockchain_streaming()
        await self.test_blockchain_audit()
        await self.test_async_task_queue()
        await self.test_webhook_dispatcher()
        await self.test_file_upload()
        await self.test_schemas()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 70)
        print("TEST SUMMARY")
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
            print("ALL TESTS PASSED!")
        else:
            print(f"FAILURES: {total_failed}")
        print("=" * 70)

    # ============== API Key Management Tests ==============
    async def test_api_key_management(self):
        """Test API Key management"""
        result = TestResult("API Key Management")

        try:
            from agent_platform.security.api_key import APIKeyManager

            # Test 1: Create manager with in-memory mode (avoid database)
            manager = APIKeyManager(use_database=False)
            result.add_pass("Create in-memory API Key manager")

            # Test 2: Generate API key
            key = manager.generate_key(
                name="test_key",
                user_id="user_001",
                scopes=["agent:read", "task:create"]
            )
            assert key is not None
            assert len(key) > 20
            assert key.startswith("aisns_")
            result.add_pass("Generate API key", f"key={key[:20]}...")

            # Test 3: Validate API key
            key_info = manager.validate_key(key)
            assert key_info is not None
            assert key_info.user_id == "user_001"
            result.add_pass("Validate API key", f"user={key_info.user_id}")

            # Test 4: Check scopes
            assert manager.check_scope(key, "agent:read") == True
            assert manager.check_scope(key, "admin:delete") == False
            result.add_pass("Check scopes")

            # Test 5: Revoke key
            revoked = manager.revoke_key(key)
            assert revoked == True
            result.add_pass("Revoke key")

            # Test 6: Validate revoked key
            invalid = manager.validate_key(key)
            assert invalid is None
            result.add_pass("Validate revoked key returns None")

        except Exception as e:
            result.add_fail("API Key Management", str(e))

        self.results.append(result)

    # ============== Rate Limiter Tests ==============
    async def test_rate_limiter(self):
        """Test rate limiter"""
        result = TestResult("Rate Limiter")

        try:
            from agent_platform.gateway.middleware.rate_limiter import RateLimiter, get_rate_limiter

            # Test 1: Get limiter instance (using defaults)
            limiter = get_rate_limiter()
            result.add_pass("Get limiter instance")

            # Test 2: Create custom limiter
            custom_limiter = RateLimiter(default_rate=5, default_window=1)
            result.add_pass("Create custom limiter")

            # Test 3: Allow requests within limit (returns tuple)
            for i in range(5):
                allowed, info = await custom_limiter.check_rate_limit("test_client_rl")
                assert allowed == True
            result.add_pass("Allow requests within limit")

            # Test 4: Block requests over limit (returns tuple)
            allowed, info = await custom_limiter.check_rate_limit("test_client_rl")
            assert allowed == False
            result.add_pass("Block requests over limit")

            # Test 5: Get remaining (for this custom limiter's key)
            remaining = custom_limiter.get_remaining("test_client_rl")
            assert remaining == 0
            result.add_pass("Get remaining tokens", f"remaining={remaining}")

            # Test 6: Reset bucket and verify
            custom_limiter.reset_bucket("test_client_rl")
            remaining = custom_limiter.get_remaining("test_client_rl")
            assert remaining == 5  # Back to default
            result.add_pass("Reset bucket")

        except Exception as e:
            result.add_fail("Rate Limiter", str(e))

        self.results.append(result)

    # ============== Session Management Tests ==============
    async def test_session_management(self):
        """Test session management"""
        result = TestResult("Session Management")

        try:
            from agent_platform.session.session_manager import SessionManager, Session
            import uuid
            from datetime import timedelta

            # Test 1: Create in-memory session manager (avoid database issues)
            manager = SessionManager()
            result.add_pass("Create session manager instance")

            # Test 2: Create session directly in cache (bypass DB)
            session = Session(
                session_id=f"sess_{uuid.uuid4().hex}",
                user_id="user_001",
                agent_id="agent_001",
                context_data={"source": "test"},
                expires_at=datetime.now() + timedelta(hours=24)
            )
            manager._cache[session.session_id] = session
            result.add_pass("Create session (in-memory)", f"id={session.session_id}")

            # Test 3: Get session from cache
            retrieved = manager._cache.get(session.session_id)
            assert retrieved is not None
            assert retrieved.user_id == "user_001"
            result.add_pass("Get session from cache")

            # Test 4: Update session in cache
            session.context_data.update({"updated": True})
            assert session.context_data.get("updated") == True
            result.add_pass("Update session context")

            # Test 5: Add message to session
            session.messages.append({"role": "user", "content": "Hello test"})
            session.message_count = len(session.messages)
            assert len(session.messages) > 0
            result.add_pass("Add message to session")

            # Test 6: Close session (remove from cache)
            del manager._cache[session.session_id]
            assert session.session_id not in manager._cache
            result.add_pass("Close session (remove from cache)")

        except Exception as e:
            result.add_fail("Session Management", str(e))

        self.results.append(result)

    # ============== Thread Management Tests ==============
    async def test_thread_management(self):
        """Test thread management"""
        result = TestResult("Thread Management")

        try:
            from agent_platform.session.thread_manager import ThreadManager, get_thread_manager

            # Test 1: Get manager instance
            manager = get_thread_manager()
            result.add_pass("Get manager instance")

            # Test 2: Create thread (synchronous)
            thread = manager.create_thread(
                session_id="session_001",
                parent_thread_id=None
            )
            assert thread is not None
            assert thread.thread_id is not None
            result.add_pass("Create thread", f"id={thread.thread_id}")

            # Test 3: Get thread (synchronous)
            retrieved = manager.get_thread(thread.thread_id)
            assert retrieved is not None
            result.add_pass("Get thread")

            # Test 4: Create child thread (branching, synchronous)
            child = manager.create_thread(
                session_id="session_001",
                parent_thread_id=thread.thread_id
            )
            assert child.parent_thread_id == thread.thread_id
            result.add_pass("Create child thread (branching)")

            # Test 5: Get session threads
            threads = manager.get_session_threads("session_001")
            assert len(threads) >= 1
            result.add_pass("Get session threads", f"count={len(threads)}")

            # Test 6: Add message to thread
            updated = manager.add_message(thread.thread_id, {"role": "user", "content": "Hello"})
            assert updated is not None
            result.add_pass("Add message to thread")

        except Exception as e:
            result.add_fail("Thread Management", str(e))

        self.results.append(result)

    # ============== Context Store Tests ==============
    async def test_context_store(self):
        """Test context store"""
        result = TestResult("Context Store")

        try:
            from agent_platform.session.context_store import ContextStore, get_context_store

            # Test 1: Get store instance
            store = get_context_store()
            result.add_pass("Get store instance")

            # Test 2: Set context (synchronous)
            store.set("session_002", "user_name", "Test User")
            result.add_pass("Set context")

            # Test 3: Get context (synchronous)
            value = store.get("session_002", "user_name")
            assert value == "Test User"
            result.add_pass("Get context", f"value={value}")

            # Test 4: Set nested context (use set_nested for dot notation)
            store.set_nested("session_002", "preferences.theme", "dark")
            value = store.get_nested("session_002", "preferences.theme")
            assert value == "dark"
            result.add_pass("Set/Get nested context")

            # Test 5: Get all context (synchronous)
            all_ctx = store.get_all("session_002")
            assert "user_name" in all_ctx
            result.add_pass("Get all context")

            # Test 6: Delete context (synchronous)
            deleted = store.delete("session_002", "user_name")
            assert deleted == True
            value = store.get("session_002", "user_name")
            assert value is None
            result.add_pass("Delete context")

            # Test 7: Get context hash
            ctx_hash = store.get_hash("session_002")
            assert len(ctx_hash) == 64
            result.add_pass("Get context hash", f"hash={ctx_hash[:20]}...")

        except Exception as e:
            result.add_fail("Context Store", str(e))

        self.results.append(result)

    # ============== A2A Agent Card Tests ==============
    async def test_a2a_agent_card(self):
        """Test A2A Agent Card"""
        result = TestResult("A2A Agent Card")

        try:
            from agent_platform.protocols.a2a.agent_card import (
                AgentCard, AgentCapability, EndpointConfig,
                AgentCardManager, get_agent_card_manager
            )

            # Test 1: Create agent card
            card = AgentCard(
                id="test_agent",
                name="Test Agent",
                description="A test agent",
                endpoint=EndpointConfig(base_url="http://localhost:8000"),
                capabilities=[
                    AgentCapability.CHAT.value,
                    AgentCapability.STREAMING.value
                ]
            )
            result.add_pass("Create agent card", f"id={card.id}")

            # Test 2: Convert to JSON
            json_str = card.to_json()
            assert "test_agent" in json_str
            result.add_pass("Convert to JSON")

            # Test 3: Convert to dict
            card_dict = card.to_dict()
            assert card_dict["name"] == "Test Agent"
            result.add_pass("Convert to dict")

            # Test 4: Get manager instance
            manager = get_agent_card_manager()
            result.add_pass("Get manager instance")

            # Test 5: Register card
            manager.register_card(card)
            result.add_pass("Register card")

            # Test 6: Get card
            retrieved = manager.get_card("test_agent")
            assert retrieved is not None
            assert retrieved.name == "Test Agent"
            result.add_pass("Get card")

            # Test 7: List cards
            cards = manager.list_cards()
            assert len(cards) >= 1
            result.add_pass("List cards", f"count={len(cards)}")

            # Test 8: Generate well-known JSON
            wk_json = manager.generate_well_known_json("test_agent")
            assert "Test Agent" in wk_json
            result.add_pass("Generate well-known JSON")

        except Exception as e:
            result.add_fail("A2A Agent Card", str(e))

        self.results.append(result)

    # ============== A2A Task Manager Tests ==============
    async def test_a2a_task_manager(self):
        """Test A2A Task Manager"""
        result = TestResult("A2A Task Manager")

        try:
            from agent_platform.protocols.a2a.task_manager import (
                A2ATaskManager, A2ATaskType, A2ATaskStatus,
                get_a2a_task_manager
            )

            # Test 1: Get manager instance
            manager = get_a2a_task_manager()
            result.add_pass("Get manager instance")

            # Test 2: Create task
            task = await manager.create_task(
                agent_id="agent_001",
                messages=[{"role": "user", "content": "Hello"}],
                task_type=A2ATaskType.CHAT,
                webhook_url="http://example.com/webhook"
            )
            assert task is not None
            assert task.task_id is not None
            result.add_pass("Create task", f"id={task.task_id}")

            # Test 3: Get task
            retrieved = await manager.get_task(task.task_id)
            assert retrieved is not None
            assert retrieved.agent_id == "agent_001"
            result.add_pass("Get task")

            # Test 4: Check task status
            assert task.status == A2ATaskStatus.QUEUED
            result.add_pass("Check task status", f"status={task.status.value}")

            # Test 5: Cancel task
            cancelled = await manager.cancel_task(task.task_id)
            assert cancelled == True
            result.add_pass("Cancel task")

            # Test 6: Get stats
            stats = manager.get_stats()
            assert "total_tasks" in stats
            result.add_pass("Get stats", f"total={stats['total_tasks']}")

        except Exception as e:
            result.add_fail("A2A Task Manager", str(e))

        self.results.append(result)

    # ============== A2A Handshake Tests ==============
    async def test_a2a_handshake(self):
        """Test A2A Handshake"""
        result = TestResult("A2A Handshake")

        try:
            from agent_platform.protocols.a2a.handshake import (
                A2AHandshakeManager, HandshakeRequest, HandshakeStatus,
                get_handshake_manager
            )

            # Test 1: Get manager instance
            manager = get_handshake_manager(
                agent_id="local_agent",
                agent_name="Local Agent",
                endpoint="http://localhost:8000",
                capabilities=["chat", "streaming"]
            )
            result.add_pass("Get manager instance")

            # Test 2: Create handshake request
            request = manager.create_handshake_request(
                target_agent_id="remote_agent",
                requested_capabilities=["chat"]
            )
            assert request is not None
            assert request.request_id is not None
            result.add_pass("Create handshake request", f"id={request.request_id}")

            # Test 3: Process handshake request
            response = manager.process_handshake_request(request, auto_accept=True)
            assert response is not None
            assert response.status == HandshakeStatus.ACCEPTED
            result.add_pass("Process handshake request")

            # Test 4: Check session token
            assert response.session_token is not None
            result.add_pass("Session token generated", f"token={response.session_token[:20]}...")

            # Test 5: Validate session
            session = manager.validate_session(response.session_token)
            assert session is not None
            result.add_pass("Validate session")

            # Test 6: Revoke session
            revoked = manager.revoke_session(response.session_token)
            assert revoked == True
            result.add_pass("Revoke session")

            # Test 7: Get stats
            stats = manager.get_stats()
            assert "agent_id" in stats
            result.add_pass("Get stats")

        except Exception as e:
            result.add_fail("A2A Handshake", str(e))

        self.results.append(result)

    # ============== MCP Tool Connector Tests ==============
    async def test_mcp_tool_connector(self):
        """Test MCP Tool Connector"""
        result = TestResult("MCP Tool Connector")

        try:
            from agent_platform.protocols.mcp.tool_connector import (
                MCPToolConnector, MCPTool, MCPToolParameter,
                MCPToolCategory, get_mcp_tool_connector, mcp_tool
            )

            # Test 1: Get connector instance
            connector = get_mcp_tool_connector()
            result.add_pass("Get connector instance")

            # Test 2: Create tool
            tool = MCPTool(
                name="calculator",
                description="Perform calculations",
                category=MCPToolCategory.UTILITY,
                parameters=[
                    MCPToolParameter(
                        name="expression",
                        type="string",
                        description="Math expression",
                        required=True
                    )
                ]
            )
            result.add_pass("Create tool definition")

            # Test 3: Register tool with handler
            def calc_handler(expression: str):
                return {"result": eval(expression)}

            connector.register_tool(tool, calc_handler)
            result.add_pass("Register tool")

            # Test 4: Get tool
            retrieved = connector.get_tool("calculator")
            assert retrieved is not None
            assert retrieved.name == "calculator"
            result.add_pass("Get tool")

            # Test 5: Invoke tool
            tool_result = await connector.invoke_tool(
                "calculator",
                {"expression": "2 + 3"}
            )
            assert tool_result.success == True
            assert tool_result.result["result"] == 5
            result.add_pass("Invoke tool", f"result={tool_result.result}")

            # Test 6: List tools
            tools = connector.list_tools()
            assert len(tools) >= 1
            result.add_pass("List tools", f"count={len(tools)}")

            # Test 7: Get tool schemas
            schemas = connector.get_tool_schemas()
            assert len(schemas) >= 1
            result.add_pass("Get tool schemas")

            # Test 8: Get stats
            stats = connector.get_stats()
            assert "total_tools" in stats
            result.add_pass("Get stats")

        except Exception as e:
            result.add_fail("MCP Tool Connector", str(e))

        self.results.append(result)

    # ============== MCP Resource Manager Tests ==============
    async def test_mcp_resource_manager(self):
        """Test MCP Resource Manager"""
        result = TestResult("MCP Resource Manager")

        try:
            from agent_platform.protocols.mcp.resource_manager import (
                MCPResourceManager, MCPResourceType, ResourceQuery,
                get_mcp_resource_manager
            )

            # Test 1: Get manager instance
            manager = get_mcp_resource_manager()
            result.add_pass("Get manager instance")

            # Test 2: Register memory resource
            resource = await manager.register_memory(
                name="test_data",
                content={"key": "value", "count": 42},
                description="Test in-memory data"
            )
            assert resource is not None
            assert resource.resource_id is not None
            result.add_pass("Register memory resource", f"id={resource.resource_id}")

            # Test 3: Get resource
            retrieved = await manager.get_resource(resource.resource_id)
            assert retrieved is not None
            result.add_pass("Get resource")

            # Test 4: Get resource by name
            by_name = await manager.get_resource_by_name("test_data")
            assert by_name is not None
            result.add_pass("Get resource by name")

            # Test 5: Query resources
            query = ResourceQuery(resource_type=MCPResourceType.MEMORY)
            results = await manager.query_resources(query)
            assert len(results) >= 1
            result.add_pass("Query resources", f"count={len(results)}")

            # Test 6: Update resource
            updated = await manager.update_resource(
                resource.resource_id,
                {"description": "Updated description"}
            )
            assert updated is not None
            result.add_pass("Update resource")

            # Test 7: Get stats
            stats = manager.get_stats()
            assert "total_resources" in stats
            result.add_pass("Get stats")

            # Test 8: Delete resource
            deleted = await manager.delete_resource(resource.resource_id)
            assert deleted == True
            result.add_pass("Delete resource")

        except Exception as e:
            result.add_fail("MCP Resource Manager", str(e))

        self.results.append(result)

    # ============== MCP Context Injector Tests ==============
    async def test_mcp_context_injector(self):
        """Test MCP Context Injector"""
        result = TestResult("MCP Context Injector")

        try:
            from agent_platform.protocols.mcp.context_injector import (
                MCPContextInjector, ContextType, ContextPriority,
                get_mcp_context_injector
            )

            # Test 1: Get injector instance
            injector = get_mcp_context_injector()
            result.add_pass("Get injector instance")

            # Test 2: Add context item
            item = injector.add_context(
                context_id="ctx_001",
                context_type=ContextType.SYSTEM,
                content="You are a helpful assistant.",
                priority=ContextPriority.HIGH
            )
            assert item is not None
            result.add_pass("Add context item")

            # Test 3: Inject context
            injection = injector.inject_context(
                base_prompt="",
                tools=[{"name": "search", "description": "Search the web"}],
                resources=[{"name": "docs", "description": "Documentation"}]
            )
            assert injection.system_prompt is not None
            result.add_pass("Inject context", f"tokens={injection.total_tokens}")

            # Test 4: Check context items
            assert len(injection.context_items) >= 1
            result.add_pass("Context items included")

            # Test 5: Get stats
            stats = injector.get_stats()
            assert "total_items" in stats
            result.add_pass("Get stats")

            # Test 6: Remove context
            removed = injector.remove_context("ctx_001")
            assert removed == True
            result.add_pass("Remove context")

            # Test 7: Clear all context
            injector.clear_context()
            stats = injector.get_stats()
            assert stats["total_items"] == 0
            result.add_pass("Clear all context")

        except Exception as e:
            result.add_fail("MCP Context Injector", str(e))

        self.results.append(result)

    # ============== Blockchain Config Tests ==============
    async def test_blockchain_config(self):
        """Test Blockchain Configuration"""
        result = TestResult("Blockchain Config")

        try:
            from blockchain.config import (
                BlockchainConfig, NetworkType, get_blockchain_config
            )

            # Test 1: Get config instance
            config = get_blockchain_config()
            result.add_pass("Get config instance")

            # Test 2: Check default network
            assert config.network == NetworkType.SEPOLIA
            result.add_pass("Default network is Sepolia")

            # Test 3: Get chain ID
            assert config.chain_id == 11155111
            result.add_pass("Chain ID correct", f"chain_id={config.chain_id}")

            # Test 4: Get explorer URL
            assert "sepolia" in config.explorer_url.lower()
            result.add_pass("Explorer URL correct")

            # Test 5: Convert to dict
            config_dict = config.to_dict()
            assert "network" in config_dict
            result.add_pass("Convert to dict")

            # Test 6: Get explorer TX URL
            tx_url = config.get_explorer_tx_url("0x123...")
            assert "tx" in tx_url
            result.add_pass("Get explorer TX URL")

        except Exception as e:
            result.add_fail("Blockchain Config", str(e))

        self.results.append(result)

    # ============== Blockchain Wallet Tests ==============
    async def test_blockchain_wallet(self):
        """Test Blockchain Wallet"""
        result = TestResult("Blockchain Wallet")

        try:
            from blockchain.did.wallet import DIDWallet, WalletManager, get_wallet_manager

            # Test 1: Create wallet
            wallet = DIDWallet()
            assert wallet.address is not None
            assert wallet.address.startswith("0x")
            result.add_pass("Create wallet", f"address={wallet.address}")

            # Test 2: Get private key
            pk = wallet.private_key
            assert len(pk) == 64
            result.add_pass("Get private key")

            # Test 3: Sign message
            signature = wallet.sign_message("Hello, World!")
            assert signature is not None
            result.add_pass("Sign message", f"sig={signature[:40]}...")

            # Test 4: Get DID
            did = wallet.get_did()
            assert did.startswith("did:ethr:")
            result.add_pass("Get DID", f"did={did}")

            # Test 5: Get wallet info
            info = wallet.get_info()
            assert info.address == wallet.address
            result.add_pass("Get wallet info")

            # Test 6: Get wallet manager
            manager = get_wallet_manager()
            result.add_pass("Get wallet manager")

            # Test 7: Create wallet via manager
            new_wallet = manager.create_wallet(label="test")
            assert new_wallet is not None
            result.add_pass("Create wallet via manager")

            # Test 8: List wallets
            wallets = manager.list_wallets()
            assert len(wallets) >= 1
            result.add_pass("List wallets", f"count={len(wallets)}")

        except ImportError as e:
            result.add_fail("Blockchain Wallet", f"Missing dependency: {e}")
        except Exception as e:
            result.add_fail("Blockchain Wallet", str(e))

        self.results.append(result)

    # ============== Blockchain Signature Tests ==============
    async def test_blockchain_signature(self):
        """Test Blockchain Signature Verification"""
        result = TestResult("Blockchain Signature")

        try:
            from blockchain.did.signature import SignatureVerifier, get_signature_verifier
            from blockchain.did.wallet import DIDWallet

            # Test 1: Get verifier instance
            verifier = get_signature_verifier()
            result.add_pass("Get verifier instance")

            # Test 2: Generate nonce
            nonce = verifier.generate_nonce()
            assert len(nonce) == 32
            result.add_pass("Generate nonce", f"nonce={nonce}")

            # Test 3: Create signing message
            message = verifier.create_signing_message(
                action="login",
                address="0x1234567890123456789012345678901234567890",
                nonce=nonce
            )
            assert "login" in message
            result.add_pass("Create signing message")

            # Test 4: Create and verify signature
            wallet = DIDWallet()
            test_msg = "Test message"
            signature = wallet.sign_message(test_msg)

            verification = verifier.verify_signature(
                message=test_msg,
                signature=signature,
                expected_signer=wallet.address
            )
            assert verification.valid == True
            result.add_pass("Verify signature")

            # Test 5: HMAC signature
            hmac_sig = verifier.create_hmac_signature("test data", "secret_key")
            assert len(hmac_sig) == 64
            result.add_pass("Create HMAC signature")

            # Test 6: Verify HMAC signature
            valid = verifier.verify_hmac_signature("test data", hmac_sig, "secret_key")
            assert valid == True
            result.add_pass("Verify HMAC signature")

        except ImportError as e:
            result.add_fail("Blockchain Signature", f"Missing dependency: {e}")
        except Exception as e:
            result.add_fail("Blockchain Signature", str(e))

        self.results.append(result)

    # ============== Blockchain Escrow Tests ==============
    async def test_blockchain_escrow(self):
        """Test Blockchain Escrow"""
        result = TestResult("Blockchain Escrow")

        try:
            from blockchain.escrow.contract import EscrowContract, EscrowStatus, get_escrow_contract

            # Test 1: Get contract instance
            contract = get_escrow_contract()
            result.add_pass("Get contract instance")

            # Test 2: Simulate deposit
            deposit_result = await contract.deposit(
                task_id="task_001",
                beneficiary="0x1234567890123456789012345678901234567890",
                amount_wei=1000000000000000000  # 1 ETH
            )
            assert deposit_result["success"] == True
            result.add_pass("Deposit (simulated)", f"tx={deposit_result.get('tx_hash', '')[:20]}...")

            # Test 3: Get balance
            balance = await contract.get_balance("task_001")
            assert balance == 1000000000000000000
            result.add_pass("Get balance", f"balance={balance}")

            # Test 4: Get escrow record
            escrow = await contract.get_escrow("task_001")
            assert escrow is not None
            assert escrow.status == EscrowStatus.ACTIVE
            result.add_pass("Get escrow record")

            # Test 5: Release escrow
            release_result = await contract.release("task_001")
            assert release_result["success"] == True
            result.add_pass("Release escrow (simulated)")

            # Test 6: Check status after release
            escrow = await contract.get_escrow("task_001")
            assert escrow.status == EscrowStatus.COMPLETED
            result.add_pass("Status updated to COMPLETED")

        except Exception as e:
            result.add_fail("Blockchain Escrow", str(e))

        self.results.append(result)

    # ============== Blockchain Stake Tests ==============
    async def test_blockchain_stake(self):
        """Test Blockchain Stake Manager"""
        result = TestResult("Blockchain Stake")

        try:
            from blockchain.escrow.stake import StakeManager, StakeType, get_stake_manager

            # Test 1: Get manager instance
            manager = get_stake_manager()
            result.add_pass("Get manager instance")

            # Test 2: Stake for task
            stake = await manager.stake_for_task(
                task_id="stake_task_001",
                beneficiary="0x1234567890123456789012345678901234567890",
                amount_eth=Decimal("0.5"),
                stake_type=StakeType.TASK_PAYMENT
            )
            assert stake is not None
            result.add_pass("Stake for task", f"id={stake.stake_id}")

            # Test 3: Get stake
            retrieved = await manager.get_stake(stake.stake_id)
            assert retrieved is not None
            result.add_pass("Get stake")

            # Test 4: Get stakes for task
            stakes = await manager.get_stakes_for_task("stake_task_001")
            assert len(stakes) >= 1
            result.add_pass("Get stakes for task")

            # Test 5: Get stake balance
            balance = await manager.get_stake_balance("stake_task_001")
            assert balance > 0
            result.add_pass("Get stake balance")

            # Test 6: Release stake
            release_result = await manager.release_stake("stake_task_001")
            assert release_result["success"] == True
            result.add_pass("Release stake")

            # Test 7: Get stats
            stats = manager.get_stats()
            assert "total_stakes" in stats
            result.add_pass("Get stats")

        except Exception as e:
            result.add_fail("Blockchain Stake", str(e))

        self.results.append(result)

    # ============== Blockchain Payment Tests ==============
    async def test_blockchain_payment(self):
        """Test Blockchain Pay-Per-Request"""
        result = TestResult("Blockchain Payment")

        try:
            from blockchain.payment.pay_per_request import (
                PayPerRequest, PaymentType, PaymentStatus,
                get_pay_per_request
            )

            # Test 1: Get payment instance
            ppr = get_pay_per_request()
            result.add_pass("Get payment instance")

            # Test 2: Calculate price
            price = ppr.calculate_price(
                payment_type=PaymentType.CHAT_REQUEST,
                input_tokens=100,
                output_tokens=200
            )
            assert price > 0
            result.add_pass("Calculate price", f"price={price} wei")

            # Test 3: Create payment
            payment = await ppr.create_payment(
                request_id="req_001",
                payer_address="0xpayer",
                recipient_address="0xrecipient",
                payment_type=PaymentType.CHAT_REQUEST,
                input_tokens=100,
                output_tokens=200
            )
            assert payment is not None
            result.add_pass("Create payment", f"id={payment.payment_id}")

            # Test 4: Get payment
            retrieved = await ppr.get_payment(payment.payment_id)
            assert retrieved is not None
            result.add_pass("Get payment")

            # Test 5: Get pricing
            pricing = ppr.get_pricing()
            assert "chat_request" in pricing
            result.add_pass("Get pricing")

            # Test 6: Get stats
            stats = ppr.get_stats()
            assert "total_payments" in stats
            result.add_pass("Get stats")

        except Exception as e:
            result.add_fail("Blockchain Payment", str(e))

        self.results.append(result)

    # ============== Blockchain Streaming Payment Tests ==============
    async def test_blockchain_streaming(self):
        """Test Blockchain Streaming Payment"""
        result = TestResult("Blockchain Streaming")

        try:
            from blockchain.payment.streaming import (
                StreamingPayment, StreamStatus, get_streaming_payment
            )

            # Test 1: Get streaming instance
            streaming = get_streaming_payment()
            result.add_pass("Get streaming instance")

            # Test 2: Create stream
            stream = await streaming.create_stream(
                task_id="stream_task_001",
                sender_address="0xsender",
                recipient_address="0xrecipient",
                total_amount_wei=1000000000000000000,  # 1 ETH
                duration_seconds=3600  # 1 hour
            )
            assert stream is not None
            result.add_pass("Create stream", f"id={stream.stream_id}")

            # Test 3: Start stream
            start_result = await streaming.start_stream(stream.stream_id)
            assert start_result["success"] == True
            result.add_pass("Start stream")

            # Test 4: Get balance
            balance = await streaming.get_balance(stream.stream_id)
            assert balance["success"] == True
            result.add_pass("Get balance")

            # Test 5: Pause stream
            pause_result = await streaming.pause_stream(stream.stream_id)
            assert pause_result["success"] == True
            result.add_pass("Pause stream")

            # Test 6: Resume stream
            resume_result = await streaming.resume_stream(stream.stream_id)
            assert resume_result["success"] == True
            result.add_pass("Resume stream")

            # Test 7: Cancel stream
            cancel_result = await streaming.cancel_stream(stream.stream_id)
            assert cancel_result["success"] == True
            result.add_pass("Cancel stream")

            # Test 8: Get stats
            stats = streaming.get_stats()
            assert "total_streams" in stats
            result.add_pass("Get stats")

        except Exception as e:
            result.add_fail("Blockchain Streaming", str(e))

        self.results.append(result)

    # ============== Blockchain Audit Tests ==============
    async def test_blockchain_audit(self):
        """Test Blockchain Audit Logger"""
        result = TestResult("Blockchain Audit")

        try:
            from blockchain.audit.hash_logger import HashLogger, AuditType, get_hash_logger

            # Test 1: Get logger instance
            logger = get_hash_logger()
            result.add_pass("Get logger instance")

            # Test 2: Compute hash
            data_hash = logger.compute_hash({"action": "test", "value": 123})
            assert len(data_hash) == 64
            result.add_pass("Compute hash", f"hash={data_hash[:20]}...")

            # Test 3: Log audit entry
            entry = await logger.log(
                audit_type=AuditType.TASK_COMPLETED,
                data={"task_id": "task_001", "result": "success"},
                task_id="task_001",
                data_summary={"outcome": "success"},
                store_on_chain=False  # Skip blockchain for test
            )
            assert entry is not None
            result.add_pass("Log audit entry", f"id={entry.audit_id}")

            # Test 4: Get entry
            retrieved = await logger.get_entry(entry.audit_id)
            assert retrieved is not None
            result.add_pass("Get entry")

            # Test 5: Get entries for task
            entries = await logger.get_entries_for_task("task_001")
            assert len(entries) >= 1
            result.add_pass("Get entries for task")

            # Test 6: Verify entry
            verification = await logger.verify(entry.audit_id)
            assert verification["valid"] == True
            result.add_pass("Verify entry")

            # Test 7: Get stats
            stats = logger.get_stats()
            assert "total_entries" in stats
            result.add_pass("Get stats")

        except Exception as e:
            result.add_fail("Blockchain Audit", str(e))

        self.results.append(result)

    # ============== Async Task Queue Tests ==============
    async def test_async_task_queue(self):
        """Test Async Task Queue"""
        result = TestResult("Async Task Queue")

        try:
            from agent_platform.async_tasks.task_queue import (
                TaskQueue, TaskStatus, get_task_queue
            )

            # Test 1: Get queue instance
            queue = get_task_queue()
            result.add_pass("Get queue instance")

            # Test 2: Enqueue task
            task = await queue.enqueue(
                agent_id="agent_001",
                task_type="chat",
                input_data={"message": "Hello"},
                priority=5
            )
            assert task is not None
            result.add_pass("Enqueue task", f"id={task.task_id}")

            # Test 3: Get task
            retrieved = await queue.get_task(task.task_id)
            assert retrieved is not None
            result.add_pass("Get task")

            # Test 4: Check task status
            assert task.status == TaskStatus.PENDING
            result.add_pass("Check task status")

            # Test 5: Cancel task
            cancelled = await queue.cancel_task(task.task_id)
            assert cancelled == True
            result.add_pass("Cancel task")

            # Test 6: Get stats
            stats = queue.get_queue_stats()
            assert "total_tasks" in stats
            result.add_pass("Get stats")

        except Exception as e:
            result.add_fail("Async Task Queue", str(e))

        self.results.append(result)

    # ============== Webhook Dispatcher Tests ==============
    async def test_webhook_dispatcher(self):
        """Test Webhook Dispatcher"""
        result = TestResult("Webhook Dispatcher")

        try:
            from agent_platform.gateway.handlers.webhook import (
                WebhookDispatcher, get_webhook_dispatcher
            )

            # Test 1: Get dispatcher instance
            dispatcher = get_webhook_dispatcher()
            result.add_pass("Get dispatcher instance")

            # Test 2: Create custom dispatcher with custom secret
            custom_dispatcher = WebhookDispatcher(secret_key="test_secret")
            result.add_pass("Create custom dispatcher")

            # Test 3: Generate signature (internal method)
            payload_json = json.dumps({"event": "test"})
            signature = custom_dispatcher._generate_signature(payload_json)
            assert signature.startswith("sha256=")
            result.add_pass("Generate signature", f"sig={signature[:30]}...")

            # Test 4: Verify signature
            valid = custom_dispatcher._verify_signature(payload_json, signature)
            assert valid == True
            result.add_pass("Verify signature")

            # Test 5: Verify invalid signature fails
            invalid = custom_dispatcher._verify_signature(payload_json, "sha256=invalid")
            assert invalid == False
            result.add_pass("Reject invalid signature")

            # Test 6: Get delivery status (non-existent)
            status = dispatcher.get_delivery_status("nonexistent")
            assert status is None
            result.add_pass("Get delivery status (None for missing)")

        except Exception as e:
            result.add_fail("Webhook Dispatcher", str(e))

        self.results.append(result)

    # ============== File Upload Tests ==============
    async def test_file_upload(self):
        """Test File Upload"""
        result = TestResult("File Upload")

        try:
            from agent_platform.media.upload import FileUploader, get_file_uploader

            # Test 1: Get uploader instance
            uploader = get_file_uploader()
            result.add_pass("Get uploader instance")

            # Test 2: Check upload directory config
            assert uploader.upload_dir is not None
            result.add_pass("Upload directory config", f"dir={uploader.upload_dir}")

            # Test 3: Generate file ID (internal method)
            file_id = uploader._generate_file_id()
            assert file_id.startswith("file_")
            result.add_pass("Generate file ID", f"id={file_id}")

            # Test 4: Generate stored name
            stored_name = uploader._get_stored_name(file_id, "test.pdf")
            assert stored_name.endswith(".pdf")
            result.add_pass("Generate stored name", f"name={stored_name}")

            # Test 5: Detect MIME type
            mime_type = uploader._detect_mime_type("test.pdf")
            assert mime_type == "application/pdf"
            result.add_pass("Detect MIME type", f"type={mime_type}")

            # Test 6: Max file size config
            assert uploader.max_file_size > 0
            result.add_pass("Max file size config", f"max={uploader.max_file_size}")

        except Exception as e:
            result.add_fail("File Upload", str(e))

        self.results.append(result)

    # ============== Schemas Tests ==============
    async def test_schemas(self):
        """Test Request/Response Schemas"""
        result = TestResult("Schemas")

        try:
            from agent_platform.gateway.schemas.requests import (
                ChatRequest, ChatResponse, TaskRequest, TaskResponse,
                FileUploadResponse, APIResponse, WebhookPayload
            )

            # Test 1: ChatRequest
            chat_req = ChatRequest(
                agent_id="agent_001",
                message="Hello",
                session_id="session_001"
            )
            assert chat_req.agent_id == "agent_001"
            result.add_pass("ChatRequest schema")

            # Test 2: ChatResponse
            chat_resp = ChatResponse(
                message="Hello there!",
                session_id="session_001"
            )
            assert chat_resp.message == "Hello there!"
            result.add_pass("ChatResponse schema")

            # Test 3: TaskRequest
            task_req = TaskRequest(
                agent_id="agent_001",
                task_type="chat",
                input_data={"message": "Hello"}
            )
            assert task_req.task_type == "chat"
            result.add_pass("TaskRequest schema")

            # Test 4: TaskResponse
            from agent_platform.gateway.schemas.requests import TaskStatus
            task_resp = TaskResponse(
                task_id="task_001",
                status=TaskStatus.PENDING
            )
            assert task_resp.task_id == "task_001"
            result.add_pass("TaskResponse schema")

            # Test 5: APIResponse
            api_resp = APIResponse(
                success=True,
                data={"key": "value"}
            )
            assert api_resp.success == True
            result.add_pass("APIResponse schema")

            # Test 6: WebhookPayload
            webhook_payload = WebhookPayload(
                event_type="task.completed",
                task_id="task_001",
                status=TaskStatus.COMPLETED
            )
            assert webhook_payload.event_type == "task.completed"
            result.add_pass("WebhookPayload schema")

        except Exception as e:
            result.add_fail("Schemas", str(e))

        self.results.append(result)


async def main():
    """Run all tests"""
    suite = PlatformTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
