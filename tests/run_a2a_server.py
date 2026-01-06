#!/usr/bin/env python3
"""
A2A Protocol Server with Blockchain Integration

This is a standalone A2A server for testing with blockchain payment support.
It exposes the Agent Card, handles skill invocations, and manages escrow payments.

Usage:
    python tests/run_a2a_server.py [--port 8000]

Endpoints:
    GET  /.well-known/agent.json      - Agent Card (discovery)
    POST /a2a/rpc                     - JSON-RPC 2.0 endpoint
    POST /a2a/tasks                   - REST API for tasks
    GET  /a2a/tasks/{id}              - Get task status
    GET  /a2a_ui                      - Visual Interface
    POST /api/blockchain/wallet/create - Create wallet
    POST /api/blockchain/escrow/deposit - Deposit to escrow
    POST /api/blockchain/escrow/release - Release escrow
    POST /api/blockchain/escrow/refund  - Refund escrow
"""

import os
import sys
import json
import uuid
import asyncio
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import blockchain modules
try:
    from blockchain.did.wallet import DIDWallet, WalletManager
    from blockchain.escrow.contract import get_escrow_contract, EscrowStatus
    from blockchain.payment.pay_per_request import get_pay_per_request, PaymentType
    HAS_BLOCKCHAIN = True
except ImportError as e:
    print(f"Warning: Blockchain modules not available: {e}")
    HAS_BLOCKCHAIN = False

# Import Sepolia service for real blockchain interaction
try:
    from blockchain.sepolia_service import get_sepolia_service, SepoliaService
    sepolia_service = get_sepolia_service()
    HAS_SEPOLIA = sepolia_service.is_connected
    print(f"Sepolia service: {'Connected' if HAS_SEPOLIA else 'Not connected'}")
except ImportError as e:
    print(f"Warning: Sepolia service not available: {e}")
    sepolia_service = None
    HAS_SEPOLIA = False

# Import skills
try:
    from agent_platform.skills.weather import WeatherSkill
    HAS_WEATHER_SKILL = True
except ImportError:
    HAS_WEATHER_SKILL = False


app = FastAPI(
    title="AI-SNS A2A Server",
    description="A2A Protocol Server with Blockchain Payment Integration",
    version="1.0.0"
)

# Initialize blockchain components
if HAS_BLOCKCHAIN:
    wallet_manager = WalletManager()
    escrow_contract = get_escrow_contract()
    payment_system = get_pay_per_request()
else:
    wallet_manager = None
    escrow_contract = None
    payment_system = None

# Initialize skills
if HAS_WEATHER_SKILL:
    weather_skill = WeatherSkill()
else:
    weather_skill = None

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task storage
tasks_db: Dict[str, Dict] = {}


# ============== Skill Handlers ==============

async def handle_chat(message: str, metadata: Dict) -> str:
    """Handle general chat skill"""
    # Check for weather-related queries
    weather_keywords = ['weather', 'temperature', 'forecast', 'rain', 'sunny', 'cloudy']
    if any(kw in message.lower() for kw in weather_keywords):
        if weather_skill:
            result = await weather_skill.execute(message, metadata)
            if result.get('success'):
                return result.get('response', 'Weather data retrieved.')

    # Default chat response
    return f"[Chat Skill Response] I received your message: '{message}'. I'm an AI agent that can help with general questions, code execution, web search, and file analysis. For weather queries, try asking about specific cities!"


async def handle_code_execution(message: str, metadata: Dict) -> str:
    """Handle code execution skill"""
    # In a real implementation, this would execute code safely
    if "print" in message.lower() or "python" in message.lower():
        return "[Code Execution Skill] Code execution simulated. In production, this would execute Python code in a sandboxed environment."
    return f"[Code Execution Skill] Ready to execute code. Send Python code to execute."


async def handle_web_search(message: str, metadata: Dict) -> str:
    """Handle web search skill"""
    # In a real implementation, this would perform web search
    return f"[Web Search Skill] Simulated search results for: '{message}'. In production, this would return real search results."


async def handle_file_analysis(message: str, metadata: Dict) -> str:
    """Handle file analysis skill"""
    return f"[File Analysis Skill] Ready to analyze files. Upload a file to analyze its contents."


async def handle_weather(message: str, metadata: Dict) -> str:
    """Handle weather skill"""
    if weather_skill:
        result = await weather_skill.execute(message, metadata)
        if result.get('success'):
            return result.get('response', 'Weather data retrieved.')
        else:
            return f"Weather query failed: {result.get('error', 'Unknown error')}"
    return "[Weather Skill] Weather service not available. Please check the configuration."


