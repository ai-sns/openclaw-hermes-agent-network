"""
Built-in ad-hoc command: A2A Task (JSON-RPC transport).

Handles generic A2A task requests via XEP-0050 ad-hoc commands.
Accepts a JSON-RPC request, forwards to local A2A server or handles locally.
Migrated from xmpp_a2a.py.
"""
import json
import logging
import asyncio
import sys
import os
from typing import Dict, Any, Optional

from runtime.apps.sns.a2a_commands.base import AdhocCommand, CommandContext

logger = logging.getLogger(__name__)

A2A_ADHOC_TASK_NODE = "urn:xmpp:a2a:cmd:tasks"


class A2ATaskCommand(AdhocCommand):
    """Generic A2A task command using JSON-RPC transport over XEP-0050."""

    node = A2A_ADHOC_TASK_NODE
    name = "A2A Task"
    description = "Generic A2A task endpoint accepting JSON-RPC 2.0 requests."
    form_fields = [
        {"var": "jsonrpc_request", "type": "text-multi", "label": "JSON-RPC Request"},
    ]

    _source = "builtin"

    async def handle_execute(self, iq, session, ctx: CommandContext) -> dict:
        """Stage 1: Present form with JSON-RPC request field."""
        try:
            form = ctx.make_form(ftype='form', title='A2A Task')
            form.addField(
                var='jsonrpc_request',
                ftype='text-multi',
                label='JSON-RPC Request',
                value='',
            )
            session['payload'] = form
            session['next'] = None  # Will be wired by registry
            session['has_next'] = True
            session['allow_complete'] = True
            return session
        except Exception as e:
            logger.error("Error in A2A task command handler: %s", e)
            session['notes'] = [('error', f'Internal error: {e}')]
            return session

    async def handle_submit(self, payload, session, ctx: CommandContext) -> dict:
        """
        Stage 2: Process submitted JSON-RPC request.

        Priority 1: Forward to local A2A server (HTTP POST localhost:8789/a2a/)
        Priority 2: Local fallback handler for known methods
        """
        try:
            # Extract the jsonrpc_request from the submitted form
            request_str = ""
            if hasattr(payload, 'get_fields'):
                fields = payload.get_fields()
                field = fields.get('jsonrpc_request')
                if field:
                    val = field.get('value', '')
                    # text-multi may return a list of lines
                    if isinstance(val, list):
                        request_str = '\n'.join(str(v) for v in val)
                    else:
                        request_str = str(val)
            elif hasattr(payload, 'values'):
                request_str = str(payload.values.get('jsonrpc_request', ''))

            request_str = request_str.strip()
            sender_jid = str(session.get('from', ''))
            logger.info(
                "Received A2A task request from %s (%d chars)",
                sender_jid, len(request_str),
            )

            if not request_str:
                response_str = json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Empty request"},
                    "id": None,
                })
            else:
                # Try forwarding to local A2A server first
                response_str = await _forward_to_local_a2a_server(request_str)

                if response_str is None:
                    # A2A server unavailable, try local fallback
                    try:
                        request_dict = json.loads(request_str)
                    except json.JSONDecodeError as e:
                        response_str = json.dumps({
                            "jsonrpc": "2.0",
                            "error": {"code": -32700, "message": f"Parse error: {e}"},
                            "id": None,
                        })
                        request_dict = None

                    if request_dict is not None:
                        response_dict = _local_handle_jsonrpc(request_dict, sender_jid)
                        response_str = json.dumps(response_dict, ensure_ascii=False)

            # Build result form
            result_form = ctx.make_form(ftype='result', title='A2A Task Result')
            result_form.addField(
                var='jsonrpc_response',
                ftype='text-multi',
                label='JSON-RPC Response',
                value=response_str,
            )
            session['payload'] = result_form
            session['next'] = None
            session['has_next'] = False
            return session

        except Exception as e:
            logger.error("Error processing A2A task submission: %s", e)
            session['notes'] = [('error', f'Processing error: {e}')]
            return session


# ── Helper Functions ──────────────────────────────────────────────────────────

async def _forward_to_local_a2a_server(request_str: str) -> Optional[str]:
    """
    Forward a JSON-RPC request to the local A2A server via HTTP POST.

    Uses run_in_executor with sync urllib to avoid event-loop conflicts.
    Returns the response body string, or None if the server is unreachable.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_http_post_a2a, request_str),
            timeout=30,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("_forward_to_local_a2a_server: timeout (30s)")
        return None
    except Exception as e:
        logger.warning("_forward_to_local_a2a_server: failed: %s", e)
        return None


def _sync_http_post_a2a(request_str: str) -> str:
    """Synchronous HTTP POST to local A2A server. Runs in thread executor."""
    import urllib.request
    url = "http://127.0.0.1:8789/a2a/"
    body = request_str.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Host": "localhost",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _local_handle_jsonrpc(request: dict, sender_jid: str = "") -> dict:
    """
    Local fallback handler for JSON-RPC requests when A2A server is unavailable.
    Routes known methods to local handlers.
    """
    rpc_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "tasks/send":
        message = params.get("message", {})
        parts = message.get("parts", [])

        # Detect if message contains structured card data
        their_card = {}
        card_field_names = {"name", "company", "title", "email", "xmpp", "website", "phone"}
        for part in parts:
            if part.get("type") == "data":
                data = part.get("data", {})
                if data and card_field_names & set(data.keys()):
                    their_card = data
                    break
            elif part.get("type") == "text":
                try:
                    parsed = json.loads(part.get("text", "{}"))
                    if isinstance(parsed, dict) and card_field_names & set(parsed.keys()):
                        their_card = parsed
                except json.JSONDecodeError:
                    pass

        # Only do business card exchange if we detected card-like data
        if their_card:
            meta_jid = params.get("metadata", {}).get("sender_jid", "")
            effective_jid = meta_jid or sender_jid
            try:
                from a2aserver.business_card import exchange_business_card
                my_card = exchange_business_card(their_card, sender_jid=effective_jid)
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "id": rpc_id or "task-local",
                        "status": {"state": "completed"},
                        "artifacts": [
                            {"parts": [{"type": "data", "data": my_card}]}
                        ],
                    },
                    "id": rpc_id,
                }
            except Exception as e:
                logger.warning("Local business card exchange failed: %s", e)
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": f"Local handler error: {e}"},
                    "id": rpc_id,
                }

        # Generic tasks/send: return our card as default response (no DB write)
        my_card = _load_my_business_card() or {}
        return {
            "jsonrpc": "2.0",
            "result": {
                "id": rpc_id or "task-local",
                "status": {"state": "completed"},
                "artifacts": [
                    {"parts": [{"type": "data", "data": my_card}]}
                ],
            },
            "id": rpc_id,
        }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "error": {"code": -32601, "message": f"Method not found: {method}"},
        "id": rpc_id,
    }


def _load_my_business_card() -> Dict[str, Any]:
    """Load own business card from A2A server database."""
    try:
        # File is at aisns_backend/runtime/apps/sns/a2a_commands/<this>.py
        # Need 6 dirname() calls to reach project root (parent of aisns_backend)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )))
        )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from a2aserver.db import init_db, get_my_card
        init_db()
        card = get_my_card()
        card.pop("id", None)
        card.pop("updated_at", None)
        return card
    except Exception as e:
        logger.warning("Failed to load business card from A2A server DB: %s", e)
        return {}
