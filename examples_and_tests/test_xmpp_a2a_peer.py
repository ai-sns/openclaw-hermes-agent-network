#!/usr/bin/env python
"""
Comprehensive XMPP A2A test peer.

Mirrors the system backend's ad-hoc command functionality so the two sides
can fully test each other:

  Inbound (peer receives):
    - urn:xmpp:a2a:cmd:tasks            (A2A Task JSON-RPC)
    - urn:xmpp:a2a:cmd:exchange_business_card  (Business Card Exchange)

  Outbound (peer initiates):
    - call_a2a_task        -> target's  urn:xmpp:a2a:cmd:tasks
    - call_exchange_card   -> target's  urn:xmpp:a2a:cmd:exchange_business_card

After connecting, an interactive command prompt lets you trigger outbound
calls while inbound handlers stay active in the background.

Usage:
  python examples_and_tests/test_xmpp_a2a_peer.py --jid chenchen@xabber.de --password YOUR_PW
"""
import argparse
import asyncio
import json
import logging
import signal
import sys
import threading
import uuid
from typing import Any, Dict, Optional

import slixmpp
from slixmpp.xmlstream import ET

# ── Constants (must match system backend) ────────────────────────────────
A2A_ADHOC_TASK_NODE = "urn:xmpp:a2a:cmd:tasks"
A2A_ADHOC_EXCHANGE_NODE = "urn:xmpp:a2a:cmd:exchange_business_card"

A2A_FEATURE_NS = "urn:xmpp:a2a:1"
A2A_BUSINESS_CARD_NS = "urn:xmpp:a2a:business_card:1"
A2A_PEP_NODE = "urn:xmpp:a2a:agentcard"

CARD_FIELDS = ("name", "company", "title", "email", "xmpp", "website", "phone")

LOGGER = logging.getLogger("test_a2a_peer")


