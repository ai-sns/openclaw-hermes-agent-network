"""
XMPP A2A Integration Module

Provides A2A (Agent-to-Agent) capabilities over XMPP:
- Fetches agent card from inline config or agent_cfg.memo.agent_card_url
- Publishes agent card via XEP-0163 PEP
- Advertises A2A capabilities via XEP-0030 Service Discovery
- Dynamically registers ad-hoc commands from plugin registry + DB config
- Discovers and invokes peer A2A capabilities

Data flow:
  aisns_cfg.memo.a2a_config.agent_card (inline) OR
  aisns_cfg.agent_id -> agent_cfg -> memo JSON -> agent_card_url
  -> publish via XMPP Disco + PEP

Ad-hoc commands are loaded from:
  1. Built-in plugins (a2a_commands/*.py)
  2. User plugins (aisns_backend/scripts/a2a_commands/*.py)
  3. Config-type commands (aisns_cfg.memo.a2a_config.adhoc_commands)
"""

import json
import logging
import asyncio
import uuid
from typing import Optional, Dict, Any, List

from runtime.apps.sns.a2a_commands import discover_commands, build_config_commands
from runtime.apps.sns.a2a_commands.base import AdhocCommand, CommandContext

logger = logging.getLogger(__name__)

# A2A namespace URNs for XMPP disco features
A2A_FEATURE_NS = "urn:xmpp:a2a:1"
A2A_BUSINESS_CARD_NS = "urn:xmpp:a2a:business_card:1"
A2A_PEP_NODE = "urn:xmpp:a2a:agentcard"
# Command node URIs are defined per-plugin; re-exported here for backward compat
from runtime.apps.sns.a2a_commands.exchange_business_card import (
    A2A_ADHOC_EXCHANGE_NODE,
)
from runtime.apps.sns.a2a_commands.a2a_task import A2A_ADHOC_TASK_NODE