# Skill dispatcher
SKILL_HANDLERS = {
    "chat": handle_chat,
    "weather": handle_weather,
    "code-execution": handle_code_execution,
    "web-search": handle_web_search,
    "file-analysis": handle_file_analysis,
}


async def dispatch_skill(skill_id: str, message: str, metadata: Dict) -> str:
    """Dispatch to appropriate skill handler"""
    handler = SKILL_HANDLERS.get(skill_id, handle_chat)
    return await handler(message, metadata)


# ============== Agent Card Endpoint ==============

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Agent Card Discovery Endpoint

    This is the standard A2A discovery endpoint.
    Returns the Agent Card with all capabilities and skills.
    """
    agent_json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "static", ".well-known", "agent.json"
    )

    if os.path.exists(agent_json_path):
        return FileResponse(agent_json_path, media_type="application/json")

    # Fallback inline Agent Card
    return {
        "name": "AI-SNS Agent Platform",
        "description": "AI Agent Open Platform supporting A2A and MCP protocols",
        "url": "http://localhost:8000/a2a",
        "version": "1.0.0",
        "protocolVersion": "0.3",
        "capabilities": {
            "streaming": True,
            "pushNotifications": True,
            "stateTransitionHistory": False
        },
        "skills": [
            {
                "id": "chat",
                "name": "General Chat",
                "description": "General conversation and Q&A",
                "inputModes": ["text"],
                "outputModes": ["text"]
            }
        ]
    }


# ============== JSON-RPC 2.0 Endpoint ==============

@app.post("/a2a/rpc")
async def jsonrpc_endpoint(request: Request):
    """
    JSON-RPC 2.0 Endpoint

    Supports the following methods:
    - tasks/send: Create and execute a task
    - tasks/sendSubscribe: Create task with streaming (returns immediately, use SSE for updates)
    - tasks/get: Get task status
    - tasks/cancel: Cancel a task
    - tasks/pushNotification/set: Set webhook for notifications
    """
    try:
        body = await request.json()
    except:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Parse error"},
            "id": None
        }, status_code=400)

    jsonrpc = body.get("jsonrpc")
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    if jsonrpc != "2.0":
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request: jsonrpc must be '2.0'"},
            "id": req_id
        })

    if not method:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request: method is required"},
            "id": req_id
        })

    # Handle methods
    if method == "tasks/send":
        return await handle_tasks_send(params, req_id)
    elif method == "tasks/sendSubscribe":
        return await handle_tasks_send(params, req_id, subscribe=True)
    elif method == "tasks/get":
        return await handle_tasks_get(params, req_id)
    elif method == "tasks/cancel":
        return await handle_tasks_cancel(params, req_id)
    elif method == "tasks/pushNotification/set":
        return await handle_push_notification_set(params, req_id)
    elif method == "tasks/pushNotification/get":
        return await handle_push_notification_get(params, req_id)
    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": req_id
        })


async def handle_tasks_send(params: Dict, req_id: Any, subscribe: bool = False) -> JSONResponse:
    """Handle tasks/send method"""
    task_id = params.get("id") or f"task-{uuid.uuid4().hex[:12]}"
    message_obj = params.get("message", {})
    metadata = params.get("metadata", {})

    # Extract message content
    parts = message_obj.get("parts", [])
    message_text = ""
    for part in parts:
        if part.get("type") == "text":
            message_text += part.get("text", "")

    if not message_text:
        # Try direct content
        message_text = message_obj.get("content", "")

    # Determine skill
    skill_id = metadata.get("skill_id", "chat")

    # Create task
    task = {
        "id": task_id,
        "status": {
            "state": "working",
            "timestamp": datetime.now().isoformat()
        },
        "input_message": message_text,
        "skill_id": skill_id,
        "metadata": metadata,
        "created_at": datetime.now().isoformat()
    }
    tasks_db[task_id] = task

    # Execute skill
    try:
        output = await dispatch_skill(skill_id, message_text, metadata)

        # Update task
        task["status"]["state"] = "completed"
        task["output"] = output
        task["completed_at"] = datetime.now().isoformat()

        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {
                "id": task_id,
                "sessionId": metadata.get("session_id", ""),
                "status": {
                    "state": "completed",
                    "message": "Task completed successfully",
                    "timestamp": task["completed_at"]
                },
                "artifacts": [],
                "history": [
                    {
                        "role": "user",
                        "parts": [{"type": "text", "text": message_text}]
                    },
                    {
                        "role": "agent",
                        "parts": [{"type": "text", "text": output}]
                    }
                ]
            },
            "id": req_id
        })

    except Exception as e:
        task["status"]["state"] = "failed"
        task["error"] = str(e)

        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {
                "id": task_id,
                "status": {
                    "state": "failed",
                    "message": str(e)
                }
            },
            "id": req_id
        })


async def handle_tasks_get(params: Dict, req_id: Any) -> JSONResponse:
    """Handle tasks/get method"""
    task_id = params.get("id")

    if not task_id:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid params: id is required"},
            "id": req_id
        })

    task = tasks_db.get(task_id)

    if not task:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": f"Task not found: {task_id}"},
            "id": req_id
        })

    return JSONResponse({
        "jsonrpc": "2.0",
        "result": {
            "id": task_id,
            "status": task["status"],
            "output": task.get("output"),
            "history": [
                {"role": "user", "parts": [{"type": "text", "text": task.get("input_message", "")}]},
                {"role": "agent", "parts": [{"type": "text", "text": task.get("output", "")}]}
            ] if task.get("output") else []
        },
        "id": req_id
    })


async def handle_tasks_cancel(params: Dict, req_id: Any) -> JSONResponse:
    """Handle tasks/cancel method"""
    task_id = params.get("id")

    if not task_id:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid params: id is required"},
            "id": req_id
        })

    task = tasks_db.get(task_id)

    if not task:
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {"id": task_id, "success": False, "message": "Task not found"},
            "id": req_id
        })

    if task["status"]["state"] in ["completed", "failed", "cancelled"]:
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {"id": task_id, "success": False, "message": "Task already finished"},
            "id": req_id
        })

    task["status"]["state"] = "cancelled"

    return JSONResponse({
        "jsonrpc": "2.0",
        "result": {"id": task_id, "success": True, "status": task["status"]},
        "id": req_id
    })


async def handle_push_notification_set(params: Dict, req_id: Any) -> JSONResponse:
    """Handle tasks/pushNotification/set method"""
    task_id = params.get("id")
    webhook_url = params.get("pushNotificationConfig", {}).get("url")

    return JSONResponse({
        "jsonrpc": "2.0",
        "result": {
            "id": task_id,
            "pushNotificationConfig": {"url": webhook_url}
        },
        "id": req_id
    })


async def handle_push_notification_get(params: Dict, req_id: Any) -> JSONResponse:
    """Handle tasks/pushNotification/get method"""
    task_id = params.get("id")

    return JSONResponse({
        "jsonrpc": "2.0",
        "result": {
            "id": task_id,
            "pushNotificationConfig": None
        },
        "id": req_id
    })


# ============== REST API Endpoints ==============

@app.post("/a2a/tasks")
async def create_task_rest(request: Request):
    """
    REST API: Create Task

    Alternative to JSON-RPC for creating tasks.
    """
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    messages = body.get("messages", [])
    metadata = body.get("metadata", {})

    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")

    # Get first user message
    message_text = ""
    for msg in messages:
        if msg.get("role") == "user":
            message_text = msg.get("content", "")
            break

    task_id = f"task-{uuid.uuid4().hex[:12]}"
    skill_id = metadata.get("skill_id", "chat")

    # Create task
    task = {
        "id": task_id,
        "status": {"state": "working", "timestamp": datetime.now().isoformat()},
        "input_message": message_text,
        "skill_id": skill_id,
        "metadata": metadata,
        "created_at": datetime.now().isoformat()
    }
    tasks_db[task_id] = task

    # Execute skill
    output = await dispatch_skill(skill_id, message_text, metadata)

    task["status"]["state"] = "completed"
    task["output"] = output
    task["completed_at"] = datetime.now().isoformat()

    return {
        "task_id": task_id,
        "status": "completed",
        "output": output,
        "skill_id": skill_id
    }


@app.get("/a2a/tasks/{task_id}")
async def get_task_rest(task_id: str):
    """
    REST API: Get Task Status
    """
    task = tasks_db.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": task["status"]["state"],
        "output": task.get("output"),
        "skill_id": task.get("skill_id"),
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at")
    }


# ============== Health Check ==============

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/")
async def root():
    return {
        "name": "AI-SNS A2A Server",
        "version": "1.0.0",
        "blockchain_enabled": HAS_BLOCKCHAIN,
        "endpoints": {
            "agent_card": "/.well-known/agent.json",
            "jsonrpc": "/a2a/rpc",
            "tasks": "/a2a/tasks",
            "health": "/health",
            "ui": "/a2a_ui",
            "blockchain": {
                "wallet_create": "/api/blockchain/wallet/create",
                "escrow_deposit": "/api/blockchain/escrow/deposit",
                "escrow_release": "/api/blockchain/escrow/release",
                "escrow_refund": "/api/blockchain/escrow/refund"
            }
        }
    }


# ============== Visual Interface ==============

@app.get("/a2a_ui")
async def get_ui():
    """Serve the A2A + Blockchain visual interface"""
    ui_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "static", "a2a_blockchain_ui.html"
    )

    if os.path.exists(ui_path):
        return FileResponse(ui_path, media_type="text/html")

    return HTMLResponse("""
    <html>
        <body style="font-family: sans-serif; padding: 50px; text-align: center;">
            <h1>A2A + Blockchain Interface</h1>
            <p>UI file not found. Please ensure static/a2a_blockchain_ui.html exists.</p>
        </body>
    </html>
    """)


# ============== Blockchain API Endpoints ==============

@app.post("/api/blockchain/wallet/create")
async def create_wallet(request: Request):
    """Create a new blockchain wallet"""
    try:
        body = await request.json()
    except:
        body = {}

    network_mode = body.get("network_mode", "simulation")

    # In simulation mode, always return simulated wallet
    if network_mode == "simulation" or not HAS_BLOCKCHAIN:
        address = "0x" + secrets.token_hex(20)
        return {
            "success": True,
            "address": address,
            "balance_eth": "0.00",
            "did": f"did:ethr:{address}",
            "network": "simulation",
            "simulated": True
        }

    # Sepolia mode - use real blockchain wallet
    try:
        wallet = wallet_manager.create_wallet()
        wallet_address = wallet.address

        # Get real balance from Sepolia if connected
        balance_eth = "0.00"
        sepolia_connected = False
        if sepolia_service and sepolia_service.is_connected:
            sepolia_connected = True
            balance_result = sepolia_service.get_balance(wallet_address)
            if balance_result.get("success"):
                balance_eth = balance_result.get("balance_eth", "0.00")

        return {
            "success": True,
            "address": wallet_address,
            "private_key": wallet.private_key_hex,  # User needs to save this!
            "balance_eth": balance_eth,
            "did": wallet.get_did(),
            "network": "sepolia",
            "sepolia_connected": sepolia_connected,
            "simulated": False,
            "explorer_url": f"https://sepolia.etherscan.io/address/{wallet_address}",
            "warning": "Save your private key securely! It will not be shown again."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/blockchain/escrow/deposit")
async def escrow_deposit(request: Request):
    """Deposit funds to escrow for a task"""
    body = await request.json()
    task_id = body.get("task_id", f"task-{uuid.uuid4().hex[:12]}")
    skill_id = body.get("skill_id", "chat")
    network_mode = body.get("network_mode", "simulation")

    # Skill pricing (in wei)
    skill_prices = {
        "chat": 1000000000000000,
        "weather": 500000000000000,
        "code-execution": 5000000000000000,
        "web-search": 500000000000000,
        "file-analysis": 2000000000000000
    }

    amount = skill_prices.get(skill_id, 1000000000000000)

    # Simulation mode or no blockchain available
    if network_mode == "simulation" or not HAS_BLOCKCHAIN:
        tx_hash = "0x" + secrets.token_hex(32)
        return {
            "success": True,
            "task_id": task_id,
            "tx_hash": tx_hash,
            "amount_wei": str(amount),
            "amount_eth": str(Decimal(amount) / Decimal(10**18)),
            "status": "active",
            "network": "simulation",
            "simulated": True
        }

    # Sepolia mode - use real blockchain
    try:
        result = await escrow_contract.deposit(
            task_id=task_id,
            beneficiary="0x" + "0" * 40,
            amount_wei=amount
        )

        return {
            "success": result.get("success", False),
            "task_id": task_id,
            "tx_hash": result.get("tx_hash"),
            "amount_wei": str(amount),
            "amount_eth": str(Decimal(amount) / Decimal(10**18)),
            "status": "active",
            "network": "sepolia",
            "simulated": False
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/blockchain/escrow/release")
async def escrow_release(request: Request):
    """Release escrow funds to beneficiary"""
    body = await request.json()
    task_id = body.get("task_id")
    network_mode = body.get("network_mode", "simulation")

    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")

    # Simulation mode or no blockchain available
    if network_mode == "simulation" or not HAS_BLOCKCHAIN:
        tx_hash = "0x" + secrets.token_hex(32)
        return {
            "success": True,
            "task_id": task_id,
            "tx_hash": tx_hash,
            "status": "released",
            "network": "simulation",
            "simulated": True
        }

    # Sepolia mode - use real blockchain
    try:
        result = await escrow_contract.release(task_id)
        return {
            "success": result.get("success", False),
            "task_id": task_id,
            "tx_hash": result.get("tx_hash"),
            "status": "released",
            "network": "sepolia",
            "simulated": False
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/blockchain/escrow/refund")
async def escrow_refund(request: Request):
    """Refund escrow to depositor"""
    body = await request.json()
    task_id = body.get("task_id")
    network_mode = body.get("network_mode", "simulation")

    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")

    # Simulation mode or no blockchain available
    if network_mode == "simulation" or not HAS_BLOCKCHAIN:
        tx_hash = "0x" + secrets.token_hex(32)
        return {
            "success": True,
            "task_id": task_id,
            "tx_hash": tx_hash,
            "status": "refunded",
            "network": "simulation",
            "simulated": True
        }

    # Sepolia mode - use real blockchain
    try:
        result = await escrow_contract.refund(task_id)
        return {
            "success": result.get("success", False),
            "task_id": task_id,
            "tx_hash": result.get("tx_hash"),
            "status": "refunded",
            "network": "sepolia",
            "simulated": False
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/blockchain/pricing")
async def get_pricing():
    """Get skill pricing information"""
    return {
        "currency": "ETH",
        "network": "sepolia",
        "skills": {
            "chat": {"price_wei": "1000000000000000", "price_eth": "0.001"},
            "weather": {"price_wei": "500000000000000", "price_eth": "0.0005"},
            "code-execution": {"price_wei": "5000000000000000", "price_eth": "0.005"},
            "web-search": {"price_wei": "500000000000000", "price_eth": "0.0005"},
            "file-analysis": {"price_wei": "2000000000000000", "price_eth": "0.002"}
        }
    }


# ============== Sepolia Network API Endpoints ==============

@app.get("/api/blockchain/sepolia/status")
async def sepolia_status():
    """Get Sepolia network connection status"""
    if not sepolia_service:
        return {
            "connected": False,
            "error": "Sepolia service not initialized",
            "network": "sepolia"
        }

    status = sepolia_service.get_connection_status()
    return {
        "connected": status.connected,
        "rpc_url": status.rpc_url,
        "chain_id": status.chain_id,
        "block_number": status.block_number,
        "error": status.error,
        "network": "sepolia",
        "explorer": "https://sepolia.etherscan.io"
    }


@app.get("/api/blockchain/sepolia/balance/{address}")
async def get_sepolia_balance(address: str):
    """Get ETH balance for an address on Sepolia"""
    if not sepolia_service:
        return {
            "success": False,
            "error": "Sepolia service not initialized",
            "address": address
        }

    return sepolia_service.get_balance(address)


@app.get("/api/blockchain/sepolia/faucets")
async def get_faucets():
    """Get list of Sepolia faucet URLs"""
    from blockchain.sepolia_service import SEPOLIA_FAUCETS
    return {
        "faucets": SEPOLIA_FAUCETS,
        "note": "Use these faucets to get free Sepolia test ETH"
    }


@app.get("/api/blockchain/sepolia/gas-price")
async def get_gas_price():
    """Get current gas price on Sepolia"""
    if not sepolia_service:
        return {"success": False, "error": "Sepolia service not initialized"}

    return sepolia_service.get_gas_price()


@app.get("/api/blockchain/sepolia/tx/{tx_hash}")
async def get_sepolia_transaction(tx_hash: str):
    """Get transaction details from Sepolia"""
    if not sepolia_service:
        return {"success": False, "error": "Sepolia service not initialized"}

    return sepolia_service.get_transaction(tx_hash)


# ============== Main ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="A2A Protocol Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    print("=" * 70)
    print("  AI-SNS A2A Protocol Server + Blockchain Integration")
    print("=" * 70)
    print(f"  Server: http://{args.host}:{args.port}")
    print(f"  Visual UI: http://localhost:{args.port}/a2a_ui")
    print("-" * 70)
    print(f"  Agent Card: http://localhost:{args.port}/.well-known/agent.json")
    print(f"  JSON-RPC: http://localhost:{args.port}/a2a/rpc")
    print(f"  REST API: http://localhost:{args.port}/a2a/tasks")
    print("-" * 70)
    print("  Blockchain API:")
    print(f"    POST /api/blockchain/wallet/create")
    print(f"    POST /api/blockchain/escrow/deposit")
    print(f"    POST /api/blockchain/escrow/release")
    print(f"    POST /api/blockchain/escrow/refund")
    print(f"    GET  /api/blockchain/pricing")
    print("=" * 70)
    print(f"\n  Open http://localhost:{args.port}/a2a_ui in your browser\n")
    print("  Press Ctrl+C to stop\n")

    uvicorn.run(app, host=args.host, port=args.port)