# ═══════════════════════════════════════════════════════════════════════════
#  TestA2APeer  –  slixmpp client with full A2A ad-hoc command support
# ═══════════════════════════════════════════════════════════════════════════
class TestA2APeer(slixmpp.ClientXMPP):
    """XMPP peer that exposes AND invokes A2A ad-hoc commands."""

    def __init__(
        self,
        jid: str,
        password: str,
        my_card: Dict[str, str],
        response_text: str,
        result_echo: bool,
    ):
        super().__init__(jid, password)
        self.my_card = my_card
        self.response_text = response_text
        self.result_echo = result_echo
        self._shutdown_event: Optional[asyncio.Event] = None
        self._session_ready = asyncio.Event()

        self.add_event_handler("session_start", self._on_session_start)
        self.add_event_handler("disconnected", self._on_disconnected)
        self.add_event_handler("failed_auth", self._on_failed_auth)

        self.register_plugin("xep_0030")
        self.register_plugin("xep_0004")
        self.register_plugin("xep_0050")
        self.register_plugin("xep_0163")
        self.register_plugin("xep_0060")
        self.register_plugin("xep_0199", {"keepalive": True, "frequency": 30, "timeout": 10})

        # Avoid SCRAM-SHA-*-PLUS channel binding failures on some servers
        # (e.g. xabber.de rejects tls-exporter binding from Python's ssl).
        # Force SCRAM-SHA-1 which works without channel binding.
        self['feature_mechanisms'].use_mech = 'SCRAM-SHA-1'

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def _on_session_start(self, _event: Any) -> None:
        LOGGER.info("Session started for %s", self.boundjid.full)
        self.send_presence()
        await self.get_roster()

        # Register disco features and publish agent card via PEP
        try:
            self._register_disco_features()
        except Exception:
            pass
        try:
            await self._publish_agent_card_pep()
        except Exception:
            pass

        # Register inbound ad-hoc commands
        self["xep_0050"].add_command(
            node=A2A_ADHOC_TASK_NODE,
            name="A2A Task",
            handler=self._handle_a2a_task_command,
        )
        self["xep_0050"].add_command(
            node=A2A_ADHOC_EXCHANGE_NODE,
            name="Exchange Business Card",
            handler=self._handle_exchange_command,
        )
        LOGGER.info("Registered inbound ad-hoc commands: %s, %s",
                     A2A_ADHOC_TASK_NODE, A2A_ADHOC_EXCHANGE_NODE)
        self._session_ready.set()

    def _on_disconnected(self, _event: Any) -> None:
        LOGGER.warning("Disconnected")
        if self._shutdown_event is not None and not self._shutdown_event.is_set():
            self._shutdown_event.set()

    async def _on_failed_auth(self, _event: Any) -> None:
        LOGGER.error("Authentication failed (credentials may be wrong)")
        # Small delay: slixmpp may fire failed_auth per-mechanism before
        # trying fallbacks; only shut down if session never starts.
        await asyncio.sleep(2)
        if not self._session_ready.is_set():
            if self._shutdown_event is not None and not self._shutdown_event.is_set():
                self._shutdown_event.set()

    # =====================================================================
    #  INBOUND: A2A Task  (urn:xmpp:a2a:cmd:tasks)
    # =====================================================================

    async def _handle_a2a_task_command(self, _iq: Any, session: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 1: return form with jsonrpc_request field."""
        form = self["xep_0004"].make_form(ftype="form", title="A2A Task")
        form.addField(var="jsonrpc_request", ftype="text-multi",
                      label="JSON-RPC Request", value="")
        session["payload"] = form
        session["next"] = self._handle_a2a_task_submit
        session["has_next"] = True
        session["allow_complete"] = True
        return session

    async def _handle_a2a_task_submit(self, payload: Any, session: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: parse JSON-RPC request and return response."""
        request_str = _extract_form_value(payload, "jsonrpc_request").strip()
        LOGGER.info("[INBOUND task] from %s (%d chars)", session.get("from", ""), len(request_str))

        response = self._build_jsonrpc_response(request_str)
        response_str = json.dumps(response, ensure_ascii=False)

        result_form = self["xep_0004"].make_form(ftype="result", title="A2A Task Result")
        result_form.addField(var="jsonrpc_response", ftype="text-multi",
                             label="JSON-RPC Response", value=response_str)
        session["payload"] = result_form
        session["next"] = None
        session["has_next"] = False
        LOGGER.info("[INBOUND task] responded (%d chars)", len(response_str))
        return session

    def _build_jsonrpc_response(self, request_str: str) -> Dict[str, Any]:
        if not request_str:
            return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Empty request"}, "id": None}
        try:
            request = json.loads(request_str)
        except json.JSONDecodeError as exc:
            return {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {exc}"}, "id": None}

        rpc_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method not in ("tasks/send", "tasks/get"):
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": rpc_id}

        result: Dict[str, Any] = {
            "id": params.get("id", "test-task") if isinstance(params, dict) else "test-task",
            "status": {"state": "completed"},
            "artifacts": [{"parts": [{"type": "text", "text": self.response_text}]}],
        }
        if self.result_echo:
            result["metadata"] = {"echo_request": request}
        return {"jsonrpc": "2.0", "result": result, "id": rpc_id}

    # =====================================================================
    #  INBOUND: Exchange Business Card  (urn:xmpp:a2a:cmd:exchange_business_card)
    # =====================================================================

    async def _handle_exchange_command(self, _iq: Any, session: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 1: return form requesting the caller's card."""
        form = self["xep_0004"].make_form(ftype="form", title="Exchange Business Card")
        for field_name in CARD_FIELDS:
            form.addField(var=field_name, ftype="text-single",
                          label=field_name.capitalize(), value="")
        session["payload"] = form
        session["next"] = self._handle_exchange_submit
        session["has_next"] = True
        session["allow_complete"] = True
        return session

    async def _handle_exchange_submit(self, payload: Any, session: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: read their card, log it, return our card."""
        their_card: Dict[str, str] = {}
        if hasattr(payload, "get_fields"):
            fields = payload.get_fields()
            for var_name in CARD_FIELDS:
                field = fields.get(var_name)
                if field:
                    their_card[var_name] = field.get("value", "") or ""
        elif hasattr(payload, "get_values"):
            vals = payload.get_values()
            for var_name in CARD_FIELDS:
                their_card[var_name] = str(vals.get(var_name, ""))

        sender_jid = str(session.get("from", ""))
        their_card["sender_jid"] = sender_jid
        LOGGER.info("[INBOUND exchange] Received card from %s: %s", sender_jid, their_card)

        # Return our card
        result_form = self["xep_0004"].make_form(ftype="result", title="Business Card Exchange Result")
        for key in CARD_FIELDS:
            result_form.addField(var=key, ftype="text-single",
                                 label=key.capitalize(), value=self.my_card.get(key, ""))
        session["payload"] = result_form
        session["next"] = None
        session["has_next"] = False
        LOGGER.info("[INBOUND exchange] Returned our card to %s", sender_jid)
        return session

    # =====================================================================
    #  JID Resolution
    # =====================================================================

    def _register_disco_features(self) -> None:
        disco = None
        try:
            disco = self["xep_0030"]
        except Exception:
            disco = None
        if not disco:
            return
        for ns in (A2A_FEATURE_NS, A2A_BUSINESS_CARD_NS, "http://jabber.org/protocol/commands"):
            try:
                disco.add_feature(ns)
            except Exception:
                pass

    def _build_agent_card(self) -> Dict[str, Any]:
        name = self.my_card.get("name", "Test A2A Peer")
        agent_card = {
            "name": name,
            "description": "An agent that exposes A2A ad-hoc commands for testing.",
            "url": "http://localhost:8789/a2a/",
            "version": "1.0.0",
            "protocolVersion": "0.3",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "stateTransitionHistory": False,
            },
            "skills": [
                {
                    "id": "exchange_business_card",
                    "name": "Exchange Business Card",
                    "description": "Exchange business cards between agents.",
                    "tags": ["business_card", "networking"],
                    "examples": ["Exchange business cards", "Send my business card"],
                }
            ],
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
            "provider": {
                "organization": "AI-SNS Platform",
                "url": "https://ai-sns.com",
            },
        }
        return agent_card

    async def _publish_agent_card_pep(self) -> None:
        card = self._build_agent_card()
        try:
            item = ET.Element("{%s}agentcard" % A2A_PEP_NODE)
            item.text = json.dumps(card, ensure_ascii=False)
        except Exception:
            return
        published = False
        try:
            pep = self["xep_0163"]
        except Exception:
            pep = None
        if pep:
            try:
                await pep.publish(item, node=A2A_PEP_NODE, id="current")
                published = True
                LOGGER.info("Published agent card to PEP node %s", A2A_PEP_NODE)
            except Exception:
                pass
        if not published:
            try:
                pubsub = self["xep_0060"]
            except Exception:
                pubsub = None
            if pubsub:
                try:
                    await pubsub.publish(self.boundjid.bare, A2A_PEP_NODE, payload=item, id="current")
                    published = True
                    LOGGER.info("Published agent card to PubSub node %s", A2A_PEP_NODE)
                except Exception:
                    pass
        if not published:
            LOGGER.warning("PEP/0060 not available: failed to publish agent card")

    def _resolve_full_jid(self, bare_jid: str) -> str:
        """
        Resolve a bare JID to a full JID using roster presence.
        Ad-hoc commands must be sent to a full JID (with resource),
        otherwise the server returns item-not-found.
        If already a full JID or no presence found, returns as-is.
        """
        if '/' in bare_jid:
            return bare_jid  # Already a full JID

        try:
            roster_item = self.client_roster[bare_jid]
            resources = roster_item.resources
            if resources:
                # Pick the first available resource
                resource = next(iter(resources))
                full_jid = f"{bare_jid}/{resource}"
                LOGGER.debug("Resolved %s -> %s", bare_jid, full_jid)
                return full_jid
        except Exception as e:
            LOGGER.debug("Could not resolve full JID for %s: %s", bare_jid, e)

        LOGGER.warning("No presence found for %s, using bare JID (may fail)", bare_jid)
        return bare_jid

    # =====================================================================
    #  PEP: Fetch peer agent card (optional helper)
    # =====================================================================

    async def fetch_peer_agent_card_pep(self, peer_jid: str) -> Optional[Dict[str, Any]]:
        bare = str(peer_jid).split('/')[0]
        if not bare or '@' not in bare:
            return None
        try:
            pubsub = self["xep_0060"]
        except Exception:
            pubsub = None
        if not pubsub:
            return None
        try:
            iq = await asyncio.wait_for(pubsub.get_items(bare, A2A_PEP_NODE, max_items=1), timeout=10)
        except Exception:
            return None
        try:
            # Iterate over returned PubSub items and read the payload element text
            for item in iq['pubsub']['items']['substanzas']:
                try:
                    payload_el = None
                    for child in item.xml:
                        if child.text:
                            payload_el = child
                            break
                    if payload_el is not None and payload_el.text:
                        return json.loads(payload_el.text)
                except Exception:
                    continue
            return None
        except Exception:
            return None

    # =====================================================================
    #  OUTBOUND: Call peer A2A Task
    # =====================================================================

    async def call_a2a_task(self, target_jid: str, message_text: str = "Hello from test peer") -> Dict[str, Any]:
        """
        Invoke urn:xmpp:a2a:cmd:tasks on a peer (mirrors system's call_a2a_task).
        Returns dict with 'ok' and 'result' or 'error'.
        """
        rpc_id = str(uuid.uuid4())[:8]
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "tasks/send",
            "params": {
                "id": f"task-{rpc_id}",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message_text}],
                },
            },
        }
        request_str = json.dumps(jsonrpc_request, ensure_ascii=False)
        LOGGER.info("[OUTBOUND task] Calling %s ...", target_jid)

        try:
            # Resolve bare JID to full JID via roster presence
            target_jid = self._resolve_full_jid(target_jid)

            adhoc = self["xep_0050"]
            # Step 1: Execute -> get form
            resp = await asyncio.wait_for(
                adhoc.send_command(target_jid, A2A_ADHOC_TASK_NODE, action="execute"),
                timeout=30,
            )
            session_id = resp["command"]["sessionid"]
            form = resp["command"]["form"]

            # Step 2: Fill jsonrpc_request and submit
            try:
                form["type"] = "submit"
            except Exception:
                pass
            if hasattr(form, "set_values"):
                form.set_values({"jsonrpc_request": request_str})
            else:
                fields = form.get_fields() if hasattr(form, "get_fields") else {}
                if "jsonrpc_request" in fields:
                    fields["jsonrpc_request"]["value"] = request_str

            # Step 3: Complete
            result = await asyncio.wait_for(
                adhoc.send_command(
                    target_jid, A2A_ADHOC_TASK_NODE,
                    action="complete", sessionid=session_id, payload=form,
                ),
                timeout=60,
            )

            # Step 4: Parse jsonrpc_response
            result_form = result["command"].get("form")
            if not result_form:
                return {"ok": False, "error": "No response form received"}
            response_str = _extract_form_value(result_form, "jsonrpc_response").strip()
            if not response_str:
                return {"ok": False, "error": "Empty jsonrpc_response from peer"}

            response_dict = json.loads(response_str)
            if "error" in response_dict and response_dict["error"]:
                err = response_dict["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return {"ok": False, "error": f"JSON-RPC error: {msg}", "raw": response_dict}

            LOGGER.info("[OUTBOUND task] Success from %s", target_jid)
            return {"ok": True, "result": response_dict.get("result", {})}

        except asyncio.TimeoutError:
            LOGGER.warning("[OUTBOUND task] Timeout calling %s", target_jid)
            return {"ok": False, "error": "timeout"}
        except Exception as e:
            LOGGER.error("[OUTBOUND task] Error calling %s: %s", target_jid, e)
            return {"ok": False, "error": str(e)}

    # =====================================================================
    #  OUTBOUND: Call peer Exchange Business Card
    # =====================================================================

    async def call_exchange_card(self, target_jid: str) -> Dict[str, Any]:
        """
        Invoke urn:xmpp:a2a:cmd:exchange_business_card on a peer
        (mirrors system's call_exchange_business_card).
        Returns dict with 'ok' and 'peer_card' or 'error'.
        """
        LOGGER.info("[OUTBOUND exchange] Calling %s ...", target_jid)
        try:
            # Resolve bare JID to full JID via roster presence
            target_jid = self._resolve_full_jid(target_jid)

            adhoc = self["xep_0050"]
            # Step 1: Execute -> get form with card fields
            resp = await asyncio.wait_for(
                adhoc.send_command(target_jid, A2A_ADHOC_EXCHANGE_NODE, action="execute"),
                timeout=30,
            )
            session_id = resp["command"]["sessionid"]
            form = resp["command"]["form"]

            # Step 2: Fill our card values
            try:
                form["type"] = "submit"
            except Exception:
                pass
            card_values = {key: (self.my_card.get(key, "") or "") for key in CARD_FIELDS}
            if hasattr(form, "set_values"):
                try:
                    form.set_values(card_values)
                except Exception:
                    fields = form.get_fields() if hasattr(form, "get_fields") else {}
                    for k, v in card_values.items():
                        if k in fields:
                            fields[k]["value"] = v
            else:
                fields = form.get_fields() if hasattr(form, "get_fields") else {}
                for k, v in card_values.items():
                    if k in fields:
                        fields[k]["value"] = v

            # Step 3: Complete
            result = await asyncio.wait_for(
                adhoc.send_command(
                    target_jid, A2A_ADHOC_EXCHANGE_NODE,
                    action="complete", sessionid=session_id, payload=form,
                ),
                timeout=30,
            )

            # Step 4: Parse peer card from result form
            result_form = result["command"].get("form")
            if not result_form:
                return {"ok": False, "error": "No response form received"}

            peer_card: Dict[str, str] = {}
            if hasattr(result_form, "get_fields"):
                fields = result_form.get_fields()
                for key in CARD_FIELDS:
                    field = fields.get(key)
                    if field:
                        peer_card[key] = field.get("value", "") or ""
            elif hasattr(result_form, "get_values"):
                vals = result_form.get_values()
                for key in CARD_FIELDS:
                    peer_card[key] = str(vals.get(key, ""))

            LOGGER.info("[OUTBOUND exchange] Got peer card from %s: %s", target_jid, peer_card)
            return {"ok": True, "peer_card": peer_card}

        except asyncio.TimeoutError:
            LOGGER.warning("[OUTBOUND exchange] Timeout calling %s", target_jid)
            return {"ok": False, "error": "timeout"}
        except Exception as e:
            LOGGER.error("[OUTBOUND exchange] Error calling %s: %s", target_jid, e)
            return {"ok": False, "error": str(e)}

    # ── Run loop ─────────────────────────────────────────────────────────

    async def run_until_stopped(self) -> None:
        self._shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signame in ("SIGINT", "SIGTERM"):
            sig = getattr(signal, signame, None)
            if sig is None:
                continue
            try:
                loop.add_signal_handler(sig, self._shutdown_event.set)
            except (NotImplementedError, RuntimeError):
                pass

        LOGGER.info("Connecting as %s ...", self.boundjid.bare)
        self.connect()
        await self._shutdown_event.wait()
        LOGGER.info("Disconnecting")
        self.disconnect()


# ═══════════════════════════════════════════════════════════════════════════
#  Helper: extract a single field value from a slixmpp Form payload
# ═══════════════════════════════════════════════════════════════════════════
def _extract_form_value(payload: Any, field_name: str) -> str:
    """Extract a field value from a slixmpp Form / stanza payload."""
    if hasattr(payload, "get_values"):
        try:
            value = payload.get_values().get(field_name, "")
            if isinstance(value, list):
                return "\n".join(str(item) for item in value)
            return str(value)
        except Exception:
            pass
    if hasattr(payload, "get_fields"):
        try:
            field = payload.get_fields().get(field_name)
            if field:
                value = field.get("value", "")
                if isinstance(value, list):
                    return "\n".join(str(item) for item in value)
                return str(value)
        except Exception:
            pass
    return ""


# ═══════════════════════════════════════════════════════════════════════════
#  Interactive command loop (runs in a separate thread on Windows)
# ═══════════════════════════════════════════════════════════════════════════
HELP_TEXT = """
Available commands (type and press Enter):
  task <target_jid> [message]    Call peer's A2A Task (tasks/send)
  exchange <target_jid>          Call peer's Exchange Business Card
  agentcard <target_jid>         Fetch peer Agent Card from PEP
  card                           Show our own business card
  help                           Show this help
  quit / exit                    Disconnect and quit
""".strip()


def _start_input_thread(peer: TestA2APeer, loop: asyncio.AbstractEventLoop) -> None:
    """Read stdin in a daemon thread and schedule async calls on the event loop."""

    def _input_loop() -> None:
        print(f"\n{'=' * 60}")
        print("  Test A2A Peer - Interactive Console")
        print(f"  JID: {peer.boundjid.bare}")
        print(f"{'=' * 60}")
        print(HELP_TEXT)
        print()

        while True:
            try:
                raw = input("a2a> ").strip()
            except (EOFError, KeyboardInterrupt):
                asyncio.run_coroutine_threadsafe(
                    _async_shutdown(peer), loop
                )
                break
            if not raw:
                continue

            parts = raw.split(None, 2)
            cmd = parts[0].lower()

            if cmd in ("quit", "exit"):
                asyncio.run_coroutine_threadsafe(
                    _async_shutdown(peer), loop
                )
                break
            elif cmd == "help":
                print(HELP_TEXT)
            elif cmd == "card":
                print(json.dumps(peer.my_card, indent=2, ensure_ascii=False))
            elif cmd == "task":
                if len(parts) < 2:
                    print("Usage: task <target_jid> [message]")
                    continue
                target = parts[1]
                msg = parts[2] if len(parts) > 2 else "Hello from test peer"
                future = asyncio.run_coroutine_threadsafe(
                    peer.call_a2a_task(target, msg), loop
                )
                try:
                    result = future.result(timeout=120)
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except Exception as exc:
                    print(f"Error: {exc}")
            elif cmd == "exchange":
                if len(parts) < 2:
                    print("Usage: exchange <target_jid>")
                    continue
                target = parts[1]
                future = asyncio.run_coroutine_threadsafe(
                    peer.call_exchange_card(target), loop
                )
                try:
                    # Allow buffer above internal 30+30s timeouts
                    result = future.result(timeout=90)
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except Exception as exc:
                    print(f"Error: {exc}")
            elif cmd == "agentcard":
                if len(parts) < 2:
                    print("Usage: agentcard <target_jid>")
                    continue
                target = parts[1]
                future = asyncio.run_coroutine_threadsafe(
                    peer.fetch_peer_agent_card_pep(target), loop
                )
                try:
                    card = future.result(timeout=30)
                    if card:
                        print(json.dumps({"ok": True, "agent_card": card}, indent=2, ensure_ascii=False))
                    else:
                        print(json.dumps({"ok": False, "error": "No agent card found or PEP not available"}, indent=2, ensure_ascii=False))
                except Exception as exc:
                    print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
            else:
                print(f"Unknown command: {cmd}")
                print(HELP_TEXT)

    thread = threading.Thread(target=_input_loop, daemon=True)
    thread.start()


async def _async_shutdown(peer: TestA2APeer) -> None:
    if peer._shutdown_event and not peer._shutdown_event.is_set():
        peer._shutdown_event.set()


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════
DEFAULT_CARD: Dict[str, str] = {
    "name": "ChenChen (Test Peer)",
    "company": "Test Corp",
    "title": "QA Tester",
    "email": "chenchen@xabber.de",
    "xmpp": "chenchen@xabber.de",
    "website": "",
    "phone": "",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Full-featured XMPP A2A ad-hoc command test peer "
                    "for bidirectional testing with the AI-SNS backend.",
    )
    parser.add_argument(
        "--jid", default="chenchen@xabber.de",
        help="XMPP JID for the test peer (default: chenchen@xabber.de)",
    )
    parser.add_argument("--password", required=True, help="XMPP password")
    parser.add_argument(
        "--response-text",
        default="pong from test XMPP A2A peer",
        help="Text returned in the JSON-RPC result artifact (inbound tasks)",
    )
    parser.add_argument(
        "--card-name", default=DEFAULT_CARD["name"],
        help="Name on our business card",
    )
    parser.add_argument(
        "--card-email", default=DEFAULT_CARD["email"],
        help="Email on our business card",
    )
    parser.add_argument(
        "--no-echo", action="store_true",
        help="Do not echo the received JSON-RPC request in result.metadata",
    )
    parser.add_argument(
        "--no-interactive", action="store_true",
        help="Disable the interactive command console (server-only mode)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable verbose slixmpp debug logs")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    my_card = dict(DEFAULT_CARD)
    my_card["name"] = args.card_name
    my_card["email"] = args.card_email
    my_card["xmpp"] = args.jid

    peer = TestA2APeer(
        jid=args.jid,
        password=args.password,
        my_card=my_card,
        response_text=args.response_text,
        result_echo=not args.no_echo,
    )

    # Start the interactive console thread (unless disabled)
    if not args.no_interactive:
        loop = asyncio.get_running_loop()
        # Wait for XMPP session to be ready before starting the console
        async def _start_console_after_ready() -> None:
            await peer._session_ready.wait()
            _start_input_thread(peer, loop)
        asyncio.ensure_future(_start_console_after_ready())

    await peer.run_until_stopped()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
