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
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# A2A namespace URNs for XMPP disco features
A2A_FEATURE_NS = "urn:xmpp:a2a:1"
A2A_BUSINESS_CARD_NS = "urn:xmpp:a2a:business_card:1"
A2A_PEP_NODE = "urn:xmpp:a2a:agentcard"
A2A_ADHOC_EXCHANGE_NODE = "urn:xmpp:a2a:cmd:exchange_business_card"


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
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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

            # Set our card values in the form
            if hasattr(form, 'set_fields'):
                for key in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone'):
                    try:
                        form.set_fields({key: my_card.get(key, '')})
                    except Exception:
                        pass
            elif hasattr(form, 'fields'):
                for key in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone'):
                    if key in form.fields:
                        form.fields[key]['value'] = my_card.get(key, '')

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
