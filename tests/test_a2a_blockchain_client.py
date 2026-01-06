#!/usr/bin/env python3
"""
A2A + Blockchain Secure Transaction Client

This client demonstrates the complete secure A2A transaction flow:
1. Discover Agent (get Agent Card)
2. Authorize payment (deposit to escrow)
3. Call skill with payment proof
4. Receive result + settlement transaction

Usage:
    python tests/test_a2a_blockchain_client.py --url http://localhost:8765
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from blockchain.did.wallet import DIDWallet, WalletManager
from blockchain.escrow.contract import EscrowContract, get_escrow_contract
from blockchain.payment.pay_per_request import PayPerRequest, PaymentType, get_pay_per_request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class A2ABlockchainClient:
    """
    A2A Client with Blockchain Payment Integration

    This client:
    1. Discovers agents via Agent Card
    2. Stakes payment in escrow before calling
    3. Calls skills with payment proof
    4. Handles automatic settlement
    """

    def __init__(
        self,
        agent_url: str,
        wallet: Optional[DIDWallet] = None
    ):
        """
        Initialize A2A blockchain client.

        Args:
            agent_url: Base URL of the A2A agent
            wallet: Optional wallet for payments
        """
        self.agent_url = agent_url.rstrip('/')
        self.wallet = wallet or self._create_wallet()
        self.escrow = get_escrow_contract()
        self.payment_system = get_pay_per_request()

        # Cache agent card
        self._agent_card: Optional[Dict[str, Any]] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    def _create_wallet(self) -> DIDWallet:
        """Create a new wallet for payments"""
        try:
            wallet = DIDWallet()
            logger.info(f"Created wallet: {wallet.address}")
            return wallet
        except ImportError:
            logger.warning("web3 not available, using mock wallet")
            return None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client"""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """Close client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    # =================================================================
    # Step 1: Agent Discovery
    # =================================================================

    async def discover_agent(self) -> Dict[str, Any]:
        """
        Discover agent by fetching Agent Card.

        Returns:
            Agent Card with capabilities, skills, and pricing
        """
        client = await self._get_client()

        # Fetch agent card from well-known location
        url = f"{self.agent_url}/.well-known/agent.json"
        logger.info(f"Discovering agent at: {url}")

        response = await client.get(url)
        response.raise_for_status()

        self._agent_card = response.json()

        logger.info(f"Discovered agent: {self._agent_card.get('name')}")
        logger.info(f"Protocol version: {self._agent_card.get('protocolVersion')}")
        logger.info(f"Skills: {[s['id'] for s in self._agent_card.get('skills', [])]}")

        return self._agent_card

    def get_skills(self) -> list:
        """Get available skills from cached agent card"""
        if not self._agent_card:
            raise RuntimeError("Agent not discovered. Call discover_agent() first.")
        return self._agent_card.get('skills', [])

    def get_skill_by_id(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get skill details by ID"""
        for skill in self.get_skills():
            if skill.get('id') == skill_id:
                return skill
        return None

    def get_pricing(self) -> Dict[str, Any]:
        """Get pricing information from agent card"""
        if not self._agent_card:
            raise RuntimeError("Agent not discovered. Call discover_agent() first.")
        return self._agent_card.get('pricing', {})

    # =================================================================
    # Step 2: Payment Authorization (Deposit to Escrow)
    # =================================================================

    async def authorize_payment(
        self,
        task_id: str,
        skill_id: str,
        estimated_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Authorize payment by depositing to escrow.

        Args:
            task_id: Unique task identifier
            skill_id: Skill to call
            estimated_tokens: Estimated token usage

        Returns:
            Payment authorization with tx_hash
        """
        # Calculate price based on skill
        payment_type = self._skill_to_payment_type(skill_id)
        amount_wei = self.payment_system.calculate_price(
            payment_type,
            input_tokens=estimated_tokens,
            output_tokens=estimated_tokens
        )

        logger.info(f"Calculated price: {Decimal(amount_wei) / Decimal(10**18)} ETH")

        # Get beneficiary address from agent card
        beneficiary = self._agent_card.get('payment', {}).get(
            'wallet_address',
            '0x' + '0' * 40  # Default for simulation
        )

        # Create payment request
        payment = await self.payment_system.create_payment(
            request_id=task_id,
            payer_address=self.wallet.address if self.wallet else '0x' + '0' * 40,
            recipient_address=beneficiary,
            payment_type=payment_type,
            input_tokens=estimated_tokens,
            output_tokens=estimated_tokens
        )

        # Authorize (deposit to escrow)
        result = await self.payment_system.authorize_payment(
            payment.payment_id,
            wallet=self.wallet
        )

        logger.info(f"Payment authorized: {result.get('tx_hash')}")

        return {
            "payment_id": payment.payment_id,
            "task_id": task_id,
            "amount_wei": amount_wei,
            "amount_eth": str(Decimal(amount_wei) / Decimal(10**18)),
            "tx_hash": result.get('tx_hash'),
            "status": "authorized"
        }

    def _skill_to_payment_type(self, skill_id: str) -> PaymentType:
        """Map skill ID to payment type"""
        mapping = {
            'chat': PaymentType.CHAT_REQUEST,
            'code-execution': PaymentType.TASK_EXECUTION,
            'web-search': PaymentType.API_CALL,
            'file-analysis': PaymentType.FILE_PROCESSING,
            'weather': PaymentType.API_CALL
        }
        return mapping.get(skill_id, PaymentType.CHAT_REQUEST)

    # =================================================================
    # Step 3: Call Skill with Payment Proof
    # =================================================================

    async def call_skill(
        self,
        task_id: str,
        skill_id: str,
        message: str,
        payment_tx_hash: str
    ) -> Dict[str, Any]:
        """
        Call a skill with payment proof.

        Args:
            task_id: Task identifier
            skill_id: Skill to invoke
            message: User message
            payment_tx_hash: Payment transaction hash

        Returns:
            Task result with settlement info
        """
        client = await self._get_client()

        # Build JSON-RPC request
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "id": task_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}]
                },
                "metadata": {
                    "skill_id": skill_id,
                    "payment": {
                        "tx_hash": payment_tx_hash,
                        "payer_address": self.wallet.address if self.wallet else None
                    }
                }
            },
            "id": 1
        }

        logger.info(f"Calling skill '{skill_id}' with payment proof")

        # Send request
        url = f"{self.agent_url}/a2a/rpc"
        response = await client.post(url, json=rpc_request)
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            logger.error(f"Skill call failed: {result['error']}")
            return result

        return result.get("result", {})

    # =================================================================
    # Step 4: Complete Transaction Flow
    # =================================================================

    async def execute_secure_task(
        self,
        skill_id: str,
        message: str,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete secure task with blockchain payment.

        This method:
        1. Discovers agent (if not cached)
        2. Authorizes payment
        3. Calls skill
        4. Returns result with transaction proof

        Args:
            skill_id: Skill to invoke
            message: User message
            task_id: Optional task ID (auto-generated if not provided)

        Returns:
            Complete task result with blockchain proof
        """
        import hashlib

        # Generate task ID if not provided
        if not task_id:
            hash_input = f"{skill_id}_{message}_{datetime.now().isoformat()}"
            task_id = f"task_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"

        result = {
            "task_id": task_id,
            "skill_id": skill_id,
            "steps": [],
            "success": False
        }

        try:
            # Step 1: Discover agent
            if not self._agent_card:
                agent_card = await self.discover_agent()
                result["steps"].append({
                    "step": 1,
                    "name": "Agent Discovery",
                    "status": "success",
                    "agent_name": agent_card.get("name"),
                    "skills": [s["id"] for s in agent_card.get("skills", [])]
                })

            # Verify skill exists
            skill = self.get_skill_by_id(skill_id)
            if not skill:
                raise ValueError(f"Skill '{skill_id}' not found")

            # Step 2: Authorize payment
            payment = await self.authorize_payment(
                task_id=task_id,
                skill_id=skill_id
            )
            result["steps"].append({
                "step": 2,
                "name": "Payment Authorization",
                "status": "success",
                "payment_id": payment["payment_id"],
                "amount_eth": payment["amount_eth"],
                "deposit_tx_hash": payment["tx_hash"]
            })
            result["payment"] = payment

            # Step 3: Call skill
            task_result = await self.call_skill(
                task_id=task_id,
                skill_id=skill_id,
                message=message,
                payment_tx_hash=payment["tx_hash"]
            )

            # Extract response
            history = task_result.get("history", [])
            agent_response = ""
            for msg in history:
                if msg.get("role") == "agent":
                    parts = msg.get("parts", [])
                    for part in parts:
                        if part.get("type") == "text":
                            agent_response = part.get("text", "")

            result["steps"].append({
                "step": 3,
                "name": "Skill Execution",
                "status": task_result.get("status", {}).get("state", "unknown"),
                "response_preview": agent_response[:200] + "..." if len(agent_response) > 200 else agent_response
            })
            result["response"] = agent_response
            result["task_status"] = task_result.get("status", {})

            # Step 4: Settlement (automatic in the response)
            settlement_tx = task_result.get("settlement", {}).get("tx_hash")
            result["steps"].append({
                "step": 4,
                "name": "Settlement",
                "status": "success" if settlement_tx else "pending",
                "settlement_tx_hash": settlement_tx
            })
            result["settlement"] = task_result.get("settlement", {})

            result["success"] = True

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            result["error"] = str(e)
            result["steps"].append({
                "step": "error",
                "name": "Error",
                "status": "failed",
                "message": str(e)
            })

        return result

    # =================================================================
    # Utility Methods
    # =================================================================

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status via JSON-RPC"""
        client = await self._get_client()

        rpc_request = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": task_id},
            "id": 1
        }

        response = await client.post(
            f"{self.agent_url}/a2a/rpc",
            json=rpc_request
        )
        response.raise_for_status()

        return response.json()

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel task and refund payment"""
        client = await self._get_client()

        rpc_request = {
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "params": {"id": task_id},
            "id": 1
        }

        response = await client.post(
            f"{self.agent_url}/a2a/rpc",
            json=rpc_request
        )
        response.raise_for_status()

        return response.json()


async def run_demo(url: str):
    """Run demonstration of secure A2A transaction"""
    print("\n" + "=" * 70)
    print("  A2A + Blockchain Secure Transaction Demo")
    print("=" * 70)

    client = A2ABlockchainClient(url)

    try:
        # Example 1: Weather query
        print("\n--- Example 1: Weather Query ---")
        result = await client.execute_secure_task(
            skill_id="chat",
            message="What's the weather like in Shanghai today?"
        )

        print(f"\nTask ID: {result['task_id']}")
        print(f"Success: {result['success']}")

        print("\nTransaction Flow:")
        for step in result['steps']:
            status = "✓" if step['status'] in ['success', 'completed'] else "✗"
            print(f"  {status} Step {step.get('step', '?')}: {step['name']}")
            if step.get('deposit_tx_hash'):
                print(f"      Deposit TX: {step['deposit_tx_hash'][:16]}...")
            if step.get('settlement_tx_hash'):
                print(f"      Settlement TX: {step['settlement_tx_hash'][:16]}...")

        if result.get('payment'):
            print(f"\nPayment: {result['payment']['amount_eth']} ETH")

        if result.get('response'):
            print(f"\nResponse: {result['response'][:300]}...")

        # Example 2: Code execution
        print("\n\n--- Example 2: Code Execution ---")
        result2 = await client.execute_secure_task(
            skill_id="code-execution",
            message="Execute: print('2 + 2 =', 2 + 2)"
        )

        print(f"\nTask ID: {result2['task_id']}")
        print(f"Success: {result2['success']}")

        if result2.get('payment'):
            print(f"Payment: {result2['payment']['amount_eth']} ETH")

    finally:
        await client.close()

    print("\n" + "=" * 70)
    print("  Demo Complete")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="A2A + Blockchain Secure Transaction Client"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8765",
        help="A2A agent URL"
    )
    parser.add_argument(
        "--skill",
        default="chat",
        help="Skill to invoke"
    )
    parser.add_argument(
        "--message",
        default="What's the weather like today?",
        help="Message to send"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo mode"
    )

    args = parser.parse_args()

    if args.demo:
        asyncio.run(run_demo(args.url))
    else:
        # Single task execution
        async def run_single():
            client = A2ABlockchainClient(args.url)
            try:
                result = await client.execute_secure_task(
                    skill_id=args.skill,
                    message=args.message
                )
                print(json.dumps(result, indent=2, default=str))
            finally:
                await client.close()

        asyncio.run(run_single())


if __name__ == "__main__":
    main()
