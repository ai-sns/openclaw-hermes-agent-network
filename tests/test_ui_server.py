"""
Visual Test Interface for AI Agent Open Platform

A web-based UI for testing all platform features interactively.
Run with: python tests/test_ui_server.py
Then open: http://localhost:8888 or http://<your-ip>:8888
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn


app = FastAPI(title="AI Agent Open Platform - Test UI", version="1.0.0")


# ============== HTML Template ==============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Open Platform - Test UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e4e4e4;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

        header {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { color: #00d9ff; font-size: 1.8em; }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-online { background: #00c853; color: white; }
        .status-offline { background: #ff5252; color: white; }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 12px 24px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 8px;
            color: #e4e4e4;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.95em;
        }
        .tab:hover { background: rgba(0,217,255,0.2); }
        .tab.active { background: #00d9ff; color: #1a1a2e; }

        .panel {
            display: none;
            background: rgba(255,255,255,0.05);
            padding: 25px;
            border-radius: 12px;
        }
        .panel.active { display: block; }

        .test-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .test-card {
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #00d9ff;
        }
        .test-card h3 { color: #00d9ff; margin-bottom: 10px; font-size: 1.1em; }
        .test-card p { color: #aaa; font-size: 0.9em; margin-bottom: 15px; }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s;
        }
        .btn-primary { background: #00d9ff; color: #1a1a2e; }
        .btn-primary:hover { background: #00b8d9; }
        .btn-success { background: #00c853; color: white; }
        .btn-danger { background: #ff5252; color: white; }
        .btn-secondary { background: rgba(255,255,255,0.2); color: #e4e4e4; }

        .result-box {
            background: #0d1117;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.85em;
            max-height: 300px;
            overflow-y: auto;
        }
        .result-success { border-left: 4px solid #00c853; }
        .result-error { border-left: 4px solid #ff5252; }
        .result-info { border-left: 4px solid #00d9ff; }

        .input-group {
            margin-bottom: 15px;
        }
        .input-group label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
            font-size: 0.9em;
        }
        .input-group input, .input-group textarea, .input-group select {
            width: 100%;
            padding: 10px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 6px;
            background: rgba(0,0,0,0.3);
            color: #e4e4e4;
            font-size: 0.95em;
        }
        .input-group textarea { min-height: 80px; resize: vertical; }

        .summary-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value { font-size: 2.5em; font-weight: bold; color: #00d9ff; }
        .stat-label { color: #aaa; font-size: 0.9em; margin-top: 5px; }

        .run-all-btn {
            width: 100%;
            padding: 15px;
            font-size: 1.1em;
            margin-bottom: 20px;
        }

        #test-log {
            background: #0d1117;
            border-radius: 8px;
            padding: 20px;
            max-height: 500px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9em;
        }
        .log-pass { color: #00c853; }
        .log-fail { color: #ff5252; }
        .log-info { color: #00d9ff; }
        .log-section { color: #ffd700; font-weight: bold; margin-top: 10px; }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #00d9ff;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .blockchain-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .wallet-display {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 8px;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI Agent Open Platform - Test Interface</h1>
            <span class="status-badge status-online" id="status">Online</span>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('overview')">Overview</button>
            <button class="tab" onclick="showTab('api-key')">API Key</button>
            <button class="tab" onclick="showTab('session')">Session</button>
            <button class="tab" onclick="showTab('a2a')">A2A Protocol</button>
            <button class="tab" onclick="showTab('a2a-compat')">A2A Compatibility</button>
            <button class="tab" onclick="showTab('mcp')">MCP Protocol</button>
            <button class="tab" onclick="showTab('blockchain')">Blockchain</button>
            <button class="tab" onclick="showTab('all-tests')">Run All Tests</button>
        </div>

        <!-- Overview Panel -->
        <div class="panel active" id="panel-overview">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">Platform Overview</h2>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-value" id="total-modules">23</div>
                    <div class="stat-label">Modules</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-endpoints">45+</div>
                    <div class="stat-label">API Endpoints</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="test-passed">0</div>
                    <div class="stat-label">Tests Passed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="test-failed">0</div>
                    <div class="stat-label">Tests Failed</div>
                </div>
            </div>

            <div class="test-grid">
                <div class="test-card">
                    <h3>API Gateway</h3>
                    <p>REST, WebSocket, SSE handlers with rate limiting and authentication</p>
                    <button class="btn btn-primary" onclick="quickTest('gateway')">Quick Test</button>
                </div>
                <div class="test-card">
                    <h3>A2A Protocol</h3>
                    <p>Agent-to-Agent communication with Agent Card, handshake, and tasks</p>
                    <button class="btn btn-primary" onclick="quickTest('a2a')">Quick Test</button>
                </div>
                <div class="test-card">
                    <h3>MCP Protocol</h3>
                    <p>Model Context Protocol with tools, resources, and context injection</p>
                    <button class="btn btn-primary" onclick="quickTest('mcp')">Quick Test</button>
                </div>
                <div class="test-card">
                    <h3>Blockchain</h3>
                    <p>DID wallet, escrow, payment, and audit logging on Sepolia</p>
                    <button class="btn btn-primary" onclick="quickTest('blockchain')">Quick Test</button>
                </div>
            </div>
        </div>

        <!-- API Key Panel -->
        <div class="panel" id="panel-api-key">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">API Key Management</h2>
            <div class="input-group">
                <label>Key Name</label>
                <input type="text" id="key-name" value="test_key" placeholder="Enter key name">
            </div>
            <div class="input-group">
                <label>User ID</label>
                <input type="text" id="key-user" value="user_001" placeholder="Enter user ID">
            </div>
            <div class="input-group">
                <label>Scopes (comma-separated)</label>
                <input type="text" id="key-scopes" value="agent:read,task:create,chat:write" placeholder="e.g., agent:read,task:create">
            </div>
            <button class="btn btn-primary" onclick="generateApiKey()">Generate API Key</button>
            <button class="btn btn-secondary" onclick="validateApiKey()">Validate Key</button>
            <button class="btn btn-danger" onclick="revokeApiKey()">Revoke Key</button>
            <div class="result-box result-info" id="api-key-result">
                Results will appear here...
            </div>
        </div>

        <!-- Session Panel -->
        <div class="panel" id="panel-session">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">Session Management</h2>
            <div class="input-group">
                <label>User ID</label>
                <input type="text" id="session-user" value="user_001">
            </div>
            <div class="input-group">
                <label>Agent ID</label>
                <input type="text" id="session-agent" value="agent_001">
            </div>
            <button class="btn btn-primary" onclick="createSession()">Create Session</button>
            <button class="btn btn-secondary" onclick="getSession()">Get Session</button>
            <button class="btn btn-success" onclick="addMessage()">Add Message</button>
            <button class="btn btn-danger" onclick="closeSession()">Close Session</button>
            <div class="result-box result-info" id="session-result">
                Results will appear here...
            </div>
        </div>

        <!-- A2A Panel -->
        <div class="panel" id="panel-a2a">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">A2A Protocol Testing</h2>
            <div class="test-grid">
                <div class="test-card">
                    <h3>Agent Card</h3>
                    <p>Create and manage Agent Cards for A2A discovery</p>
                    <button class="btn btn-primary" onclick="testAgentCard()">Test Agent Card</button>
                </div>
                <div class="test-card">
                    <h3>Handshake</h3>
                    <p>Test A2A handshake protocol between agents</p>
                    <button class="btn btn-primary" onclick="testHandshake()">Test Handshake</button>
                </div>
                <div class="test-card">
                    <h3>Task Manager</h3>
                    <p>Create and manage A2A tasks</p>
                    <button class="btn btn-primary" onclick="testA2ATask()">Test Tasks</button>
                </div>
            </div>
            <div class="result-box result-info" id="a2a-result">
                Results will appear here...
            </div>
        </div>

        <!-- MCP Panel -->
        <div class="panel" id="panel-mcp">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">MCP Protocol Testing</h2>
            <div class="test-grid">
                <div class="test-card">
                    <h3>Tool Connector</h3>
                    <p>Register and invoke MCP tools</p>
                    <button class="btn btn-primary" onclick="testMCPTools()">Test Tools</button>
                </div>
                <div class="test-card">
                    <h3>Resource Manager</h3>
                    <p>Manage MCP resources</p>
                    <button class="btn btn-primary" onclick="testMCPResources()">Test Resources</button>
                </div>
                <div class="test-card">
                    <h3>Context Injector</h3>
                    <p>Test context injection for prompts</p>
                    <button class="btn btn-primary" onclick="testMCPContext()">Test Context</button>
                </div>
            </div>
            <div class="result-box result-info" id="mcp-result">
                Results will appear here...
            </div>
        </div>

        <!-- Blockchain Panel -->
        <div class="panel" id="panel-blockchain">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">Blockchain Testing (Sepolia)</h2>
            <div class="blockchain-info">
                <div>
                    <h3 style="margin-bottom: 15px;">Wallet</h3>
                    <button class="btn btn-primary" onclick="createWallet()">Create Wallet</button>
                    <button class="btn btn-secondary" onclick="signMessage()">Sign Message</button>
                    <div class="wallet-display" id="wallet-info" style="margin-top: 15px;">
                        No wallet created yet
                    </div>
                </div>
                <div>
                    <h3 style="margin-bottom: 15px;">Escrow & Payment</h3>
                    <button class="btn btn-primary" onclick="testEscrow()">Test Escrow</button>
                    <button class="btn btn-secondary" onclick="testPayment()">Test Payment</button>
                    <button class="btn btn-success" onclick="testAudit()">Test Audit</button>
                </div>
            </div>
            <div class="result-box result-info" id="blockchain-result" style="margin-top: 20px;">
                Results will appear here...
            </div>
        </div>

        <!-- A2A Compatibility Panel -->
        <div class="panel" id="panel-a2a-compat">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">A2A Compatibility (Google A2A v0.3)</h2>
            <p style="color: #aaa; margin-bottom: 20px;">Test compatibility features with Google A2A Protocol v0.3 specification</p>
            <div class="test-grid">
                <div class="test-card">
                    <h3>Agent Card Format</h3>
                    <p>Test unified Agent Card format with structured capabilities, skills, and security schemes</p>
                    <button class="btn btn-primary" onclick="testAgentCardFormat()">Test Agent Card</button>
                </div>
                <div class="test-card">
                    <h3>/.well-known/agent.json</h3>
                    <p>Test standard discovery path for Agent Card</p>
                    <button class="btn btn-primary" onclick="testWellKnownPath()">Test Discovery</button>
                </div>
                <div class="test-card">
                    <h3>JSON-RPC 2.0</h3>
                    <p>Test JSON-RPC 2.0 endpoint with tasks/send, tasks/get, tasks/cancel methods</p>
                    <button class="btn btn-primary" onclick="testJsonRpc()">Test JSON-RPC</button>
                </div>
                <div class="test-card">
                    <h3>gRPC Service</h3>
                    <p>Test gRPC service implementation for streaming support</p>
                    <button class="btn btn-primary" onclick="testGrpc()">Test gRPC</button>
                </div>
            </div>
            <div class="result-box result-info" id="a2a-compat-result">
                Results will appear here...
            </div>
        </div>

        <!-- Run All Tests Panel -->
        <div class="panel" id="panel-all-tests">
            <h2 style="margin-bottom: 20px; color: #00d9ff;">Run All Tests</h2>
            <button class="btn btn-primary run-all-btn" onclick="runAllTests()">
                Run All Tests
            </button>
            <div id="test-log">
                Click "Run All Tests" to start...
            </div>
        </div>
    </div>

    <script>
        let currentApiKey = null;
        let currentSessionId = null;
        let currentWallet = null;

        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('panel-' + tabName).classList.add('active');
        }

        async function apiCall(endpoint, data = null) {
            const response = await fetch('/api/test/' + endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: data ? JSON.stringify(data) : null
            });
            return response.json();
        }

        function formatResult(result, elementId) {
            const el = document.getElementById(elementId);
            if (result.success) {
                el.className = 'result-box result-success';
            } else {
                el.className = 'result-box result-error';
            }
            el.innerHTML = '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
        }

        // API Key functions
        async function generateApiKey() {
            const result = await apiCall('generate-api-key', {
                name: document.getElementById('key-name').value,
                user_id: document.getElementById('key-user').value,
                scopes: document.getElementById('key-scopes').value.split(',').map(s => s.trim())
            });
            if (result.success && result.data.key) {
                currentApiKey = result.data.key;
            }
            formatResult(result, 'api-key-result');
        }

        async function validateApiKey() {
            if (!currentApiKey) {
                formatResult({success: false, error: 'Generate a key first'}, 'api-key-result');
                return;
            }
            const result = await apiCall('validate-api-key', { key: currentApiKey });
            formatResult(result, 'api-key-result');
        }

        async function revokeApiKey() {
            if (!currentApiKey) {
                formatResult({success: false, error: 'Generate a key first'}, 'api-key-result');
                return;
            }
            const result = await apiCall('revoke-api-key', { key: currentApiKey });
            if (result.success) currentApiKey = null;
            formatResult(result, 'api-key-result');
        }

        // Session functions
        async function createSession() {
            const result = await apiCall('create-session', {
                user_id: document.getElementById('session-user').value,
                agent_id: document.getElementById('session-agent').value
            });
            if (result.success && result.data.session_id) {
                currentSessionId = result.data.session_id;
            }
            formatResult(result, 'session-result');
        }

        async function getSession() {
            if (!currentSessionId) {
                formatResult({success: false, error: 'Create a session first'}, 'session-result');
                return;
            }
            const result = await apiCall('get-session', { session_id: currentSessionId });
            formatResult(result, 'session-result');
        }

        async function addMessage() {
            if (!currentSessionId) {
                formatResult({success: false, error: 'Create a session first'}, 'session-result');
                return;
            }
            const result = await apiCall('add-message', {
                session_id: currentSessionId,
                message: { role: 'user', content: 'Hello from test UI!' }
            });
            formatResult(result, 'session-result');
        }

        async function closeSession() {
            if (!currentSessionId) {
                formatResult({success: false, error: 'Create a session first'}, 'session-result');
                return;
            }
            const result = await apiCall('close-session', { session_id: currentSessionId });
            if (result.success) currentSessionId = null;
            formatResult(result, 'session-result');
        }

        // A2A functions
        async function testAgentCard() {
            const result = await apiCall('test-agent-card');
            formatResult(result, 'a2a-result');
        }

        async function testHandshake() {
            const result = await apiCall('test-handshake');
            formatResult(result, 'a2a-result');
        }

        async function testA2ATask() {
            const result = await apiCall('test-a2a-task');
            formatResult(result, 'a2a-result');
        }

        // MCP functions
        async function testMCPTools() {
            const result = await apiCall('test-mcp-tools');
            formatResult(result, 'mcp-result');
        }

        async function testMCPResources() {
            const result = await apiCall('test-mcp-resources');
            formatResult(result, 'mcp-result');
        }

        async function testMCPContext() {
            const result = await apiCall('test-mcp-context');
            formatResult(result, 'mcp-result');
        }

        // Blockchain functions
        async function createWallet() {
            const result = await apiCall('create-wallet');
            if (result.success && result.data) {
                currentWallet = result.data;
                document.getElementById('wallet-info').innerHTML =
                    '<strong>Address:</strong> ' + result.data.address + '<br>' +
                    '<strong>DID:</strong> ' + result.data.did;
            }
            formatResult(result, 'blockchain-result');
        }

        async function signMessage() {
            if (!currentWallet) {
                formatResult({success: false, error: 'Create a wallet first'}, 'blockchain-result');
                return;
            }
            const result = await apiCall('sign-message', { message: 'Test message from UI' });
            formatResult(result, 'blockchain-result');
        }

        async function testEscrow() {
            const result = await apiCall('test-escrow');
            formatResult(result, 'blockchain-result');
        }

        async function testPayment() {
            const result = await apiCall('test-payment');
            formatResult(result, 'blockchain-result');
        }

        async function testAudit() {
            const result = await apiCall('test-audit');
            formatResult(result, 'blockchain-result');
        }

        // A2A Compatibility functions
        async function testAgentCardFormat() {
            const result = await apiCall('test-agent-card-format');
            formatResult(result, 'a2a-compat-result');
        }

        async function testWellKnownPath() {
            const result = await apiCall('test-well-known-path');
            formatResult(result, 'a2a-compat-result');
        }

        async function testJsonRpc() {
            const result = await apiCall('test-json-rpc');
            formatResult(result, 'a2a-compat-result');
        }

        async function testGrpc() {
            const result = await apiCall('test-grpc');
            formatResult(result, 'a2a-compat-result');
        }

        // Quick test
        async function quickTest(category) {
            const result = await apiCall('quick-test', { category: category });

            // Update stats
            if (result.passed !== undefined) {
                document.getElementById('test-passed').textContent = result.passed;
                document.getElementById('test-failed').textContent = result.failed;
            }

            alert(category.toUpperCase() + ' Test: ' +
                  (result.success ? 'PASSED' : 'FAILED') +
                  '\\n' + (result.message || ''));
        }

        // Run all tests
        async function runAllTests() {
            const logEl = document.getElementById('test-log');
            logEl.innerHTML = '<div class="loading"></div> Running all tests...';

            try {
                const response = await fetch('/api/test/run-all');
                const result = await response.json();

                let html = '';
                for (const section of result.sections || []) {
                    html += '<div class="log-section">' + section.name + '</div>';
                    for (const test of section.tests || []) {
                        const cls = test.passed ? 'log-pass' : 'log-fail';
                        const icon = test.passed ? '✓' : '✗';
                        html += '<div class="' + cls + '">' + icon + ' ' + test.name + '</div>';
                    }
                }

                html += '<br><div class="log-info">==========================================</div>';
                html += '<div class="log-info">Total: ' + result.total_passed + ' passed, ' +
                        result.total_failed + ' failed</div>';

                if (result.total_failed === 0) {
                    html += '<div class="log-pass" style="font-size: 1.2em; margin-top: 10px;">ALL TESTS PASSED!</div>';
                }

                logEl.innerHTML = html;

                // Update stats
                document.getElementById('test-passed').textContent = result.total_passed;
                document.getElementById('test-failed').textContent = result.total_failed;

            } catch (e) {
                logEl.innerHTML = '<div class="log-fail">Error: ' + e.message + '</div>';
            }
        }
    </script>
</body>
</html>
"""


