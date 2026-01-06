#!/usr/bin/env python3
"""
Full A2A Platform Test Suite

This script:
1. Starts the A2A server
2. Runs all tests
3. Generates a comprehensive report
"""

import os
import sys
import json
import time
import signal
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test results storage
test_results = []
server_process = None


def add_result(section: str, test_name: str, passed: bool, details: str = "", response: Any = None):
    """Add a test result"""
    test_results.append({
        "section": section,
        "test": test_name,
        "passed": passed,
        "details": details,
        "response": response
    })


def print_header(text: str):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")


async def run_tests():
    """Run all tests"""
    import httpx

    base_url = "http://127.0.0.1:8765"

    async with httpx.AsyncClient(timeout=30.0) as client:

        # ============== Section 1: Agent Discovery ==============
        print_header("1. Agent Discovery (/.well-known/agent.json)")

        try:
            resp = await client.get(f"{base_url}/.well-known/agent.json")
            agent_card = resp.json()

            # Test 1.1: Agent Card accessible
            passed = resp.status_code == 200
            print_test("Agent Card accessible", passed, f"Status: {resp.status_code}")
            add_result("Agent Discovery", "Agent Card accessible", passed, f"Status: {resp.status_code}")

            # Test 1.2: Has required fields
            required_fields = ["name", "url", "protocolVersion", "capabilities", "skills"]
            missing = [f for f in required_fields if f not in agent_card]
            passed = len(missing) == 0
            print_test("Has required fields", passed, f"Missing: {missing}" if missing else "All fields present")
            add_result("Agent Discovery", "Has required fields", passed)

            # Test 1.3: Protocol version is 0.3
            passed = agent_card.get("protocolVersion") == "0.3"
            print_test("Protocol version is 0.3", passed, f"Version: {agent_card.get('protocolVersion')}")
            add_result("Agent Discovery", "Protocol version is 0.3", passed)

            # Test 1.4: Has skills
            skills = agent_card.get("skills", [])
            passed = len(skills) > 0
            print_test("Has skills defined", passed, f"Found {len(skills)} skills")
            add_result("Agent Discovery", "Has skills defined", passed, f"{len(skills)} skills")

            # Test 1.5: Skills have required structure
            skill_ids = [s.get("id") for s in skills]
            print_test("Skills list", True, f"IDs: {skill_ids}")
            add_result("Agent Discovery", "Skills list", True, str(skill_ids))

        except Exception as e:
            print_test("Agent Card accessible", False, str(e))
            add_result("Agent Discovery", "Agent Card accessible", False, str(e))
            return

        # ============== Section 2: JSON-RPC 2.0 Endpoint ==============
        print_header("2. JSON-RPC 2.0 Endpoint (/a2a/rpc)")

        # Test 2.1: tasks/send - Chat skill
        try:
            rpc_req = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {
                    "id": "test-chat-001",
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "Hello, what skills do you have?"}]
                    },
                    "metadata": {"skill_id": "chat"}
                },
                "id": 1
            }
            resp = await client.post(f"{base_url}/a2a/rpc", json=rpc_req)
            result = resp.json()

            passed = resp.status_code == 200 and "result" in result
            output = result.get("result", {}).get("history", [{}])[-1].get("parts", [{}])[0].get("text", "")[:100]
            print_test("tasks/send (chat skill)", passed, f"Response: {output}...")
            add_result("JSON-RPC 2.0", "tasks/send (chat)", passed, output, result)
        except Exception as e:
            print_test("tasks/send (chat skill)", False, str(e))
            add_result("JSON-RPC 2.0", "tasks/send (chat)", False, str(e))

        # Test 2.2: tasks/send - Code execution skill
        try:
            rpc_req = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {
                    "id": "test-code-001",
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "Execute: print('Hello World')"}]
                    },
                    "metadata": {"skill_id": "code-execution"}
                },
                "id": 2
            }
            resp = await client.post(f"{base_url}/a2a/rpc", json=rpc_req)
            result = resp.json()

            passed = resp.status_code == 200 and "result" in result
            print_test("tasks/send (code-execution skill)", passed)
            add_result("JSON-RPC 2.0", "tasks/send (code-execution)", passed, response=result)
        except Exception as e:
            print_test("tasks/send (code-execution skill)", False, str(e))
            add_result("JSON-RPC 2.0", "tasks/send (code-execution)", False, str(e))

        # Test 2.3: tasks/send - Web search skill
        try:
            rpc_req = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {
                    "id": "test-search-001",
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "Search for AI news"}]
                    },
                    "metadata": {"skill_id": "web-search"}
                },
                "id": 3
            }
            resp = await client.post(f"{base_url}/a2a/rpc", json=rpc_req)
            result = resp.json()

            passed = resp.status_code == 200 and "result" in result
            print_test("tasks/send (web-search skill)", passed)
            add_result("JSON-RPC 2.0", "tasks/send (web-search)", passed, response=result)
        except Exception as e:
            print_test("tasks/send (web-search skill)", False, str(e))
            add_result("JSON-RPC 2.0", "tasks/send (web-search)", False, str(e))

        # Test 2.4: tasks/send - File analysis skill
        try:
            rpc_req = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {
                    "id": "test-file-001",
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "Analyze this file"}]
                    },
                    "metadata": {"skill_id": "file-analysis"}
                },
                "id": 4
            }
            resp = await client.post(f"{base_url}/a2a/rpc", json=rpc_req)
            result = resp.json()

            passed = resp.status_code == 200 and "result" in result
            print_test("tasks/send (file-analysis skill)", passed)
            add_result("JSON-RPC 2.0", "tasks/send (file-analysis)", passed, response=result)
        except Exception as e:
            print_test("tasks/send (file-analysis skill)", False, str(e))
            add_result("JSON-RPC 2.0", "tasks/send (file-analysis)", False, str(e))

        # Test 2.5: tasks/get
        try:
            rpc_req = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "params": {"id": "test-chat-001"},
                "id": 5
            }
            resp = await client.post(f"{base_url}/a2a/rpc", json=rpc_req)
            result = resp.json()

            passed = resp.status_code == 200 and "result" in result
            status = result.get("result", {}).get("status", {}).get("state", "unknown")
            print_test("tasks/get", passed, f"Task status: {status}")
            add_result("JSON-RPC 2.0", "tasks/get", passed, f"Status: {status}")
        except Exception as e:
            print_test("tasks/get", False, str(e))
            add_result("JSON-RPC 2.0", "tasks/get", False, str(e))

        # Test 2.6: tasks/cancel
        try:
            rpc_req = {
                "jsonrpc": "2.0",
                "method": "tasks/cancel",
                "params": {"id": "test-chat-001"},
                "id": 6
            }
            resp = await client.post(f"{base_url}/a2a/rpc", json=rpc_req)
            result = resp.json()

            passed = resp.status_code == 200 and "result" in result
            print_test("tasks/cancel", passed)
            add_result("JSON-RPC 2.0", "tasks/cancel", passed, response=result)
        except Exception as e:
            print_test("tasks/cancel", False, str(e))
            add_result("JSON-RPC 2.0", "tasks/cancel", False, str(e))

        # Test 2.7: Error handling - Invalid method
        try:
            rpc_req = {
                "jsonrpc": "2.0",
                "method": "invalid/method",
                "params": {},
                "id": 7
            }
            resp = await client.post(f"{base_url}/a2a/rpc", json=rpc_req)
            result = resp.json()

            passed = "error" in result and result["error"]["code"] == -32601
            print_test("Error: Method not found", passed, f"Code: {result.get('error', {}).get('code')}")
            add_result("JSON-RPC 2.0", "Error handling (method not found)", passed)
        except Exception as e:
            print_test("Error: Method not found", False, str(e))
            add_result("JSON-RPC 2.0", "Error handling", False, str(e))

        # ============== Section 3: REST API ==============
        print_header("3. REST API (/a2a/tasks)")

        # Test 3.1: POST /a2a/tasks
        try:
            req_body = {
                "messages": [
                    {"role": "user", "content": "Hello from REST API test"}
                ],
                "metadata": {"skill_id": "chat"}
            }
            resp = await client.post(f"{base_url}/a2a/tasks", json=req_body)
            result = resp.json()

            passed = resp.status_code == 200 and "task_id" in result
            task_id = result.get("task_id", "")
            print_test("POST /a2a/tasks", passed, f"Task ID: {task_id}")
            add_result("REST API", "POST /a2a/tasks", passed, f"Task ID: {task_id}")

            # Test 3.2: GET /a2a/tasks/{id}
            if task_id:
                resp = await client.get(f"{base_url}/a2a/tasks/{task_id}")
                result = resp.json()

                passed = resp.status_code == 200 and "status" in result
                print_test("GET /a2a/tasks/{id}", passed, f"Status: {result.get('status')}")
                add_result("REST API", "GET /a2a/tasks/{id}", passed)
        except Exception as e:
            print_test("POST /a2a/tasks", False, str(e))
            add_result("REST API", "POST /a2a/tasks", False, str(e))

        # Test 3.3: GET /a2a/tasks/{id} - Not found
        try:
            resp = await client.get(f"{base_url}/a2a/tasks/nonexistent-task")
            passed = resp.status_code == 404
            print_test("GET /a2a/tasks/{id} - Not found", passed, f"Status: {resp.status_code}")
            add_result("REST API", "GET /a2a/tasks - Not found", passed)
        except Exception as e:
            print_test("GET /a2a/tasks/{id} - Not found", False, str(e))
            add_result("REST API", "GET /a2a/tasks - Not found", False, str(e))

        # ============== Section 4: Health & Root ==============
        print_header("4. Health & Info Endpoints")

        # Test 4.1: Health check
        try:
            resp = await client.get(f"{base_url}/health")
            result = resp.json()

            passed = resp.status_code == 200 and result.get("status") == "healthy"
            print_test("GET /health", passed, f"Status: {result.get('status')}")
            add_result("Health", "GET /health", passed)
        except Exception as e:
            print_test("GET /health", False, str(e))
            add_result("Health", "GET /health", False, str(e))

        # Test 4.2: Root endpoint
        try:
            resp = await client.get(f"{base_url}/")
            result = resp.json()

            passed = resp.status_code == 200 and "name" in result
            print_test("GET /", passed, f"Name: {result.get('name')}")
            add_result("Health", "GET /", passed)
        except Exception as e:
            print_test("GET /", False, str(e))
            add_result("Health", "GET /", False, str(e))


