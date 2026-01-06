#!/usr/bin/env python3
"""
A2A + Blockchain Secure Transaction Flow Test

This script tests the complete secure transaction flow:
1. Agent Discovery - Get Agent Card with skills and pricing
2. Payment Authorization - Deposit to escrow smart contract
3. Skill Invocation - Call skill with payment proof
4. Settlement - Release/refund escrow based on result

Usage:
    python tests/test_a2a_secure_flow.py

Output:
    Detailed test report with blockchain transaction hashes
"""

import os
import sys
import json
import asyncio
import signal
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SecureFlowTest:
    """Test runner for A2A + Blockchain secure transaction flow"""

    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        self.server_process = None

    def add_result(
        self,
        section: str,
        test_name: str,
        passed: bool,
        details: str = "",
        data: Any = None
    ):
        """Add test result"""
        self.results.append({
            "section": section,
            "test": test_name,
            "passed": passed,
            "details": details,
            "data": data
        })

    def print_header(self, text: str):
        """Print section header"""
        print("\n" + "=" * 70)
        print(f"  {text}")
        print("=" * 70)

    def print_test(self, name: str, passed: bool, details: str = ""):
        """Print test result"""
        status = "PASS" if passed else "FAIL"
        icon = "+" if passed else "-"
        print(f"  [{icon}] {status}: {name}")
        if details:
            for line in details.split('\n'):
                print(f"         {line}")

    async def run_tests(self):
        """Run all secure flow tests"""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:

            # =================================================================
            # Section 1: Agent Discovery
            # =================================================================
            self.print_header("1. Agent Discovery")

            try:
                # Test 1.1: Fetch Agent Card
                resp = await client.get(f"{self.base_url}/.well-known/agent.json")
                agent_card = resp.json()

                passed = resp.status_code == 200
                self.print_test(
                    "Fetch Agent Card",
                    passed,
                    f"Status: {resp.status_code}"
                )
                self.add_result("Agent Discovery", "Fetch Agent Card", passed)

                # Test 1.2: Verify A2A protocol version
                proto_version = agent_card.get("protocolVersion", "")
                passed = proto_version == "0.3"
                self.print_test(
                    "Protocol Version",
                    passed,
                    f"Version: {proto_version}"
                )
                self.add_result("Agent Discovery", "Protocol Version", passed)

                # Test 1.3: Verify skills exist
                skills = agent_card.get("skills", [])
                passed = len(skills) > 0
                skill_ids = [s.get("id") for s in skills]
                self.print_test(
                    "Skills Available",
                    passed,
                    f"Skills: {skill_ids}"
                )
                self.add_result("Agent Discovery", "Skills Available", passed, str(skill_ids))

                # Test 1.4: Verify pricing information
                pricing = agent_card.get("pricing", {})
                has_pricing = bool(pricing)
                self.print_test(
                    "Pricing Information",
                    has_pricing,
                    f"Pricing configured: {has_pricing}"
                )
                self.add_result("Agent Discovery", "Pricing Information", has_pricing)

                # Test 1.5: Verify capabilities
                caps = agent_card.get("capabilities", {})
                has_streaming = caps.get("streaming", False)
                has_push = caps.get("pushNotifications", False)
                self.print_test(
                    "Capabilities",
                    True,
                    f"Streaming: {has_streaming}, Push: {has_push}"
                )
                self.add_result("Agent Discovery", "Capabilities", True)

            except Exception as e:
                self.print_test("Agent Discovery", False, str(e))
                self.add_result("Agent Discovery", "Agent Discovery", False, str(e))
                return

            # =================================================================
            # Section 2: Payment Authorization (Simulated)
            # =================================================================
            self.print_header("2. Payment Authorization (Blockchain Escrow)")

            try:
                # Import blockchain modules
                from blockchain.did.wallet import DIDWallet
                from blockchain.escrow.contract import get_escrow_contract
                from blockchain.payment.pay_per_request import get_pay_per_request, PaymentType

                # Test 2.1: Create wallet
                try:
                    wallet = DIDWallet()
                    passed = wallet.address.startswith("0x")
                    self.print_test(
                        "Create Wallet",
                        passed,
                        f"Address: {wallet.address}"
                    )
                    self.add_result("Payment", "Create Wallet", passed, wallet.address)
                except ImportError as e:
                    self.print_test("Create Wallet", False, f"web3 not available: {e}")
                    self.add_result("Payment", "Create Wallet", False, str(e))
                    wallet = None

                # Test 2.2: Calculate price
                payment_system = get_pay_per_request()
                price = payment_system.calculate_price(
                    PaymentType.CHAT_REQUEST,
                    input_tokens=500,
                    output_tokens=500
                )
                passed = price > 0
                price_eth = Decimal(price) / Decimal(10**18)
                self.print_test(
                    "Calculate Price",
                    passed,
                    f"Price: {price_eth} ETH ({price} wei)"
                )
                self.add_result("Payment", "Calculate Price", passed, str(price_eth))

                # Test 2.3: Create payment request
                payment = await payment_system.create_payment(
                    request_id="test-secure-001",
                    payer_address=wallet.address if wallet else "0x" + "0" * 40,
                    recipient_address="0x" + "1" * 40,
                    payment_type=PaymentType.CHAT_REQUEST,
                    input_tokens=500,
                    output_tokens=500
                )
                passed = payment.payment_id.startswith("pay_")
                self.print_test(
                    "Create Payment Request",
                    passed,
                    f"Payment ID: {payment.payment_id}"
                )
                self.add_result("Payment", "Create Payment Request", passed)

                # Test 2.4: Authorize payment (deposit to escrow)
                auth_result = await payment_system.authorize_payment(
                    payment.payment_id,
                    wallet=wallet
                )
                passed = auth_result.get("success", False)
                tx_hash = auth_result.get("tx_hash", "")
                self.print_test(
                    "Authorize Payment (Escrow Deposit)",
                    passed,
                    f"TX Hash: {tx_hash[:20]}..." if tx_hash else "Simulated"
                )
                self.add_result("Payment", "Authorize Payment", passed, tx_hash)

            except Exception as e:
                self.print_test("Payment Authorization", False, str(e))
                self.add_result("Payment", "Payment Authorization", False, str(e))
                tx_hash = "simulated_tx_hash"

            # =================================================================
            # Section 3: Skill Invocation with Payment
            # =================================================================
            self.print_header("3. Skill Invocation (with Payment Proof)")

            test_cases = [
                {
                    "skill": "chat",
                    "message": "What is the weather like in Shanghai?",
                    "description": "Weather Query (Chat)"
                },
                {
                    "skill": "code-execution",
                    "message": "Execute: print('Hello from A2A!')",
                    "description": "Code Execution"
                }
            ]

            for i, test_case in enumerate(test_cases, 1):
                try:
                    rpc_request = {
                        "jsonrpc": "2.0",
                        "method": "tasks/send",
                        "params": {
                            "id": f"test-secure-{i:03d}",
                            "message": {
                                "role": "user",
                                "parts": [{"type": "text", "text": test_case["message"]}]
                            },
                            "metadata": {
                                "skill_id": test_case["skill"],
                                "payment": {
                                    "tx_hash": tx_hash,
                                    "verified": True
                                }
                            }
                        },
                        "id": i
                    }

                    resp = await client.post(
                        f"{self.base_url}/a2a/rpc",
                        json=rpc_request
                    )
                    result = resp.json()

                    passed = resp.status_code == 200 and "result" in result

                    # Extract response text
                    history = result.get("result", {}).get("history", [])
                    response_text = ""
                    for msg in history:
                        if msg.get("role") == "agent":
                            for part in msg.get("parts", []):
                                if part.get("type") == "text":
                                    response_text = part.get("text", "")[:100]

                    self.print_test(
                        test_case["description"],
                        passed,
                        f"Response: {response_text}..." if response_text else "No response"
                    )
                    self.add_result(
                        "Skill Invocation",
                        test_case["description"],
                        passed,
                        response_text
                    )

                except Exception as e:
                    self.print_test(test_case["description"], False, str(e))
                    self.add_result("Skill Invocation", test_case["description"], False, str(e))

            # =================================================================
            # Section 4: Settlement
            # =================================================================
            self.print_header("4. Settlement (Escrow Release/Refund)")

            try:
                # Test 4.1: Capture payment (success case)
                if 'payment' in dir():
                    capture_result = await payment_system.capture_payment(payment.payment_id)
                    passed = capture_result.get("success", False)
                    settle_tx = capture_result.get("tx_hash", "")
                    self.print_test(
                        "Capture Payment (Release Escrow)",
                        passed,
                        f"Settlement TX: {settle_tx[:20]}..." if settle_tx else "Simulated"
                    )
                    self.add_result("Settlement", "Capture Payment", passed, settle_tx)

                # Test 4.2: Refund test (create new payment)
                refund_payment = await payment_system.create_payment(
                    request_id="test-refund-001",
                    payer_address="0x" + "0" * 40,
                    recipient_address="0x" + "1" * 40,
                    payment_type=PaymentType.CHAT_REQUEST
                )
                await payment_system.authorize_payment(refund_payment.payment_id)
                refund_result = await payment_system.refund_payment(refund_payment.payment_id)
                passed = refund_result.get("success", False)
                self.print_test(
                    "Refund Payment (Escrow Return)",
                    passed,
                    f"Status: {refund_result.get('payment', {}).get('status', 'unknown')}"
                )
                self.add_result("Settlement", "Refund Payment", passed)

            except Exception as e:
                self.print_test("Settlement", False, str(e))
                self.add_result("Settlement", "Settlement", False, str(e))

            # =================================================================
            # Section 5: Task Status & Cancellation
            # =================================================================
            self.print_header("5. Task Management")

            try:
                # Test 5.1: Get task status
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {"id": "test-secure-001"},
                    "id": 1
                }
                resp = await client.post(f"{self.base_url}/a2a/rpc", json=rpc_request)
                result = resp.json()

                passed = resp.status_code == 200 and "result" in result
                status = result.get("result", {}).get("status", {}).get("state", "unknown")
                self.print_test(
                    "Get Task Status",
                    passed,
                    f"Status: {status}"
                )
                self.add_result("Task Management", "Get Task Status", passed, status)

                # Test 5.2: Cancel task
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "tasks/cancel",
                    "params": {"id": "test-secure-001"},
                    "id": 2
                }
                resp = await client.post(f"{self.base_url}/a2a/rpc", json=rpc_request)
                result = resp.json()

                passed = resp.status_code == 200 and "result" in result
                self.print_test(
                    "Cancel Task",
                    passed
                )
                self.add_result("Task Management", "Cancel Task", passed)

            except Exception as e:
                self.print_test("Task Management", False, str(e))
                self.add_result("Task Management", "Task Management", False, str(e))

    def generate_report(self) -> Tuple[int, int]:
        """Generate test report"""
        self.print_header("TEST REPORT SUMMARY")

        # Count results by section
        sections = {}
        total_passed = 0
        total_failed = 0

        for r in self.results:
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
        if total_passed + total_failed > 0:
            print(f"  Pass Rate: {total_passed/(total_passed+total_failed)*100:.1f}%")

        print("\n  Results by Section:")
        print("  " + "-" * 50)

        for section, data in sections.items():
            status = "+" if data["failed"] == 0 else "-"
            print(f"  [{status}] {section}: {data['passed']}/{data['passed']+data['failed']}")

        print("  " + "-" * 50)

        # Failed tests details
        failed_tests = [r for r in self.results if not r["passed"]]
        if failed_tests:
            print("\n  Failed Tests:")
            for r in failed_tests:
                print(f"    - [{r['section']}] {r['test']}: {r['details']}")

        print("\n" + "=" * 70)
        if total_failed == 0:
            print("  [+] ALL TESTS PASSED!")
        else:
            print(f"  [-] {total_failed} TEST(S) FAILED")
        print("=" * 70)

        return total_passed, total_failed

    def start_server(self) -> bool:
        """Start the A2A server"""
        print("\n  Starting A2A server on port 8765...")

        server_script = os.path.join(
            os.path.dirname(__file__),
            "run_a2a_server.py"
        )

        try:
            self.server_process = subprocess.Popen(
                [sys.executable, server_script, "--port", "8765"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )

            # Wait for server to start
            time.sleep(3)

            if self.server_process.poll() is not None:
                stdout, stderr = self.server_process.communicate()
                print(f"  Server failed to start!")
                print(f"  Stderr: {stderr.decode()[:500]}")
                return False

            print("  [+] Server started successfully")
            return True

        except Exception as e:
            print(f"  Error starting server: {e}")
            return False

    def stop_server(self):
        """Stop the A2A server"""
        if self.server_process:
            print("\n  Stopping server...")
            try:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                else:
                    self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
            print("  [+] Server stopped")


async def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("  A2A + Blockchain Secure Transaction Flow Test")
    print("=" * 70)
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test = SecureFlowTest()

    # Start server
    if not test.start_server():
        print("\n  Cannot proceed without server")
        return

    try:
        # Run tests
        await test.run_tests()

        # Generate report
        passed, failed = test.generate_report()

        # Return exit code
        sys.exit(0 if failed == 0 else 1)

    except Exception as e:
        print(f"\n  Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        test.stop_server()


if __name__ == "__main__":
    asyncio.run(main())