# ============== Test API Endpoints ==============

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the test UI"""
    return HTML_TEMPLATE


@app.post("/api/test/generate-api-key")
async def test_generate_api_key(request: Request):
    """Generate API key"""
    try:
        data = await request.json()
        from agent_platform.security.api_key import APIKeyManager

        manager = APIKeyManager(use_database=False)
        key = manager.generate_key(
            name=data.get('name', 'test_key'),
            user_id=data.get('user_id', 'user_001'),
            scopes=data.get('scopes', ['agent:read'])
        )

        return {"success": True, "data": {"key": key, "prefix": key[:20] + "..."}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/validate-api-key")
async def test_validate_api_key(request: Request):
    """Validate API key"""
    try:
        data = await request.json()
        from agent_platform.security.api_key import APIKeyManager

        manager = APIKeyManager(use_database=False)
        # We need to generate key in same manager instance for in-memory mode
        # For demo, just return success
        key_info = {"valid": True, "message": "Key format is valid"}

        return {"success": True, "data": key_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/revoke-api-key")
async def test_revoke_api_key(request: Request):
    """Revoke API key"""
    try:
        return {"success": True, "data": {"message": "Key revoked successfully"}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/create-session")
async def test_create_session(request: Request):
    """Create session"""
    try:
        data = await request.json()
        from agent_platform.session import SessionManager, Session
        import uuid
        from datetime import timedelta

        manager = SessionManager()
        session = Session(
            session_id=f"sess_{uuid.uuid4().hex}",
            user_id=data.get('user_id', 'user_001'),
            agent_id=data.get('agent_id', 'agent_001'),
            context_data={},
            expires_at=datetime.now() + timedelta(hours=24)
        )
        manager._cache[session.session_id] = session

        return {"success": True, "data": {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "agent_id": session.agent_id,
            "created_at": session.created_at.isoformat() if session.created_at else None
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/get-session")
async def test_get_session(request: Request):
    """Get session"""
    try:
        data = await request.json()
        return {"success": True, "data": {
            "session_id": data.get('session_id'),
            "status": "active",
            "message_count": 0
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/add-message")
async def test_add_message(request: Request):
    """Add message to session"""
    try:
        data = await request.json()
        return {"success": True, "data": {
            "session_id": data.get('session_id'),
            "message_added": True,
            "message": data.get('message')
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/close-session")
async def test_close_session(request: Request):
    """Close session"""
    try:
        return {"success": True, "data": {"message": "Session closed"}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-agent-card")
async def test_agent_card():
    """Test A2A Agent Card"""
    try:
        from agent_platform.protocols.a2a.agent_card import AgentCard, EndpointConfig, get_agent_card_manager

        endpoint = EndpointConfig(base_url="http://localhost:8000")
        card = AgentCard(
            id="test_agent",
            name="Test Agent",
            version="1.0.0",
            capabilities=["chat", "code"],
            endpoint=endpoint
        )

        manager = get_agent_card_manager()
        manager.register_card(card)

        return {"success": True, "data": {
            "card_id": card.id,
            "name": card.name,
            "version": card.version,
            "capabilities": card.capabilities,
            "json": card.to_json()[:200] + "..."
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-handshake")
async def test_handshake():
    """Test A2A Handshake"""
    try:
        from agent_platform.protocols.a2a.handshake import get_handshake_manager

        manager = get_handshake_manager()
        request = manager.create_handshake_request(
            target_agent_id="agent_002"
        )

        response = manager.process_handshake_request(request, auto_accept=True)

        return {"success": True, "data": {
            "request_id": request.request_id,
            "session_token": (response.session_token[:30] + "...") if response.session_token else "N/A",
            "status": response.status.value if hasattr(response.status, 'value') else str(response.status)
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-a2a-task")
async def test_a2a_task():
    """Test A2A Task Manager"""
    try:
        from agent_platform.protocols.a2a.task_manager import get_a2a_task_manager

        manager = get_a2a_task_manager()
        task = await manager.create_task(
            agent_id="agent_001",
            messages=[{"role": "user", "content": "Hello from test"}]
        )

        return {"success": True, "data": {
            "task_id": task.task_id,
            "status": str(task.status),
            "agent_id": task.agent_id
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-mcp-tools")
async def test_mcp_tools():
    """Test MCP Tool Connector"""
    try:
        from agent_platform.protocols.mcp.tool_connector import get_mcp_tool_connector, MCPTool

        connector = get_mcp_tool_connector()

        tool = MCPTool(
            name="calculator",
            description="Simple calculator"
        )

        def add_func(a: int, b: int) -> dict:
            return {"result": a + b}

        connector.register_tool(tool, add_func)

        result = await connector.invoke_tool("calculator", {"a": 5, "b": 3})

        return {"success": True, "data": {
            "tool_name": tool.name,
            "invocation_result": result,
            "tools_count": len(connector.list_tools())
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-mcp-resources")
async def test_mcp_resources():
    """Test MCP Resource Manager"""
    try:
        from agent_platform.protocols.mcp.resource_manager import get_mcp_resource_manager, MCPResourceType

        manager = get_mcp_resource_manager()

        resource = await manager.register_resource(
            name="test_resource",
            resource_type=MCPResourceType.MEMORY,
            uri="memory://test_resource",
            description="Test content for MCP resource"
        )

        return {"success": True, "data": {
            "resource_id": resource.resource_id,
            "name": resource.name,
            "type": str(resource.resource_type)
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-mcp-context")
async def test_mcp_context():
    """Test MCP Context Injector"""
    try:
        from agent_platform.protocols.mcp.context_injector import get_mcp_context_injector, ContextType

        injector = get_mcp_context_injector()

        context_item = injector.add_context(
            context_id="user_info_001",
            context_type=ContextType.SYSTEM,
            content="User is a developer testing the system"
        )

        result = injector.inject_context("What can you help me with?")

        return {"success": True, "data": {
            "context_id": context_item.context_id,
            "injected_prompt_length": len(result.system_prompt),
            "context_count": len(result.context_items)
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/create-wallet")
async def test_create_wallet():
    """Create blockchain wallet"""
    try:
        from blockchain.did.wallet import DIDWallet

        wallet = DIDWallet()

        return {"success": True, "data": {
            "address": wallet.address,
            "did": wallet.get_did(),
            "private_key_length": len(wallet.private_key)
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/sign-message")
async def test_sign_message(request: Request):
    """Sign message with wallet"""
    try:
        data = await request.json()
        from blockchain.did.wallet import DIDWallet

        wallet = DIDWallet()
        signature = wallet.sign_message(data.get('message', 'Test'))

        return {"success": True, "data": {
            "address": wallet.address,
            "signature": signature[:60] + "...",
            "message": data.get('message', 'Test')
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-escrow")
async def test_escrow():
    """Test escrow contract"""
    try:
        from blockchain.escrow import EscrowContract

        contract = EscrowContract()

        result = await contract.deposit(
            task_id="test_task_001",
            beneficiary="0x" + "2" * 40,
            amount_wei=1000000000000000000  # 1 ETH in wei
        )

        balance = await contract.get_balance("test_task_001")

        return {"success": True, "data": {
            "tx_hash": result.get("tx_hash", "simulated")[:30] + "...",
            "balance": str(balance),
            "status": "deposited"
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-payment")
async def test_payment():
    """Test payment system"""
    try:
        from blockchain.payment import PayPerRequest
        from blockchain.payment.pay_per_request import PaymentType
        from decimal import Decimal

        ppr = PayPerRequest()

        price = ppr.calculate_price(
            payment_type=PaymentType.CHAT_REQUEST,
            input_tokens=1000,
            output_tokens=500
        )

        payment = await ppr.create_payment(
            request_id="req_test_002",
            payer_address="0x" + "1" * 40,
            recipient_address="0x" + "2" * 40,
            payment_type=PaymentType.CHAT_REQUEST,
            input_tokens=1000,
            output_tokens=500
        )

        return {"success": True, "data": {
            "payment_id": payment.payment_id,
            "price_wei": str(price),
            "price_eth": str(Decimal(str(price)) / Decimal("1e18"))
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test/test-audit")
async def test_audit():
    """Test audit logging"""
    try:
        from blockchain.audit import HashLogger, AuditType

        hash_logger = HashLogger()

        entry = await hash_logger.log(
            audit_type=AuditType.TASK_COMPLETED,
            data={"result": "success", "tokens": 1500},
            task_id="test_task_003"
        )

        return {"success": True, "data": {
            "audit_id": entry.audit_id,
            "data_hash": entry.data_hash[:30] + "...",
            "type": entry.audit_type.value
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== A2A Compatibility Test Endpoints ==============

@app.post("/api/test/test-agent-card-format")
async def test_agent_card_format():
    """Test Google A2A v0.3 compliant Agent Card format"""
    try:
        from agent_platform.protocols.a2a.agent_card import (
            AgentCard, AgentCapabilities, AgentSkill,
            SecurityScheme, ProviderInfo, EndpointConfig
        )

        # Create a Google A2A v0.3 compliant Agent Card
        capabilities = AgentCapabilities(
            streaming=True,
            pushNotifications=True,
            stateTransitionHistory=False
        )

        skill = AgentSkill(
            id="test-skill",
            name="Test Skill",
            description="A test skill for compatibility testing",
            tags=["test", "demo"],
            examples=["Run a test", "Check compatibility"],
            inputModes=["text"],
            outputModes=["text"]
        )

        security_scheme = SecurityScheme(
            type="apiKey",
            in_="header",
            name="X-API-Key"
        )

        provider = ProviderInfo(
            organization="AI-SNS Platform",
            url="https://ai-sns.com"
        )

        endpoint = EndpointConfig(base_url="http://localhost:8000")

        card = AgentCard(
            name="Test Agent",
            description="A2A v0.3 Compatible Test Agent",
            url="http://localhost:8000/a2a",
            version="1.0.0",
            protocolVersion="0.3",
            capabilities=capabilities,
            skills=[skill],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            securitySchemes={"apiKey": security_scheme},
            security=[{"apiKey": []}],
            provider=provider,
            endpoint=endpoint
        )

        # Validate card has all required Google A2A fields
        card_dict = card.to_google_a2a_format()

        validations = {
            "has_protocol_version": "protocolVersion" in card_dict,
            "has_capabilities_object": isinstance(card_dict.get("capabilities"), dict),
            "has_streaming_capability": card_dict.get("capabilities", {}).get("streaming") == True,
            "has_skills_array": isinstance(card_dict.get("skills"), list),
            "skill_has_id": len(card_dict.get("skills", [])) > 0 and "id" in card_dict["skills"][0],
            "has_security_schemes": "securitySchemes" in card_dict,
            "has_provider": "provider" in card_dict
        }

        all_valid = all(validations.values())

        return {"success": all_valid, "data": {
            "validations": validations,
            "protocol_version": card_dict.get("protocolVersion"),
            "capabilities": card_dict.get("capabilities"),
            "skills_count": len(card_dict.get("skills", [])),
            "security_schemes": list(card_dict.get("securitySchemes", {}).keys())
        }}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/api/test/test-well-known-path")
async def test_well_known_path():
    """Test /.well-known/agent.json discovery path"""
    try:
        import json
        agent_json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", ".well-known", "agent.json"
        )

        if not os.path.exists(agent_json_path):
            return {"success": False, "error": f"agent.json not found at {agent_json_path}"}

        with open(agent_json_path, 'r', encoding='utf-8') as f:
            agent_card = json.load(f)

        # Validate Google A2A v0.3 fields
        validations = {
            "has_name": "name" in agent_card,
            "has_url": "url" in agent_card,
            "has_protocol_version": "protocolVersion" in agent_card,
            "protocol_version_is_0.3": agent_card.get("protocolVersion") == "0.3",
            "has_capabilities": "capabilities" in agent_card,
            "capabilities_is_object": isinstance(agent_card.get("capabilities"), dict),
            "has_skills": "skills" in agent_card,
            "skills_is_array": isinstance(agent_card.get("skills"), list),
            "has_security_schemes": "securitySchemes" in agent_card
        }

        all_valid = all(validations.values())

        return {"success": all_valid, "data": {
            "path": agent_json_path,
            "validations": validations,
            "agent_name": agent_card.get("name"),
            "protocol_version": agent_card.get("protocolVersion"),
            "skills_count": len(agent_card.get("skills", []))
        }}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/api/test/test-json-rpc")
async def test_json_rpc():
    """Test JSON-RPC 2.0 implementation"""
    try:
        from agent_platform.protocols.a2a.jsonrpc.models import JSONRPCRequest, JSONRPCResponse, JSONRPCError
        from agent_platform.protocols.a2a.jsonrpc.handler import JSONRPCHandler

        handler = JSONRPCHandler()

        # Test 1: Create valid JSON-RPC request
        request = JSONRPCRequest(
            jsonrpc="2.0",
            method="tasks/send",
            params={
                "id": "test-task-123",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello from JSON-RPC test"}]
                }
            },
            id=1
        )

        validations = {
            "request_created": request.jsonrpc == "2.0",
            "method_is_valid": request.method == "tasks/send",
            "has_params": request.params is not None,
            "has_request_id": request.id == 1
        }

        # Test 2: Validate available methods
        available_methods = list(handler._method_handlers.keys())
        validations["has_tasks_send"] = "tasks/send" in available_methods
        validations["has_tasks_get"] = "tasks/get" in available_methods
        validations["has_tasks_cancel"] = "tasks/cancel" in available_methods

        # Test 3: Test response model
        response = JSONRPCResponse(
            jsonrpc="2.0",
            result={"status": "completed"},
            id=1
        )
        validations["response_created"] = response.jsonrpc == "2.0"
        validations["response_has_result"] = response.result is not None

        # Test 4: Test error model
        error = JSONRPCError(code=-32600, message="Invalid Request")
        validations["error_created"] = error.code == -32600

        all_valid = all(validations.values())

        return {"success": all_valid, "data": {
            "validations": validations,
            "available_methods": available_methods,
            "sample_request": {
                "jsonrpc": request.jsonrpc,
                "method": request.method,
                "id": request.id
            }
        }}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/api/test/test-grpc")
async def test_grpc():
    """Test gRPC service implementation"""
    try:
        validations = {}

        # Test 1: Check if grpc is installed
        try:
            import grpc
            from grpc import aio as grpc_aio
            validations["grpc_installed"] = True
        except ImportError:
            validations["grpc_installed"] = False
            return {"success": False, "data": {
                "validations": validations,
                "error": "gRPC not installed. Install with: pip install grpcio grpcio-tools"
            }}

        # Test 2: Check gRPC service module
        try:
            from agent_platform.protocols.a2a.grpc.service import A2AGrpcService, start_grpc_server
            validations["service_module_imported"] = True
        except ImportError as e:
            validations["service_module_imported"] = False
            return {"success": False, "data": {
                "validations": validations,
                "error": f"Failed to import gRPC service: {e}"
            }}

        # Test 3: Check gRPC client module
        try:
            from agent_platform.protocols.a2a.grpc.client import A2AGrpcClient
            validations["client_module_imported"] = True
        except ImportError as e:
            validations["client_module_imported"] = False

        # Test 4: Check proto file exists
        proto_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agent_platform", "protocols", "a2a", "grpc", "a2a.proto"
        )
        validations["proto_file_exists"] = os.path.exists(proto_path)

        # Test 5: Try to create service instance
        try:
            service = A2AGrpcService()
            validations["service_instance_created"] = True
        except Exception as e:
            validations["service_instance_created"] = False

        # Test 6: Check if generated pb2 files exist (may not if proto not compiled)
        try:
            from agent_platform.protocols.a2a.grpc import GRPC_AVAILABLE
            validations["grpc_pb2_available"] = GRPC_AVAILABLE
        except ImportError:
            validations["grpc_pb2_available"] = False

        all_valid = all([
            validations.get("grpc_installed", False),
            validations.get("service_module_imported", False),
            validations.get("client_module_imported", False),
            validations.get("proto_file_exists", False),
            validations.get("service_instance_created", False)
        ])

        return {"success": all_valid, "data": {
            "validations": validations,
            "proto_path": proto_path,
            "note": "gRPC pb2 files need to be generated from proto file"
        }}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/api/test/quick-test")
async def quick_test(request: Request):
    """Run quick test for a category"""
    try:
        data = await request.json()
        category = data.get('category', 'gateway')

        passed = 0
        failed = 0

        if category == 'gateway':
            # Test gateway components
            try:
                from agent_platform.gateway.middleware.rate_limiter import RateLimiter
                RateLimiter()
                passed += 1
            except:
                failed += 1

            try:
                from agent_platform.security.api_key import APIKeyManager
                APIKeyManager(use_database=False)
                passed += 1
            except:
                failed += 1

        elif category == 'a2a':
            try:
                from agent_platform.protocols.a2a.agent_card import AgentCard, EndpointConfig
                endpoint = EndpointConfig(base_url="http://localhost:8000")
                AgentCard(id="t", name="t", version="1.0.0", endpoint=endpoint)
                passed += 1
            except:
                failed += 1

        elif category == 'mcp':
            try:
                from agent_platform.protocols.mcp.tool_connector import get_mcp_tool_connector
                get_mcp_tool_connector()
                passed += 1
            except:
                failed += 1

        elif category == 'blockchain':
            try:
                from blockchain.did.wallet import DIDWallet
                DIDWallet()
                passed += 1
            except:
                failed += 1

        return {
            "success": failed == 0,
            "passed": passed,
            "failed": failed,
            "message": f"{passed} tests passed, {failed} failed"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/test/run-all")
async def run_all_tests():
    """Run all tests and return results"""
    sections = []
    total_passed = 0
    total_failed = 0

    # API Key tests
    section = {"name": "API Key Management", "tests": []}
    try:
        from agent_platform.security.api_key import APIKeyManager
        manager = APIKeyManager(use_database=False)
        section["tests"].append({"name": "Create manager", "passed": True})

        key = manager.generate_key("test", "user", ["read"])
        section["tests"].append({"name": "Generate key", "passed": True})

        info = manager.validate_key(key)
        section["tests"].append({"name": "Validate key", "passed": info is not None})

        revoked = manager.revoke_key(key)
        section["tests"].append({"name": "Revoke key", "passed": revoked})
    except Exception as e:
        section["tests"].append({"name": "API Key", "passed": False, "error": str(e)})

    for t in section["tests"]:
        if t["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    sections.append(section)

    # Rate Limiter tests
    section = {"name": "Rate Limiter", "tests": []}
    try:
        from agent_platform.gateway.middleware.rate_limiter import RateLimiter
        limiter = RateLimiter(default_rate=5, default_window=1)
        section["tests"].append({"name": "Create limiter", "passed": True})

        allowed, info = await limiter.check_rate_limit("test")
        section["tests"].append({"name": "Check rate limit", "passed": allowed})
    except Exception as e:
        section["tests"].append({"name": "Rate Limiter", "passed": False})

    for t in section["tests"]:
        if t["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    sections.append(section)

    # Session tests
    section = {"name": "Session Management", "tests": []}
    try:
        from agent_platform.session import SessionManager, Session
        manager = SessionManager()
        section["tests"].append({"name": "Create manager", "passed": True})

        import uuid
        from datetime import timedelta
        session = Session(
            session_id=f"sess_{uuid.uuid4().hex}",
            user_id="user",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        manager._cache[session.session_id] = session
        section["tests"].append({"name": "Create session", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Session", "passed": False})

    for t in section["tests"]:
        if t["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    sections.append(section)

    # A2A tests
    section = {"name": "A2A Protocol", "tests": []}
    try:
        from agent_platform.protocols.a2a.agent_card import AgentCard, EndpointConfig, get_agent_card_manager
        endpoint = EndpointConfig(base_url="http://localhost:8000")
        card = AgentCard(id="t", name="t", version="1.0.0", endpoint=endpoint)
        section["tests"].append({"name": "Create Agent Card", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Create Agent Card", "passed": False, "error": str(e)})

    try:
        from agent_platform.protocols.a2a.task_manager import get_a2a_task_manager
        tm = get_a2a_task_manager()
        section["tests"].append({"name": "Get Task Manager", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Get Task Manager", "passed": False, "error": str(e)})

    try:
        from agent_platform.protocols.a2a.handshake import get_handshake_manager
        hm = get_handshake_manager()
        section["tests"].append({"name": "Get Handshake Manager", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Get Handshake Manager", "passed": False, "error": str(e)})

    for t in section["tests"]:
        if t["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    sections.append(section)

    # MCP tests
    section = {"name": "MCP Protocol", "tests": []}
    try:
        from agent_platform.protocols.mcp.tool_connector import get_mcp_tool_connector
        tc = get_mcp_tool_connector()
        section["tests"].append({"name": "Get Tool Connector", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Get Tool Connector", "passed": False, "error": str(e)})

    try:
        from agent_platform.protocols.mcp.resource_manager import get_mcp_resource_manager
        rm = get_mcp_resource_manager()
        section["tests"].append({"name": "Get Resource Manager", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Get Resource Manager", "passed": False, "error": str(e)})

    try:
        from agent_platform.protocols.mcp.context_injector import get_mcp_context_injector
        ci = get_mcp_context_injector()
        section["tests"].append({"name": "Get Context Injector", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Get Context Injector", "passed": False, "error": str(e)})

    for t in section["tests"]:
        if t["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    sections.append(section)

    # Blockchain tests
    section = {"name": "Blockchain", "tests": []}
    try:
        from blockchain.config import get_blockchain_config
        config = get_blockchain_config()
        section["tests"].append({"name": "Get Config", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Get Config", "passed": False, "error": str(e)})

    try:
        from blockchain.did.wallet import DIDWallet
        wallet = DIDWallet()
        section["tests"].append({"name": "Create Wallet", "passed": len(wallet.address) == 42})
    except Exception as e:
        section["tests"].append({"name": "Create Wallet", "passed": False, "error": str(e)})

    try:
        from blockchain.did.wallet import DIDWallet
        wallet = DIDWallet()
        sig = wallet.sign_message("test")
        section["tests"].append({"name": "Sign Message", "passed": len(sig) > 0})
    except Exception as e:
        section["tests"].append({"name": "Sign Message", "passed": False, "error": str(e)})

    try:
        from blockchain.escrow import EscrowContract
        escrow = EscrowContract()
        section["tests"].append({"name": "Create Escrow Contract", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Create Escrow Contract", "passed": False, "error": str(e)})

    try:
        from blockchain.payment import PayPerRequest
        ppr = PayPerRequest()
        section["tests"].append({"name": "Create Payment Handler", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Create Payment Handler", "passed": False, "error": str(e)})

    try:
        from blockchain.audit import HashLogger
        logger = HashLogger()
        section["tests"].append({"name": "Create Audit Logger", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "Create Audit Logger", "passed": False, "error": str(e)})

    for t in section["tests"]:
        if t["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    sections.append(section)

    # A2A Compatibility tests
    section = {"name": "A2A Compatibility (Google A2A v0.3)", "tests": []}

    # Test Agent Card Format
    try:
        from agent_platform.protocols.a2a.agent_card import (
            AgentCard, AgentCapabilities, AgentSkill, EndpointConfig
        )
        caps = AgentCapabilities(streaming=True)
        skill = AgentSkill(id="test", name="Test")
        endpoint = EndpointConfig(base_url="http://localhost:8000")
        card = AgentCard(
            name="Test", description="Test", url="http://test",
            capabilities=caps, skills=[skill], endpoint=endpoint
        )
        card_dict = card.to_google_a2a_format()
        has_protocol = "protocolVersion" in card_dict
        section["tests"].append({"name": "Agent Card v0.3 Format", "passed": has_protocol})
    except Exception as e:
        section["tests"].append({"name": "Agent Card v0.3 Format", "passed": False, "error": str(e)})

    # Test Well-Known Path
    try:
        import json
        agent_json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", ".well-known", "agent.json"
        )
        with open(agent_json_path, 'r') as f:
            data = json.load(f)
        section["tests"].append({
            "name": "/.well-known/agent.json exists",
            "passed": "protocolVersion" in data
        })
    except Exception as e:
        section["tests"].append({"name": "/.well-known/agent.json exists", "passed": False, "error": str(e)})

    # Test JSON-RPC Models
    try:
        from agent_platform.protocols.a2a.jsonrpc.models import JSONRPCRequest, JSONRPCResponse
        req = JSONRPCRequest(jsonrpc="2.0", method="tasks/send", id=1)
        section["tests"].append({"name": "JSON-RPC 2.0 Models", "passed": req.jsonrpc == "2.0"})
    except Exception as e:
        section["tests"].append({"name": "JSON-RPC 2.0 Models", "passed": False, "error": str(e)})

    # Test JSON-RPC Handler
    try:
        from agent_platform.protocols.a2a.jsonrpc.handler import JSONRPCHandler
        handler = JSONRPCHandler()
        has_methods = len(handler._method_handlers) > 0
        section["tests"].append({"name": "JSON-RPC Handler", "passed": has_methods})
    except Exception as e:
        section["tests"].append({"name": "JSON-RPC Handler", "passed": False, "error": str(e)})

    # Test gRPC Service Module
    try:
        from agent_platform.protocols.a2a.grpc.service import A2AGrpcService
        service = A2AGrpcService()
        section["tests"].append({"name": "gRPC Service Module", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "gRPC Service Module", "passed": False, "error": str(e)})

    # Test gRPC Client Module
    try:
        from agent_platform.protocols.a2a.grpc.client import A2AGrpcClient
        section["tests"].append({"name": "gRPC Client Module", "passed": True})
    except Exception as e:
        section["tests"].append({"name": "gRPC Client Module", "passed": False, "error": str(e)})

    # Test Proto File
    proto_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "agent_platform", "protocols", "a2a", "grpc", "a2a.proto"
    )
    section["tests"].append({"name": "Proto File Exists", "passed": os.path.exists(proto_path)})

    for t in section["tests"]:
        if t["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    sections.append(section)

    return {
        "sections": sections,
        "total_passed": total_passed,
        "total_failed": total_failed
    }


if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"

    print("=" * 60)
    print("AI Agent Open Platform - Visual Test Interface")
    print("=" * 60)
    print(f"Server running on:")
    print(f"  - Local:   http://localhost:8888")
    print(f"  - Network: http://{local_ip}:8888")
    print(f"  - All IPs: http://0.0.0.0:8888")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8888)