class XMPPA2AManager:
    """Manages A2A capabilities over XMPP."""

    def __init__(self, xmpp_client):
        """
        Args:
            xmpp_client: The slixmpp.ClientXMPP instance (XMPPClient)
        """
        self.client = xmpp_client
        self._agent_card: Optional[Dict[str, Any]] = None
        self._my_business_card: Optional[Dict[str, Any]] = None
        # Track registered items for reliable server-side introspection
        self._registered_features: list = []
        self._registered_commands: list = []
        # Plugin registry: node -> AdhocCommand instance
        self._command_instances: Dict[str, AdhocCommand] = {}
        self._command_context: Optional[CommandContext] = None

    # ── Agent Card Fetching ────────────────────────────────────────────────

    def _get_agent_card_url(self) -> Optional[str]:
        """
        Resolve agent_card_url from aisns_cfg -> agent_cfg -> memo JSON.
        Returns the URL string or None.
        """
        try:
            from db.database import get_db_sync
            from db.models.aisns import AISnsCfg
            from db.models.agent import AgentCfg

            db = get_db_sync()
            config = db.query(AISnsCfg).filter(
                AISnsCfg.is_delete == False
            ).first()

            if not config or not getattr(config, 'agent_id', None):
                db.close()
                return None

            agent = db.query(AgentCfg).filter_by(id=config.agent_id).first()
            db.close()

            if not agent or not agent.memo:
                return None

            extra_data = json.loads(agent.memo)
            url = extra_data.get('agent_card_url', '').strip()
            return url if url else None

        except Exception as e:
            logger.error("Failed to resolve agent_card_url: %s", e)
            return None

    @staticmethod
    def _sync_http_get(url: str) -> Dict[str, Any]:
        """Synchronous HTTP GET that runs in a thread executor.

        Uses urllib to avoid event-loop interaction issues between
        httpx.AsyncClient and slixmpp's asyncio loop on Windows.
        Also forces 127.0.0.1 to avoid IPv6 localhost resolution issues.
        """
        import urllib.request
        # Replace localhost with 127.0.0.1 to avoid IPv6 resolution issues on Windows
        fetch_url = url.replace("://localhost", "://127.0.0.1")
        req = urllib.request.Request(fetch_url, headers={"Host": "localhost"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    async def fetch_agent_card(self) -> Optional[Dict[str, Any]]:
        """Fetch the agent card from the configured URL."""
        url = self._get_agent_card_url()
        if not url:
            logger.info("No agent_card_url configured, skipping agent card fetch")
            return None

        last_error: Optional[Exception] = None
        loop = asyncio.get_event_loop()

        # Retry to avoid race: XMPP session can start before A2A server is ready.
        for attempt in range(1, 6):
            try:
                # Run synchronous HTTP in thread executor to avoid
                # asyncio event-loop conflicts with slixmpp on Windows
                card = await loop.run_in_executor(
                    None, self._sync_http_get, url
                )
                self._agent_card = card
                logger.info(
                    "Fetched agent card from %s: name=%s",
                    url,
                    card.get("name", "unknown"),
                )
                return card
            except Exception as e:
                last_error = e
                logger.warning(
                    "Failed to fetch agent card (attempt=%d/5) url=%s error_type=%s error=%r",
                    attempt,
                    url,
                    type(e).__name__,
                    e,
                )
                try:
                    await asyncio.sleep(min(attempt, 3))
                except Exception:
                    pass

        logger.error(
            "Failed to fetch agent card from %s after retries: %s",
            url,
            repr(last_error) if last_error else "unknown error",
        )
        return None

    def _load_my_business_card(self) -> Dict[str, Any]:
        """Load own business card from A2A server database."""
        try:
            import sys
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            from a2aserver.db import init_db, get_my_card
            init_db()
            card = get_my_card()
            card.pop("id", None)
            card.pop("updated_at", None)
            self._my_business_card = card
            return card
        except Exception as e:
            logger.warning("Failed to load business card from A2A server DB: %s", e)
            return {}

    # ── XEP-0030 Service Discovery ─────────────────────────────────────────

    def register_disco_features(self):
        """Register A2A features in Service Discovery."""
        try:
            try:
                disco = self.client['xep_0030']
            except Exception:
                disco = None
            if not disco:
                logger.warning("xep_0030 plugin not available")
                return

            # Add A2A feature namespaces
            added = [
                A2A_FEATURE_NS,
                A2A_BUSINESS_CARD_NS,
                "http://jabber.org/protocol/commands",
            ]
            for ns in added:
                try:
                    disco.add_feature(ns)
                    if ns not in self._registered_features:
                        self._registered_features.append(ns)
                except Exception as e:
                    logger.warning("Failed to add disco feature %s: %s", ns, e)

            logger.info("Registered A2A disco features: %s", self._registered_features)
        except Exception as e:
            logger.error("Failed to register disco features: %s", e)

    # ── XEP-0163 PEP Publishing ───────────────────────────────────────────

    async def publish_agent_card_pep(self):
        """Publish the agent card to a PEP node so contacts can discover it."""
        if not self._agent_card:
            logger.info("No agent card to publish via PEP")
            return

        try:
            from slixmpp.xmlstream import ET

            # Build an XML payload containing the agent card as JSON
            item = ET.Element("{%s}agentcard" % A2A_PEP_NODE)
            item.text = json.dumps(self._agent_card, ensure_ascii=False)

            # Publish via PEP (xep_0163 is a convenience wrapper around xep_0060)
            published = False
            try:
                pep = self.client['xep_0163']
                if pep:
                    await pep.publish(
                        item,
                        node=A2A_PEP_NODE,
                        id="current",
                    )
                    logger.info("Published agent card to PEP node %s", A2A_PEP_NODE)
                    published = True
            except Exception:
                pass

            if not published:
                try:
                    pubsub = self.client['xep_0060']
                    if pubsub:
                        await pubsub.publish(
                            self.client.boundjid.bare,
                            A2A_PEP_NODE,
                            payload=item,
                            id="current",
                        )
                        logger.info("Published agent card to PubSub node %s", A2A_PEP_NODE)
                        published = True
                except Exception:
                    pass

            if not published:
                logger.warning("Neither xep_0163 nor xep_0060 available for PEP publishing")
        except Exception as e:
            logger.error("Failed to publish agent card via PEP: %s", e)

    # ── A2A Config Loading ─────────────────────────────────────────────────

    def _load_a2a_config(self) -> Dict[str, Any]:
        """
        Load a2a_config from aisns_cfg.memo JSON.

        Returns the a2a_config dict or empty dict if not configured.
        """
        try:
            from db.database import get_db_sync
            from db.models.aisns import AISnsCfg

            db = get_db_sync()
            config = db.query(AISnsCfg).filter(
                AISnsCfg.is_delete == False
            ).first()
            db.close()

            if not config:
                return {}

            memo_str = getattr(config, 'memo', '') or ''
            if not memo_str.strip():
                return {}

            memo = json.loads(memo_str)
            return memo.get('a2a_config', {}) if isinstance(memo, dict) else {}

        except Exception as e:
            logger.warning("Failed to load a2a_config from memo: %s", e)
            return {}

    # ── XEP-0050 Ad-hoc Commands ──────────────────────────────────────────

    def register_adhoc_commands(self):
        """
        Register ad-hoc command handlers dynamically from plugin registry + DB config.

        Steps:
        1. Discover builtin + user plugin commands via a2a_commands package
        2. Load config-type commands from aisns_cfg.memo.a2a_config
        3. Determine enabled/disabled state from DB config
        4. Register only enabled commands with xep_0050
        """
        try:
            adhoc = self.client['xep_0050']
            if not adhoc:
                logger.warning("xep_0050 plugin not available, cannot register commands")
                return
        except Exception as e:
            logger.warning("xep_0050 plugin not available: %s", e)
            return

        # Build command context for handler injection
        self._command_context = CommandContext(
            xmpp_client=self.client,
            a2a_manager=self,
            logger=logger,
        )

        # 1. Discover builtin + plugin commands
        all_commands: List[AdhocCommand] = []
        try:
            all_commands = discover_commands()
        except Exception as e:
            logger.error("Failed to discover commands: %s", e)
            return

        # 2. Load config from DB
        a2a_config = self._load_a2a_config()
        adhoc_config_list = a2a_config.get('adhoc_commands', [])

        # 3. Build config-type TemplateCommand instances
        try:
            config_commands = build_config_commands(adhoc_config_list)
            all_commands.extend(config_commands)
        except Exception as e:
            logger.warning("Failed to build config commands: %s", e)

        # 4. Determine enabled state: build a lookup from DB config
        # If no config exists, all commands are enabled by default
        enabled_lookup: Dict[str, bool] = {}
        for entry in adhoc_config_list:
            if isinstance(entry, dict) and 'node' in entry:
                enabled_lookup[entry['node']] = entry.get('enabled', True)

        # 5. Register enabled commands
        self._command_instances.clear()
        self._registered_commands.clear()

        seen_nodes = set()
        for cmd in all_commands:
            if not getattr(cmd, 'node', ''):
                continue
            if cmd.node in seen_nodes:
                logger.warning(
                    "Skipping duplicate ad-hoc command node: %s (%s) [%s]",
                    cmd.node, cmd.name, cmd._source,
                )
                continue
            seen_nodes.add(cmd.node)

            # Check enabled state (default: enabled if not in lookup)
            is_enabled = enabled_lookup.get(cmd.node, True)
            if not is_enabled:
                logger.info("Skipping disabled command: %s (%s)", cmd.node, cmd.name)
                continue

            try:
                # Create handler closures that inject ctx
                execute_handler = self._make_execute_handler(cmd)
                adhoc.add_command(
                    node=cmd.node,
                    name=cmd.name,
                    handler=execute_handler,
                )
                self._command_instances[cmd.node] = cmd
                self._registered_commands.append(cmd.node)
                logger.info(
                    "Registered ad-hoc command: %s (%s) [%s]",
                    cmd.node, cmd.name, cmd._source,
                )
            except Exception as e:
                logger.error("Failed to register command %s: %s", cmd.node, e)

        logger.info(
            "Ad-hoc command registration complete: %d commands registered",
            len(self._registered_commands),
        )

    def _make_execute_handler(self, cmd: AdhocCommand):
        """
        Create an execute handler closure for a command plugin.

        The closure calls cmd.handle_execute and wires the submit handler.
        """
        ctx = self._command_context

        async def _execute_handler(iq, session):
            try:
                session = await cmd.handle_execute(iq, session, ctx)
                # Wire the submit handler as 'next' callback
                session['next'] = self._make_submit_handler(cmd)
                return session
            except Exception as e:
                logger.error("Error in execute handler for %s: %s", cmd.node, e)
                session['notes'] = [('error', f'Internal error: {e}')]
                return session

        return _execute_handler

    def _make_submit_handler(self, cmd: AdhocCommand):
        """
        Create a submit handler closure for a command plugin.

        The closure calls cmd.handle_submit with ctx.
        """
        ctx = self._command_context

        async def _submit_handler(payload, session):
            try:
                return await cmd.handle_submit(payload, session, ctx)
            except Exception as e:
                logger.error("Error in submit handler for %s: %s", cmd.node, e)
                session['notes'] = [('error', f'Processing error: {e}')]
                return session

        return _submit_handler

    def get_registered_command_metadata(self) -> List[Dict[str, Any]]:
        """Return metadata for all registered commands (for API/debug)."""
        result = []
        for node, cmd in self._command_instances.items():
            result.append(cmd.get_metadata())
        return result

    # ── Outbound: Discover & Call Other Agents ─────────────────────────────

    async def discover_peer_a2a(self, target_jid: str) -> bool:
        """
        Check if a peer JID supports A2A via disco#info.

        Args:
            target_jid: The XMPP JID to check

        Returns:
            True if the peer advertises A2A features
        """
        try:
            info = await self.client['xep_0030'].get_info(jid=target_jid)
            features = info['disco_info']['features']
            has_a2a = A2A_FEATURE_NS in features or A2A_BUSINESS_CARD_NS in features
            logger.info("Peer %s A2A support: %s (features=%s)",
                       target_jid, has_a2a, list(features))
            return has_a2a
        except Exception as e:
            logger.error("Failed to discover A2A features for %s: %s", target_jid, e)
            return False

    # ── Inbound: Read Peer Agent Card via PEP ────────────────────────────

    async def fetch_peer_agent_card_pep(self, peer_jid: str) -> Optional[Dict[str, Any]]:
        """
        Read a peer's agent card from their PEP node (urn:xmpp:a2a:agentcard).

        Uses xep_0060.get_items to fetch the published agent card item from
        the peer's PEP node. Returns the parsed agent card dict, or None on
        failure.

        Args:
            peer_jid: The bare XMPP JID of the peer (e.g. user@domain)

        Returns:
            The agent card dict, or None if unavailable
        """
        bare_jid = str(peer_jid).split('/')[0]
        if not bare_jid or '@' not in bare_jid:
            logger.warning("[XMPP-A2A] fetch_agent_card_pep: invalid peer_jid=%s", peer_jid)
            return None

        logger.info("[XMPP-A2A] fetch_agent_card_pep: requesting PEP node=%s from %s", A2A_PEP_NODE, bare_jid)

        try:
            pubsub = self.client['xep_0060']
        except Exception:
            pubsub = None

        if pubsub is None:
            logger.warning("[XMPP-A2A] fetch_agent_card_pep: xep_0060 not available")
            return None

        try:
            iq = await asyncio.wait_for(
                pubsub.get_items(bare_jid, A2A_PEP_NODE, max_items=1),
                timeout=10,
            )

            # Parse items from the PubSub response
            for item in iq['pubsub']['items']['substanzas']:
                try:
                    # The agent card is stored as JSON text inside the XML element
                    payload_el = None
                    for child in item.xml:
                        if child.text:
                            payload_el = child
                            break

                    if payload_el is not None and payload_el.text:
                        card = json.loads(payload_el.text)
                        logger.info(
                            "[XMPP-A2A] fetch_agent_card_pep: SUCCESS from %s — name=%s",
                            bare_jid,
                            card.get("name", "unknown"),
                        )
                        return card
                except Exception as parse_err:
                    logger.warning(
                        "Failed to parse PEP agent card item from %s: %s",
                        bare_jid,
                        parse_err,
                    )

            logger.info("[XMPP-A2A] fetch_agent_card_pep: no items found in PEP node for %s", bare_jid)
            return None

        except asyncio.TimeoutError:
            logger.warning("[XMPP-A2A] fetch_agent_card_pep: TIMEOUT reading PEP from %s", bare_jid)
            return None
        except Exception as e:
            logger.warning("[XMPP-A2A] fetch_agent_card_pep: FAILED for %s: %s", bare_jid, e)
            return None


    # ── Outbound: Generic Ad-hoc Command Invocation ─────────────────────────

    async def call_adhoc_command(
        self,
        peer_jid: str,
        command_node: str,
        form_data: Optional[Dict[str, Any]] = None,
        inspect_only: bool = False,
        timeout_per_resource: float = 20.0,
    ) -> dict:
        """
        Invoke any XEP-0050 ad-hoc command on a peer — fully generic.

        Flow:
        1. Resolve full JID.
        2. Send execute → receive form template.
        3. If inspect_only, return form metadata and cancel session.
        4. Fill matching fields from form_data.
        5. Submit with action=complete.
        6. Parse result form into a generic dict.

        Args:
            peer_jid: Target XMPP JID (bare or full)
            command_node: Ad-hoc command node URI
            form_data: Key-value pairs to fill into the form (keys not in form are ignored)
            inspect_only: If True, return form metadata without submitting

        Returns:
            {"ok": True, "result": {field_var: value, ...}} on success
            {"ok": True, "form": {...}, "session_id": ...} on inspect_only
            {"ok": False, "error": "...", "detail": "..."} on failure
        """
        try:
            from slixmpp.exceptions import IqError, IqTimeout
        except Exception:
            IqError = IqTimeout = None  # type: ignore

        # Build candidate list: all known resources, then bare JID as final fallback
        candidates = self._get_all_resources(peer_jid)
        if not candidates:
            candidates = [peer_jid]
        elif peer_jid not in candidates and '/' not in peer_jid:
            candidates.append(peer_jid)  # bare JID as last resort

        last_error: Optional[dict] = None

        for idx, resolved_jid in enumerate(candidates):
            logger.info(
                "[XMPP-A2A] call_adhoc: peer=%s resolved=%s node=%s inspect_only=%s (attempt %d/%d)",
                peer_jid, resolved_jid, command_node, inspect_only, idx + 1, len(candidates),
            )
            try:
                result = await asyncio.wait_for(
                    self._call_adhoc_impl(resolved_jid, command_node, form_data, inspect_only),
                    timeout=timeout_per_resource,
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(
                    "[XMPP-A2A] call_adhoc: TIMEOUT (%.0fs) peer=%s node=%s (attempt %d/%d)",
                    timeout_per_resource, resolved_jid, command_node, idx + 1, len(candidates),
                )
                last_error = {"ok": False, "error": "timeout", "detail": f"XMPP ad-hoc command timed out ({timeout_per_resource:.0f}s)"}
                # Timeout is retryable — resource may not support commands
                if idx < len(candidates) - 1:
                    logger.info(
                        "[XMPP-A2A] call_adhoc: resource %s timed out, trying next resource",
                        resolved_jid,
                    )
                    continue
                break
            except Exception as e:
                if IqTimeout is not None and isinstance(e, IqTimeout):
                    logger.warning("[XMPP-A2A] call_adhoc: IQ timeout peer=%s node=%s", resolved_jid, command_node)
                    last_error = {"ok": False, "error": "peer_unreachable", "detail": "IQ timeout (peer offline or unresponsive)"}
                    # IQ timeout is retryable — resource may not support commands
                    if idx < len(candidates) - 1:
                        logger.info(
                            "[XMPP-A2A] call_adhoc: resource %s IQ timeout, trying next resource",
                            resolved_jid,
                        )
                        continue
                    break
                if IqError is not None and isinstance(e, IqError):
                    cond = "unknown"
                    try:
                        cond = e.iq['error']['condition'] or "unknown"
                    except Exception:
                        pass
                    logger.warning(
                        "[XMPP-A2A] call_adhoc: IqError peer=%s node=%s cond=%s",
                        resolved_jid, command_node, cond,
                    )
                    last_error = {"ok": False, "error": cond, "detail": str(e)}
                    # Retry on service-unavailable (resource might not support commands)
                    if cond == "service-unavailable" and idx < len(candidates) - 1:
                        logger.info(
                            "[XMPP-A2A] call_adhoc: resource %s does not support commands, trying next resource",
                            resolved_jid,
                        )
                        continue
                    break
                logger.error("[XMPP-A2A] call_adhoc: FAILED peer=%s node=%s: %s", resolved_jid, command_node, e)
                last_error = {"ok": False, "error": "unexpected", "detail": str(e)}
                break

        return last_error or {"ok": False, "error": "no_resources", "detail": "No reachable resources found"}

    async def _call_adhoc_impl(
        self,
        target_jid: str,
        command_node: str,
        form_data: Optional[Dict[str, Any]],
        inspect_only: bool,
    ) -> dict:
        """Internal implementation of the generic ad-hoc command call."""
        adhoc = self.client['xep_0050']

        # Step 1: Execute command → get form
        logger.info("[XMPP-A2A] call_adhoc: executing node=%s on %s", command_node, target_jid)
        resp = await adhoc.send_command(
            target_jid,
            command_node,
            action='execute',
        )

        session_id = resp['command']['sessionid']
        form = resp['command'].get('form')

        # Step 2: If inspect_only, return form metadata and cancel
        if inspect_only:
            form_meta = self._extract_form_fields(form) if form else {"title": "", "fields": []}
            # Cancel the session to avoid dangling state on peer
            try:
                await adhoc.send_command(
                    target_jid,
                    command_node,
                    action='cancel',
                    sessionid=session_id,
                )
            except Exception:
                pass
            logger.info(
                "[XMPP-A2A] inspect_adhoc: peer=%s node=%s fields=%d (cancelled session=%s)",
                target_jid, command_node, len(form_meta.get("fields", [])), session_id,
            )
            return {"ok": True, "command_node": command_node, "session_id": session_id, "form": form_meta}

        # Step 3: Fill form with form_data
        if form is not None:
            self._set_form_values(form, form_data or {})

        # Step 4: Submit with complete
        logger.info(
            "[XMPP-A2A] call_adhoc: submitting node=%s peer=%s session=%s form_keys=%s",
            command_node, target_jid, session_id, list((form_data or {}).keys()),
        )
        result = await adhoc.send_command(
            target_jid,
            command_node,
            action='complete',
            sessionid=session_id,
            payload=form,
        )

        # Step 5: Parse the result
        result_form = result['command'].get('form')
        if not result_form:
            notes = result['command'].get('notes', [])
            if notes:
                error_msg = '; '.join(str(n) for n in notes)
                logger.warning("[XMPP-A2A] call_adhoc: notes error peer=%s: %s", target_jid, error_msg)
                return {"ok": False, "error": f"Ad-hoc command error: {error_msg}"}
            return {"ok": False, "error": "No response form received"}

        result_dict = self._form_to_dict(result_form)
        logger.info("[XMPP-A2A] call_adhoc: SUCCESS peer=%s node=%s result_keys=%s", target_jid, command_node, list(result_dict.keys()))
        return {"ok": True, "result": result_dict}

    # ── Form Helpers (generic) ─────────────────────────────────────────────

    @staticmethod
    def _extract_form_fields(form) -> dict:
        """Extract form metadata for inspect-only mode."""
        title = ""
        fields_list = []
        try:
            title = form.get('title', '') or ''
        except Exception:
            pass
        try:
            if hasattr(form, 'get_fields'):
                for var, field in form.get_fields().items():
                    fields_list.append({
                        "var": var,
                        "type": field.get('type', 'text-single') or 'text-single',
                        "label": field.get('label', '') or '',
                        "required": bool(field.get('required', False)),
                        "value": field.get('value', '') or '',
                    })
        except Exception:
            pass
        return {"title": title, "fields": fields_list}

    @staticmethod
    def _set_form_values(form, form_data: Dict[str, Any]) -> None:
        """Fill form fields from form_data dict. Ignores keys not in the form."""
        try:
            form['type'] = 'submit'
        except Exception:
            pass

        if not form_data:
            return

        fields = form.get_fields() if hasattr(form, 'get_fields') else {}
        matching_values = {
            key: val
            for key, val in form_data.items()
            if key in fields
        }

        if not matching_values:
            return

        if hasattr(form, 'set_values'):
            try:
                form.set_values(matching_values)
                return
            except Exception as e:
                logger.warning("[XMPP-A2A] set_values failed, falling back to per-field: %s", e)

        # Fallback: directly mutate field values
        if fields:
            for key, val in form_data.items():
                if key in fields:
                    fields[key]['value'] = val

    @staticmethod
    def _form_to_dict(form) -> Dict[str, Any]:
        """Convert a result form to a flat dict of {var: value}."""
        result = {}
        try:
            if hasattr(form, 'get_fields'):
                for var, field in form.get_fields().items():
                    val = field.get('value', '')
                    # text-multi returns list — join for usability
                    if isinstance(val, list):
                        val = '\n'.join(str(v) for v in val)
                    result[var] = val
            elif hasattr(form, 'get_values'):
                for k, v in form.get_values().items():
                    if isinstance(v, list):
                        v = '\n'.join(str(x) for x in v)
                    result[k] = v
        except Exception:
            pass
        return result

    @staticmethod
    def _derive_adhoc_node_from_skill(skill: dict) -> Optional[str]:
        """Derive command node URI from an agent card skill entry."""
        # Check explicit node fields
        for key in ('xmpp_adhoc_node', 'adhoc_node', 'command_node', 'node'):
            val = skill.get(key)
            if val and isinstance(val, str):
                return val.strip()
        # Derive from skill ID if not a URI
        skill_id = (skill.get('id') or '').strip()
        if not skill_id:
            return None
        if skill_id.startswith('urn:') or '://' in skill_id:
            return skill_id
        return f"urn:xmpp:a2a:cmd:{skill_id}"

    # ── Outbound: Discover Peer Ad-hoc Commands ───────────────────────────

    async def discover_peer_adhoc_commands(
        self,
        peer_jid: str,
        agent_card: Optional[Dict[str, Any]] = None,
    ) -> list:
        """
        Discover available ad-hoc commands on a peer.

        Sources (in order):
        1. Agent card skills array (if provided)
        2. disco#items on http://jabber.org/protocol/commands node

        Returns list of {"node": str, "name": str, "description": str|None, "source": str}
        """
        commands = []
        seen_nodes = set()

        # Source 1: Agent card skills
        if agent_card and isinstance(agent_card, dict):
            skills = agent_card.get("skills") or []
            for skill in skills:
                if not isinstance(skill, dict):
                    continue
                node = self._derive_adhoc_node_from_skill(skill)
                if node and node not in seen_nodes:
                    seen_nodes.add(node)
                    commands.append({
                        "node": node,
                        "name": skill.get("name", "") or "",
                        "description": skill.get("description", "") or "",
                        "source": "agent_card",
                    })

        # Source 2: disco#items fallback — try all known resources
        candidates = self._get_all_resources(peer_jid) or [peer_jid]
        disco_success = False
        for candidate_jid in candidates:
            try:
                disco = self.client['xep_0030']
                items_iq = await asyncio.wait_for(
                    disco.get_items(jid=candidate_jid, node="http://jabber.org/protocol/commands"),
                    timeout=15,
                )
                for item in items_iq['disco_items']['items']:
                    node = item[1]  # (jid, node, name)
                    name = item[2] or ""
                    if node and node not in seen_nodes:
                        seen_nodes.add(node)
                        commands.append({
                            "node": node,
                            "name": name,
                            "description": "",
                            "source": "disco",
                        })
                disco_success = True
                break  # success on this resource, no need to try others
            except Exception as e:
                logger.debug(
                    "[XMPP-A2A] discover_commands: disco#items failed for %s: %s (trying next resource)",
                    candidate_jid, e,
                )
        if not disco_success:
            logger.debug("[XMPP-A2A] discover_commands: disco#items failed on all resources for %s", peer_jid)

        logger.info(
            "[XMPP-A2A] discover_commands: peer=%s found=%d (agent_card=%d disco=%d)",
            peer_jid, len(commands),
            sum(1 for c in commands if c["source"] == "agent_card"),
            sum(1 for c in commands if c["source"] == "disco"),
        )
        return commands

    def _resolve_full_jid(self, target_jid: str) -> str:
        """Best-effort resolution of bare JID to a full JID using the roster.

        If the input already contains a resource ('/'), it is returned unchanged.
        Otherwise, look up the first available full JID from presence info.
        Falls back to the bare JID when no resource is known.
        """
        candidates = self._get_all_resources(target_jid)
        return candidates[0] if candidates else target_jid

    def _get_all_resources(self, target_jid: str) -> List[str]:
        """Return all known full JIDs for a bare JID, sorted by priority (desc).

        Returns an empty list if no resources are known (caller should fall
        back to the bare JID).
        """
        if not target_jid:
            return []
        if '/' in target_jid:
            return [target_jid]
        try:
            roster = getattr(self.client, 'client_roster', None)
            if roster is None:
                return []
            # Avoid RosterNode.__getitem__ side effect which silently adds
            # strangers to the local roster via add(save=True).
            if hasattr(roster, 'has_jid') and not roster.has_jid(target_jid):
                return []
            entry = roster[target_jid]
            resources = getattr(entry, 'resources', None)
            if not resources:
                return []
            # Sort resources by priority descending
            sorted_res = sorted(
                resources.items(),
                key=lambda kv: kv[1].get('priority', 0) if isinstance(kv[1], dict) else 0,
                reverse=True,
            )
            return [f"{target_jid}/{r}" for r, _ in sorted_res]
        except Exception as e:
            logger.debug("_get_all_resources: failed for %s: %s", target_jid, e)
        return []

    # ── Initialization ─────────────────────────────────────────────────────

    async def reload_a2a(self):
        """
        Lightweight hot-reload: re-read DB config and re-register A2A pieces
        without dropping the XMPP session.

        Useful when the user updates a2a_config (agent card / commands) via the
        UI and we want changes to take effect quickly. Falls back gracefully
        if any sub-step fails.
        """
        logger.info("[XMPP-A2A] reload_a2a: starting in-place reload")

        # Reset cached card so the next initialize() picks up the latest value
        self._agent_card = None

        # Clear previously registered commands from xep_0050 to avoid leftovers.
        try:
            adhoc = self.client['xep_0050']
            if adhoc and hasattr(adhoc, 'commands') and isinstance(adhoc.commands, dict):
                for node in list(self._registered_commands):
                    # slixmpp versions may key xep_0050.commands by node or by
                    # tuple/list such as (jid, node). Support both shapes.
                    keys_to_drop = []
                    for k in list(adhoc.commands.keys()):
                        if k == node:
                            keys_to_drop.append(k)
                        elif isinstance(k, (tuple, list)) and len(k) >= 2 and k[1] == node:
                            keys_to_drop.append(k)
                    for k in keys_to_drop:
                        adhoc.commands.pop(k, None)
        except Exception as e:
            logger.warning("[XMPP-A2A] reload_a2a: failed to clear old commands: %s", e)

        self._registered_commands = []
        self._command_instances = {}

        # Re-run the full initialization steps (idempotent at the disco/PEP level)
        try:
            await self.initialize()
        except Exception as e:
            logger.error("[XMPP-A2A] reload_a2a: initialize() failed: %s", e)

        logger.info("[XMPP-A2A] reload_a2a: complete (%d commands registered)",
                    len(self._registered_commands))

    async def initialize(self):
        """
        Full initialization sequence, called after XMPP session starts.
        1. Try inline agent card from DB config; fall back to URL fetch
        2. Register disco features
        3. Publish agent card via PEP
        4. Register ad-hoc command handlers (plugin-based)
        """
        logger.info("Initializing XMPP A2A integration...")

        # Try inline agent card from a2a_config first
        a2a_config = self._load_a2a_config()
        inline_card = a2a_config.get('agent_card')
        if inline_card and isinstance(inline_card, dict) and any(inline_card.values()):
            self._agent_card = inline_card
            logger.info(
                "Using inline agent card from a2a_config: name=%s",
                inline_card.get('name', 'unknown'),
            )
        else:
            # Fall back to URL fetch
            await self.fetch_agent_card()

        # Register Service Discovery features
        self.register_disco_features()

        # Publish via PEP
        await self.publish_agent_card_pep()

        # Register ad-hoc commands (plugin-based)
        self.register_adhoc_commands()

        logger.info("XMPP A2A initialization complete")