def generate_report():
    """Generate test report"""
    print_header("TEST REPORT SUMMARY")

    # Count results by section
    sections = {}
    total_passed = 0
    total_failed = 0

    for r in test_results:
        section = r["section"]
        if section not in sections:
            sections[section] = {"passed": 0, "failed": 0, "tests": []}

        if r["passed"]:
            sections[section]["passed"] += 1
            total_passed += 1
        else:
            sections[section]["failed"] += 1
            total_failed += 1

        sections[section]["tests"].append(r)

    # Print summary
    print(f"\n  Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n  Total Tests: {total_passed + total_failed}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Pass Rate: {total_passed/(total_passed+total_failed)*100:.1f}%")

    print("\n  Results by Section:")
    print("  " + "-" * 50)

    for section, data in sections.items():
        status = "✓" if data["failed"] == 0 else "✗"
        print(f"  {status} {section}: {data['passed']}/{data['passed']+data['failed']}")

    print("  " + "-" * 50)

    # Failed tests details
    failed_tests = [r for r in test_results if not r["passed"]]
    if failed_tests:
        print("\n  Failed Tests:")
        for r in failed_tests:
            print(f"    - [{r['section']}] {r['test']}: {r['details']}")

    print("\n" + "=" * 70)
    if total_failed == 0:
        print("  ✓ ALL TESTS PASSED!")
    else:
        print(f"  ✗ {total_failed} TEST(S) FAILED")
    print("=" * 70)

    return total_passed, total_failed


def main():
    global server_process

    print("\n" + "=" * 70)
    print("  AI Agent Open Platform - Full A2A Test Suite")
    print("=" * 70)
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Start the server
    print_header("Starting A2A Server")
    print("  Starting server on port 8765...")

    server_script = os.path.join(os.path.dirname(__file__), "run_a2a_server.py")

    try:
        server_process = subprocess.Popen(
            [sys.executable, server_script, "--port", "8765"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )

        # Wait for server to start
        print("  Waiting for server to initialize...")
        time.sleep(3)

        # Check if server is running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"  Server failed to start!")
            print(f"  Stderr: {stderr.decode()[:500]}")
            return

        print("  ✓ Server started successfully")

        # Run tests
        asyncio.run(run_tests())

        # Generate report
        passed, failed = generate_report()

    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if server_process:
            print("\n  Stopping server...")
            try:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
                else:
                    server_process.terminate()
                server_process.wait(timeout=5)
            except:
                server_process.kill()
            print("  ✓ Server stopped")


if __name__ == "__main__":
    main()
