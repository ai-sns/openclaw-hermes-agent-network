#!/usr/bin/env python3
"""
A2A Protocol Client Test Script

This script demonstrates how to:
1. Discover an agent via /.well-known/agent.json
2. See available skills
3. Call skills via JSON-RPC 2.0 or REST API

Usage:
    Step 1: Start the A2A server first:
        python tests/run_a2a_server.py

    Step 2: Run this client script:
        python tests/test_a2a_client.py
"""

import asyncio
import json
import httpx
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Default server URL
BASE_URL = "http://localhost:8000"


class A2AClient:
    """A2A Protocol Client for testing"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.agent_card = None

    async def close(self):
        await self.client.aclose()

    # ============== Step 1: Agent Discovery ==============

    async def discover_agent(self) -> Dict[str, Any]:
        """
        Step 1: Discover agent via /.well-known/agent.json

        This is the standard A2A discovery mechanism.
        Any A2A-compatible agent MUST expose this endpoint.
        """
        print("\n" + "="*60)
        print("Step 1: Agent Discovery")
        print("="*60)

        url = f"{self.base_url}/.well-known/agent.json"
        print(f"\n[Request] GET {url}")

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            self.agent_card = response.json()

            print(f"[Response] Status: {response.status_code}")
            print("\n[Agent Card Summary]")
            print(f"  Name: {self.agent_card.get('name')}")
            print(f"  Description: {self.agent_card.get('description')}")
            print(f"  URL: {self.agent_card.get('url')}")
            print(f"  Protocol Version: {self.agent_card.get('protocolVersion')}")

            return self.agent_card
        except Exception as e:
            print(f"[Error] Failed to discover agent: {e}")
            return {}

    # ============== Step 2: View Available Skills ==============

    async def list_skills(self) -> list:
        """
        Step 2: List all available skills

        Skills are defined in the Agent Card and represent
        the capabilities the agent can perform.
        """
        print("\n" + "="*60)
        print("Step 2: Available Skills")
        print("="*60)

        if not self.agent_card:
            await self.discover_agent()

        skills = self.agent_card.get('skills', [])

        print(f"\nFound {len(skills)} skills:\n")

        for i, skill in enumerate(skills, 1):
            print(f"  [{i}] {skill.get('name')} (id: {skill.get('id')})")
            print(f"      Description: {skill.get('description')}")
            print(f"      Tags: {', '.join(skill.get('tags', []))}")
            print(f"      Input Modes: {', '.join(skill.get('inputModes', []))}")
            print(f"      Output Modes: {', '.join(skill.get('outputModes', []))}")
            examples = skill.get('examples', [])
            if examples:
                print(f"      Examples:")
                for ex in examples[:2]:  # Show first 2 examples
                    print(f"        - {ex}")
            print()

        return skills

    # ============== Step 3: Call Skill via JSON-RPC 2.0 ==============

    async def call_skill_jsonrpc(
        self,
        message: str,
        skill_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 3a: Call a skill using JSON-RPC 2.0

        This is the Google A2A standard method using JSON-RPC 2.0.
        Method: tasks/send
        """
        print("\n" + "="*60)
        print("Step 3a: Call Skill via JSON-RPC 2.0")
        print("="*60)

        url = f"{self.base_url}/a2a/rpc"

        # Generate task ID if not provided
        if not task_id:
            task_id = f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Build JSON-RPC request
        request_body = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "id": task_id,
                "message": {
                    "role": "user",
                    "parts": [
                        {"type": "text", "text": message}
                    ]
                },
                "acceptedOutputModes": ["text"]
            },
            "id": 1
        }

        # Add skill hint if specified
        if skill_id:
            request_body["params"]["metadata"] = {"skill_id": skill_id}

        print(f"\n[Request] POST {url}")
        print(f"[Body]")
        print(json.dumps(request_body, indent=2, ensure_ascii=False))

        try:
            response = await self.client.post(url, json=request_body)
            result = response.json()

            print(f"\n[Response] Status: {response.status_code}")
            print(f"[Body]")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            return result
        except Exception as e:
            print(f"[Error] {e}")
            return {"error": str(e)}

    # ============== Step 3b: Call Skill via REST API ==============

    async def call_skill_rest(
        self,
        message: str,
        skill_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 3b: Call a skill using REST API

        Alternative method using traditional REST endpoints.
        """
        print("\n" + "="*60)
        print("Step 3b: Call Skill via REST API")
        print("="*60)

        url = f"{self.base_url}/a2a/tasks"

        request_body = {
            "messages": [
                {"role": "user", "content": message}
            ],
            "metadata": {}
        }

        if skill_id:
            request_body["metadata"]["skill_id"] = skill_id

        print(f"\n[Request] POST {url}")
        print(f"[Body]")
        print(json.dumps(request_body, indent=2, ensure_ascii=False))

        try:
            response = await self.client.post(url, json=request_body)
            result = response.json()

            print(f"\n[Response] Status: {response.status_code}")
            print(f"[Body]")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            return result
        except Exception as e:
            print(f"[Error] {e}")
            return {"error": str(e)}

    # ============== Step 4: Get Task Status ==============

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Step 4: Get task status

        For long-running tasks, you can poll for status.
        """
        print("\n" + "="*60)
        print("Step 4: Get Task Status")
        print("="*60)

        # Via JSON-RPC
        url = f"{self.base_url}/a2a/rpc"
        request_body = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": task_id},
            "id": 2
        }

        print(f"\n[Request] POST {url}")
        print(f"[Method] tasks/get")
        print(f"[Task ID] {task_id}")

        try:
            response = await self.client.post(url, json=request_body)
            result = response.json()

            print(f"\n[Response] Status: {response.status_code}")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            return result
        except Exception as e:
            print(f"[Error] {e}")
            return {"error": str(e)}


