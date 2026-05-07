"""
XMPP A2A Integration Module

Provides A2A (Agent-to-Agent) capabilities over XMPP:
- Fetches agent card from agent_cfg.memo.agent_card_url
- Publishes agent card via XEP-0163 PEP
- Advertises A2A capabilities via XEP-0030 Service Discovery
- Handles incoming Ad-hoc Commands (XEP-0050) for business card exchange
- Discovers and invokes peer A2A capabilities

Data flow:
  aisns_cfg.agent_id -> agent_cfg -> memo JSON -> agent_card_url
  -> HTTP-fetch agent card -> publish via XMPP Disco + PEP
"""

import json
import logging
import asyncio
import uuid
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# A2A namespace URNs for XMPP disco features
A2A_FEATURE_NS = "urn:xmpp:a2a:1"
A2A_BUSINESS_CARD_NS = "urn:xmpp:a2a:business_card:1"
A2A_PEP_NODE = "urn:xmpp:a2a:agentcard"
A2A_ADHOC_EXCHANGE_NODE = "urn:xmpp:a2a:cmd:exchange_business_card"
A2A_ADHOC_TASK_NODE = "urn:xmpp:a2a:cmd:tasks"


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

    # ── XEP-0050 Ad-hoc Commands ──────────────────────────────────────────

    def register_adhoc_commands(self):
        """Register ad-hoc command handlers for A2A skills."""
        try:
            adhoc = self.client['xep_0050']
            if adhoc:
                # Register exchange_business_card command
                adhoc.add_command(
                    node=A2A_ADHOC_EXCHANGE_NODE,
                    name="Exchange Business Card",
                    handler=self._handle_exchange_command,
                )
                if A2A_ADHOC_EXCHANGE_NODE not in self._registered_commands:
                    self._registered_commands.append(A2A_ADHOC_EXCHANGE_NODE)
                logger.info("Registered ad-hoc command: %s", A2A_ADHOC_EXCHANGE_NODE)

                # Register generic A2A task command (JSON-RPC transport)
                adhoc.add_command(
                    node=A2A_ADHOC_TASK_NODE,
                    name="A2A Task",
                    handler=self._handle_a2a_task_command,
                )
                if A2A_ADHOC_TASK_NODE not in self._registered_commands:
                    self._registered_commands.append(A2A_ADHOC_TASK_NODE)
                logger.info("Registered ad-hoc command: %s", A2A_ADHOC_TASK_NODE)

        except Exception as e:
            logger.error("Failed to register ad-hoc commands: %s", e)

    async def _handle_exchange_command(self, iq, session):
        """
        Handle an incoming exchange_business_card ad-hoc command.

        Stage 1 (execute): Return a data form requesting the sender's card.
        Stage 2 (complete): Process the submitted card and return our card.
        """
        try:
            form = self.client['xep_0004'].make_form(
                ftype='form',
                title='Exchange Business Card',
            )
            form.addField(var='name', ftype='text-single', label='Name', value='')
            form.addField(var='company', ftype='text-single', label='Company', value='')
            form.addField(var='title', ftype='text-single', label='Title', value='')
            form.addField(var='email', ftype='text-single', label='Email', value='')
            form.addField(var='xmpp', ftype='text-single', label='XMPP', value='')
            form.addField(var='website', ftype='text-single', label='Website', value='')
            form.addField(var='phone', ftype='text-single', label='Phone', value='')

            session['payload'] = form
            session['next'] = self._handle_exchange_submit
            session['has_next'] = True
            session['allow_complete'] = True  # Advertise 'complete' action (XEP-0050 compliance)
            return session

        except Exception as e:
            logger.error("Error in exchange command handler: %s", e)
            session['notes'] = [('error', f'Internal error: {e}')]
            return session

    async def _handle_exchange_submit(self, payload, session):
        """Process the submitted business card form and return our card."""
        try:
            # Extract submitted card data from the form
            their_card = {}
            if hasattr(payload, 'get_fields'):
                fields = payload.get_fields()
                for var_name in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone'):
                    field = fields.get(var_name)
                    if field:
                        their_card[var_name] = field.get('value', '') or ''
            elif hasattr(payload, 'values'):
                their_card = dict(payload.values)

            sender_jid = str(session.get('from', ''))
            their_card['sender_jid'] = sender_jid

            # Store via A2A server logic
            try:
                import sys
                import os as _os
                _proj_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))))
                if _proj_root not in sys.path:
                    sys.path.insert(0, _proj_root)
                from a2aserver.business_card import exchange_business_card
                my_card = exchange_business_card(their_card, sender_jid=sender_jid)
            except Exception as e:
                logger.error("Failed to process card exchange: %s", e)
                my_card = self._load_my_business_card()

            # Build response form with our card
            result_form = self.client['xep_0004'].make_form(
                ftype='result',
                title='Business Card Exchange Result',
            )
            for key in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone'):
                result_form.addField(var=key, ftype='text-single', label=key.capitalize(),
                                    value=my_card.get(key, ''))

            session['payload'] = result_form
            session['next'] = None
            session['has_next'] = False
            return session

        except Exception as e:
            logger.error("Error processing exchange submission: %s", e)
            session['notes'] = [('error', f'Processing error: {e}')]
            return session

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

    async def call_exchange_business_card(self, target_jid: str) -> Optional[Dict[str, Any]]:
        """
        Invoke exchange_business_card on a peer via XEP-0050 Ad-hoc Commands.

        Flow:
        1. Send execute command -> receive form
        2. Fill form with own card data
        3. Submit with action='complete'
        4. Parse returned card

        Args:
            target_jid: The target XMPP JID

        Returns:
            The peer's business card dict, or None on failure
        """
        try:
            # Load our card to send
            my_card = self._load_my_business_card()
            if not my_card:
                logger.warning("No business card configured, cannot exchange")
                return None

            # Step 1: Execute the command
            resp = await self.client['xep_0050'].send_command(
                target_jid,
                A2A_ADHOC_EXCHANGE_NODE,
                action='execute',
            )

            # Step 2: Fill the form
            session_id = resp['command']['sessionid']
            form = resp['command']['form']

            # Set our card values in the form (use set_values, not set_fields:
            # set_fields would wipe field declarations and fail on string values).
            # Also flip form type to 'submit' for XEP-0004 compliance.
            try:
                form['type'] = 'submit'
            except Exception:
                pass
            card_values = {
                key: (my_card.get(key, '') or '')
                for key in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone')
            }
            if hasattr(form, 'set_values'):
                try:
                    form.set_values(card_values)
                except Exception as e:
                    logger.warning("set_values failed for exchange form: %s", e)
                    fields = form.get_fields() if hasattr(form, 'get_fields') else {}
                    for key, val in card_values.items():
                        if key in fields:
                            fields[key]['value'] = val
            else:
                # Fallback: directly mutate field values
                fields = form.get_fields() if hasattr(form, 'get_fields') else {}
                for key, val in card_values.items():
                    if key in fields:
                        fields[key]['value'] = val

            # Step 3: Submit the completed form
            result = await self.client['xep_0050'].send_command(
                target_jid,
                A2A_ADHOC_EXCHANGE_NODE,
                action='complete',
                sessionid=session_id,
                payload=form,
            )

            # Step 4: Parse the returned card
            result_form = result['command'].get('form')
            if result_form:
                peer_card = {}
                if hasattr(result_form, 'get_fields'):
                    fields = result_form.get_fields()
                    for key in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone'):
                        field = fields.get(key)
                        if field:
                            peer_card[key] = field.get('value', '') or ''
                else:
                    peer_card = dict(getattr(result_form, 'values', {}))

                # Store the received card
                peer_card['sender_jid'] = target_jid
                try:
                    from a2aserver.db import init_db, add_received_card
                    init_db()
                    add_received_card(peer_card)
                except Exception as e:
                    logger.warning("Failed to store peer card: %s", e)

                logger.info("Exchanged business card with %s: %s", target_jid, peer_card.get('name', ''))
                return peer_card
            else:
                logger.warning("No form in exchange result from %s", target_jid)
                return None

        except Exception as e:
            logger.error("Failed to exchange business card with %s: %s", target_jid, e)
            return None

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
            logger.warning("fetch_peer_agent_card_pep: invalid peer_jid=%s", peer_jid)
            return None

        try:
            pubsub = self.client['xep_0060']
        except Exception:
            pubsub = None

        if pubsub is None:
            logger.warning("fetch_peer_agent_card_pep: xep_0060 not available")
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
                            "Fetched peer agent card via PEP from %s: name=%s",
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

            logger.info("No agent card items found in PEP node for %s", bare_jid)
            return None

        except asyncio.TimeoutError:
            logger.warning("fetch_peer_agent_card_pep: timeout reading PEP from %s", bare_jid)
            return None
        except Exception as e:
            logger.warning("fetch_peer_agent_card_pep: failed for %s: %s", bare_jid, e)
            return None

    # ── Generic A2A Task Ad-hoc Command (JSON-RPC transport) ─────────────

    async def _handle_a2a_task_command(self, iq, session):
        """
        Handle an incoming generic A2A task ad-hoc command.

        Stage 1 (execute): Return a data form with a jsonrpc_request field
        for the caller to fill in their JSON-RPC 2.0 request.
        """
        try:
            form = self.client['xep_0004'].make_form(
                ftype='form',
                title='A2A Task',
            )
            form.addField(
                var='jsonrpc_request',
                ftype='text-multi',
                label='JSON-RPC Request',
                value='',
            )
            session['payload'] = form
            session['next'] = self._handle_a2a_task_submit
            session['has_next'] = True
            session['allow_complete'] = True  # Advertise 'complete' action (XEP-0050 compliance)
            return session
        except Exception as e:
            logger.error("Error in A2A task command handler: %s", e)
            session['notes'] = [('error', f'Internal error: {e}')]
            return session

    async def _handle_a2a_task_submit(self, payload, session):
        """
        Process a submitted A2A task JSON-RPC request.

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
                sender_jid,
                len(request_str),
            )

            if not request_str:
                response_str = json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Empty request"},
                    "id": None,
                })
            else:
                # Try forwarding to local A2A server first
                response_str = await self._forward_to_local_a2a_server(request_str)

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
                        response_dict = self._local_handle_jsonrpc(request_dict, sender_jid)
                        response_str = json.dumps(response_dict, ensure_ascii=False)

            # Build result form
            result_form = self.client['xep_0004'].make_form(
                ftype='result',
                title='A2A Task Result',
            )
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

    async def _forward_to_local_a2a_server(self, request_str: str) -> Optional[str]:
        """
        Forward a JSON-RPC request to the local A2A server via HTTP POST.

        Uses run_in_executor with sync urllib to avoid event-loop conflicts.
        Returns the response body string, or None if the server is unreachable.
        """
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_http_post_a2a, request_str),
                timeout=30,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("_forward_to_local_a2a_server: timeout (30s)")
            return None
        except Exception as e:
            logger.warning("_forward_to_local_a2a_server: failed: %s", e)
            return None

    @staticmethod
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

    def _local_handle_jsonrpc(self, request: dict, sender_jid: str = "") -> dict:
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

            # Detect if message contains structured card data (type=data with card-like fields)
            their_card = {}
            card_field_names = {"name", "company", "title", "email", "xmpp", "website", "phone"}
            for part in parts:
                if part.get("type") == "data":
                    data = part.get("data", {})
                    # Only treat as card exchange if data contains at least one card field
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
            my_card = self._load_my_business_card() or {}
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

    # ── Outbound: Call Peer A2A Task via Ad-hoc Command ───────────────────

    async def call_a2a_task(self, target_jid: str, jsonrpc_request: dict) -> dict:
        """
        Invoke a generic A2A task on a peer via XMPP Ad-hoc Command.

        Sends a JSON-RPC 2.0 request through the urn:xmpp:a2a:cmd:tasks
        ad-hoc command node. Non-blocking, 300-second timeout.

        Flow:
        1. Send execute action → receive form with jsonrpc_request field
        2. Fill form with JSON-RPC request
        3. Submit with action=complete
        4. Parse returned jsonrpc_response

        Args:
            target_jid: The target XMPP JID
            jsonrpc_request: The JSON-RPC 2.0 request dict

        Returns:
            dict with 'ok' (bool) and 'result' (parsed response) or 'error' (str)
        """
        # Lazy import slixmpp exception types to keep module import lightweight
        try:
            from slixmpp.exceptions import IqError, IqTimeout
        except Exception:  # pragma: no cover
            IqError = IqTimeout = None  # type: ignore

        # Resolve bare JID to a full JID via roster/presence when possible
        # (XEP-0050 ad-hoc commands typically target a specific resource).
        resolved_jid = self._resolve_full_jid(target_jid)

        try:
            result = await asyncio.wait_for(
                self._call_a2a_task_impl(resolved_jid, jsonrpc_request),
                timeout=300,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("call_a2a_task: timed out (300s) for %s", resolved_jid)
            return {"ok": False, "error": "timeout", "detail": "XMPP ad-hoc command timed out (300s)"}
        except Exception as e:
            # Distinguish IqTimeout / IqError from generic exceptions
            if IqTimeout is not None and isinstance(e, IqTimeout):
                logger.warning("call_a2a_task: IQ timeout for %s", resolved_jid)
                return {"ok": False, "error": "peer_unreachable", "detail": "IQ timeout (peer offline or unresponsive)"}
            if IqError is not None and isinstance(e, IqError):
                cond = "unknown"
                try:
                    cond = e.iq['error']['condition'] or "unknown"
                except Exception:
                    pass
                logger.warning("call_a2a_task: IqError for %s: %s", resolved_jid, cond)
                return {"ok": False, "error": cond, "detail": str(e)}
            logger.error("call_a2a_task: unexpected error for %s: %s", resolved_jid, e)
            return {"ok": False, "error": "unexpected", "detail": str(e)}

    def _resolve_full_jid(self, target_jid: str) -> str:
        """Best-effort resolution of bare JID to a full JID using the roster.

        If the input already contains a resource ('/'), it is returned unchanged.
        Otherwise, look up the first available full JID from presence info.
        Falls back to the bare JID when no resource is known.
        """
        if not target_jid or '/' in target_jid:
            return target_jid
        try:
            roster = getattr(self.client, 'client_roster', None)
            if roster is None:
                return target_jid
            # Avoid RosterNode.__getitem__ side effect which silently adds
            # strangers to the local roster via add(save=True).
            if hasattr(roster, 'has_jid') and not roster.has_jid(target_jid):
                return target_jid
            entry = roster[target_jid]
            resources = getattr(entry, 'resources', None)
            if resources:
                # Pick the resource with the highest priority
                try:
                    best = max(
                        resources.items(),
                        key=lambda kv: kv[1].get('priority', 0) if isinstance(kv[1], dict) else 0,
                    )[0]
                except Exception:
                    best = next(iter(resources.keys()))
                if best:
                    return f"{target_jid}/{best}"
        except Exception as e:
            logger.debug("_resolve_full_jid: failed for %s: %s", target_jid, e)
        return target_jid

    async def _call_a2a_task_impl(self, target_jid: str, jsonrpc_request: dict) -> dict:
        """Internal implementation of the A2A task call via ad-hoc command."""
        request_str = json.dumps(jsonrpc_request, ensure_ascii=False)

        # Step 1: Execute command → get form
        adhoc = self.client['xep_0050']
        resp = await adhoc.send_command(
            target_jid,
            A2A_ADHOC_TASK_NODE,
            action='execute',
        )

        # Step 2: Fill the jsonrpc_request field.
        # IMPORTANT: use set_values (not set_fields). set_fields wipes existing
        # field declarations and expects dict metadata for each value, so passing
        # a string raises TypeError silently and the form ends up empty.
        # Also flip the form type to 'submit' for XEP-0004 compliance.
        session_id = resp['command']['sessionid']
        form = resp['command']['form']

        try:
            form['type'] = 'submit'
        except Exception:
            pass

        if hasattr(form, 'set_values'):
            try:
                form.set_values({'jsonrpc_request': request_str})
            except Exception as e:
                logger.warning("set_values failed for a2a task form: %s", e)
                # Fallback: directly mutate field value
                fields = form.get_fields() if hasattr(form, 'get_fields') else {}
                if 'jsonrpc_request' in fields:
                    fields['jsonrpc_request']['value'] = request_str
        else:
            fields = form.get_fields() if hasattr(form, 'get_fields') else {}
            if 'jsonrpc_request' in fields:
                fields['jsonrpc_request']['value'] = request_str

        # Step 3: Submit with complete
        result = await adhoc.send_command(
            target_jid,
            A2A_ADHOC_TASK_NODE,
            action='complete',
            sessionid=session_id,
            payload=form,
        )

        # Step 4: Parse the result
        result_form = result['command'].get('form')
        if not result_form:
            # Check for notes (error case)
            notes = result['command'].get('notes', [])
            if notes:
                error_msg = '; '.join(str(n) for n in notes)
                return {"ok": False, "error": f"Ad-hoc command error: {error_msg}"}
            return {"ok": False, "error": "No response form received"}

        # Extract jsonrpc_response
        response_str = ""
        if hasattr(result_form, 'get_fields'):
            fields = result_form.get_fields()
            field = fields.get('jsonrpc_response')
            if field:
                val = field.get('value', '')
                if isinstance(val, list):
                    response_str = '\n'.join(str(v) for v in val)
                else:
                    response_str = str(val)
        elif hasattr(result_form, 'values'):
            response_str = str(result_form.values.get('jsonrpc_response', ''))

        response_str = response_str.strip()
        if not response_str:
            return {"ok": False, "error": "Empty response from peer"}

        try:
            response_dict = json.loads(response_str)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON response: {e}"}

        # Check for JSON-RPC error
        if "error" in response_dict and response_dict["error"]:
            err = response_dict["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return {"ok": False, "error": f"JSON-RPC error: {msg}", "raw": response_dict}

        logger.info(
            "A2A task call to %s completed: method=%s",
            target_jid,
            jsonrpc_request.get("method", ""),
        )
        return {"ok": True, "result": response_dict.get("result", {})}

    # ── Initialization ─────────────────────────────────────────────────────

    async def initialize(self):
        """
        Full initialization sequence, called after XMPP session starts.
        1. Fetch agent card from configured URL
        2. Register disco features
        3. Publish agent card via PEP
        4. Register ad-hoc command handlers
        """
        logger.info("Initializing XMPP A2A integration...")

        # Fetch the agent card
        await self.fetch_agent_card()

        # Register Service Discovery features
        self.register_disco_features()

        # Publish via PEP
        await self.publish_agent_card_pep()

        # Register ad-hoc commands
        self.register_adhoc_commands()

        logger.info("XMPP A2A initialization complete")