async def interactive_demo():
    """Interactive demo for testing A2A calls"""

    print("\n" + "="*70)
    print("  A2A Protocol Client - Interactive Demo")
    print("="*70)
    print("\nThis demo shows how to discover and call an A2A agent.\n")

    # Check if server URL is provided
    base_url = BASE_URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"Target Server: {base_url}")

    client = A2AClient(base_url)

    try:
        # Step 1: Discover agent
        agent_card = await client.discover_agent()

        if not agent_card:
            print("\n[!] Cannot connect to server. Make sure the A2A server is running.")
            print("    Run: python tests/run_a2a_server.py")
            return

        # Step 2: List skills
        skills = await client.list_skills()

        # Interactive skill selection
        print("\n" + "="*60)
        print("Step 3: Call a Skill")
        print("="*60)

        print("\nSelect a skill to test:")
        for i, skill in enumerate(skills, 1):
            print(f"  {i}. {skill.get('name')} ({skill.get('id')})")
        print(f"  0. Exit")

        while True:
            try:
                choice = input("\nEnter skill number (or 0 to exit): ").strip()
                if choice == '0':
                    break

                skill_idx = int(choice) - 1
                if 0 <= skill_idx < len(skills):
                    selected_skill = skills[skill_idx]
                    print(f"\nSelected: {selected_skill.get('name')}")
                    print(f"Examples: {', '.join(selected_skill.get('examples', []))}")

                    message = input("\nEnter your message: ").strip()
                    if message:
                        # Call via JSON-RPC
                        result = await client.call_skill_jsonrpc(
                            message=message,
                            skill_id=selected_skill.get('id')
                        )

                        # Optionally get task status
                        if result.get('result', {}).get('id'):
                            task_id = result['result']['id']
                            await asyncio.sleep(1)
                            await client.get_task_status(task_id)
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                break

    finally:
        await client.close()

    print("\n" + "="*60)
    print("Demo completed!")
    print("="*60)


async def quick_test():
    """Quick automated test"""

    print("\n" + "="*70)
    print("  A2A Protocol - Quick Test")
    print("="*70)

    base_url = BASE_URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    client = A2AClient(base_url)

    try:
        # Step 1: Discover
        agent_card = await client.discover_agent()

        if not agent_card:
            print("\n[!] Server not available. Start with: python tests/run_a2a_server.py")
            return

        # Step 2: List skills
        skills = await client.list_skills()

        # Step 3: Call chat skill
        result = await client.call_skill_jsonrpc(
            message="Hello, what skills do you have?",
            skill_id="chat"
        )

        print("\n" + "="*60)
        print("Quick Test Complete!")
        print("="*60)

    finally:
        await client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="A2A Protocol Client Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--quick", action="store_true", help="Run quick test")
    args = parser.parse_args()

    # Update global BASE_URL
    BASE_URL = args.url

    if args.quick:
        # Pass url to quick_test
        async def run_quick():
            client = A2AClient(args.url)
            try:
                agent_card = await client.discover_agent()
                if not agent_card:
                    print("\n[!] Server not available. Start with: python tests/run_a2a_server.py")
                    return
                skills = await client.list_skills()
                result = await client.call_skill_jsonrpc(
                    message="Hello, what skills do you have?",
                    skill_id="chat"
                )
                print("\n" + "="*60)
                print("Quick Test Complete!")
                print("="*60)
            finally:
                await client.close()

        asyncio.run(run_quick())
    else:
        asyncio.run(interactive_demo())
