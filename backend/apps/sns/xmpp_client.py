"""XMPP Client Manager for SNS Module"""
import logging
import asyncio
import slixmpp
from typing import Optional, Dict
from sqlalchemy.orm import Session
from backend.config.database import get_db_sync
from backend.database.models.chat import AiChatCfg, AIFriend, AIChatMessages
from backend.apps.sns.message_formatter import format_internal_xmpp_message_for_storage

logger = logging.getLogger(__name__)


class XMPPClient(slixmpp.ClientXMPP):
    """XMPP Client implementation"""

    def __init__(self, jid: str, password: str, db_session: Session):
        super().__init__(jid, password)
        self.db = db_session
        self.jid_str = jid

        # Register event handlers
        self.add_event_handler("session_start", self.on_session_start)
        self.add_event_handler("message", self.on_message)
        self.add_event_handler("presence_subscribe", self.on_presence_subscribe)
        self.add_event_handler("roster_update", self.on_roster_update)
        self.add_event_handler("presence_subscribed", self.on_presence_subscribed)
        self.add_event_handler("disconnected", self.on_disconnected)
        self.add_event_handler("connection_failed", self.on_connection_failed)

        # Register plugins
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0199', {'keepalive': False})  # XMPP Ping (we manage our own heartbeat)
        self.register_plugin('xep_0363')  # HTTP File Upload

        # Subscription waiter infrastructure
        self._subscription_waiters: Dict[str, asyncio.Event] = {}

        self._roster_cleanup_task: Optional[asyncio.Task] = None
        self._last_roster_dump_ts: float = 0.0

        # Heartbeat configuration
        self.heartbeat_interval = 30  # seconds between pings
        self.ping_timeout = 10  # seconds to wait for pong reply
        self.heartbeat_task = None
        self._consecutive_failures = 0
        self._max_failures = 3  # trigger reconnect after this many consecutive failures

    async def on_session_start(self, event):
        """Handle session start"""
        logger.info(f"XMPP session started for {self.jid_str}")
        self.send_presence()
        await self.get_roster()

        try:
            if self._roster_cleanup_task is None or self._roster_cleanup_task.done():
                self._roster_cleanup_task = asyncio.create_task(self._delayed_roster_cleanup())
        except Exception as e:
            logger.error(f"Failed to schedule roster cleanup task: {e}")

        # Reset reconnect backoff on successful session
        try:
            manager = XMPPClientManager.get_instance()
            manager.on_session_start_reset()
        except Exception:
            pass

        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

    async def _delayed_roster_cleanup(self):
        try:
            await asyncio.sleep(20)
            await self.cleanup_roster_if_needed(max_contacts=250)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"Roster cleanup task crashed: {e}")

    def _find_roster_item(self, bare_jid: str):
        try:
            for k in self.client_roster.keys():
                if str(k).split('/')[0] == bare_jid:
                    try:
                        return self.client_roster[k]
                    except Exception:
                        return None
        except Exception:
            return None
        return None

    @staticmethod
    def _read_roster_field(item, field: str, default=None):
        """Read a field from a roster item using bracket access first.

        slixmpp RosterItem exposes state via __getitem__ (bracket access),
        NOT via .get() or getattr(). Plain dicts work with all three.
        """
        if item is None:
            return default
        # 1) bracket access – works for both slixmpp RosterItem and plain dict
        try:
            val = item[field]
            if val is not None:
                return val
        except (KeyError, TypeError, IndexError):
            pass
        # 2) .get() – works for plain dicts
        try:
            val = item.get(field)
            if val is not None:
                return val
        except (AttributeError, TypeError):
            pass
        # 3) getattr – last resort
        try:
            val = getattr(item, field, None)
            if val is not None:
                return val
        except Exception:
            pass
        return default

    def _get_roster_jids(self):
        jids = set()
        try:
            groups = self.client_roster.groups()
            for group in groups:
                for jid in groups[group]:
                    bare = str(jid).split('/')[0]
                    if bare and bare != self.jid_str:
                        jids.add(bare)
        except Exception:
            pass

        if not jids:
            try:
                for jid in self.client_roster.keys():
                    bare = str(jid).split('/')[0]
                    if bare and bare != self.jid_str:
                        jids.add(bare)
            except Exception:
                pass

        return list(jids)

    async def cleanup_roster_if_needed(self, max_contacts: int = 250):
        jids = self._get_roster_jids()
        roster_size = len(jids)

        if roster_size <= max_contacts:
            logger.info(f"Roster cleanup skipped: roster_size={roster_size} <= max_contacts={max_contacts}")
            return

        remove_count = roster_size - max_contacts
        logger.info(
            "Roster cleanup starting: roster_size=%s, max_contacts=%s, remove_count=%s",
            roster_size,
            max_contacts,
            remove_count,
        )

        activity_map: Dict[str, Optional[object]] = {}
        try:
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()
            owner = config.account if config else None

            if owner:
                friends = self.db.query(AIFriend).filter(
                    AIFriend.owner_sns_account == owner,
                    AIFriend.account.in_(jids),
                ).all()
                for f in friends:
                    activity_map[f.account] = f.last_message_time
        except Exception as e:
            logger.error(f"Roster cleanup failed to read activity from DB: {e}")

        def _activity_key(jid: str):
            ts = activity_map.get(jid)
            if ts is None:
                return 0
            try:
                return ts.timestamp()
            except Exception:
                return 0

        candidates = sorted(jids, key=_activity_key)
        to_remove = candidates[:remove_count]

        removed = 0
        failed = 0
        for idx, jid in enumerate(to_remove, start=1):
            try:
                try:
                    self.del_roster_item(jid)
                except Exception:
                    iq = self.Iq()
                    iq['type'] = 'set'
                    query = slixmpp.xmlstream.ET.Element('{jabber:iq:roster}query')
                    item = slixmpp.xmlstream.ET.Element('item', {'jid': jid, 'subscription': 'remove'})
                    query.append(item)
                    iq.xml.append(query)
                    iq.send(now=True)

                self.send_presence(pto=jid, ptype='unsubscribe')
                self.send_presence(pto=jid, ptype='unsubscribed')

                try:
                    from db.write_queue import db_write

                    _jid = jid

                    def _set_none(session):
                        try:
                            cfg = session.query(AiChatCfg).filter(
                                AiChatCfg.is_delete == False
                            ).first()
                            if not cfg:
                                return
                            friend = session.query(AIFriend).filter(
                                AIFriend.owner_sns_account == cfg.account,
                                AIFriend.account == _jid,
                            ).first()
                            if friend:
                                friend.subscription = 'none'
                        except Exception:
                            return

                    db_write(_set_none, description="xmpp_client_roster_cleanup")
                except Exception as e:
                    logger.error(f"Roster cleanup failed to update DB for {jid}: {e}")

                removed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Roster cleanup failed for {jid}: {e}")

            if (idx % 10) == 0:
                await asyncio.sleep(0)

        logger.info(
            "Roster cleanup finished: attempted=%s removed=%s failed=%s",
            len(to_remove),
            removed,
            failed,
        )

    async def on_message(self, msg):
        """Handle incoming messages"""
        if msg['type'] in ('chat', 'normal'):
            from_jid = str(msg['from']).split('/')[0]
            body = msg['body']

            if (not from_jid) or ('@' not in from_jid):
                logger.warning("Ignoring message from invalid XMPP account: %s", from_jid)
                return

            logger.info(f"Received message from {from_jid}: {body}")

            # Save to database first so the incoming message gets an earlier
            # create_time than any response the engine may generate.
            try:
                config = self.db.query(AiChatCfg).filter(
                    AiChatCfg.is_delete == False
                ).first()

                if config:
                    from datetime import datetime
                    stored_body = format_internal_xmpp_message_for_storage(body)
                    from db.write_queue import db_write
                    _from_jid = from_jid
                    _config_account = config.account
                    _config_nickname = config.nickname or config.account
                    _stored_body = stored_body

                    def _save_incoming(session):
                        friend = session.query(AIFriend).filter(
                            AIFriend.account == _from_jid,
                            AIFriend.owner_sns_account == _config_account
                        ).first()
                        if friend:
                            if not friend.nick_name:
                                friend.nick_name = _from_jid
                        else:
                            friend = AIFriend(
                                account=_from_jid,
                                nick_name=_from_jid,
                                groups="",
                                owner_sns_account=_config_account,
                                subscription="none",
                                new_message_flag=True,
                                last_message_time=datetime.now(),
                            )
                            session.add(friend)

                        message = AIChatMessages(
                            conversation_id=f"{_config_account}_{_from_jid}",
                            flag=1,  # 1=receive
                            content=_stored_body,
                            owner_account=_config_account,
                            friend_account=_from_jid,
                            owner_name=_config_nickname,
                            friend_name=_from_jid
                        )
                        session.add(message)
                        session.flush()
                        friend.new_message_flag = True
                        friend.last_message_time = datetime.now()
                        return {
                            'message_id': message.id,
                            'create_time': message.create_time.isoformat() if message.create_time else None,
                            'contact': {
                                'account': friend.account,
                                'nick_name': friend.nick_name or friend.account,
                                'new_message_flag': bool(friend.new_message_flag),
                                'last_message_time': friend.last_message_time.isoformat() if friend.last_message_time else None,
                            }
                        }

                    result = db_write(_save_incoming, description="xmpp_client_save_incoming")
                    contact_payload = result['contact']

                    await self.broadcast_new_message({
                        'type': 'new_message',
                        'data': {
                            'id': result['message_id'],
                            'from_account': from_jid,
                            'content': stored_body,
                            'flag': 1,
                            'create_time': result['create_time'],
                            'contact': contact_payload,
                        }
                    })

                    await self.broadcast_new_message({
                        'type': 'contact_upserted',
                        'data': contact_payload
                    })
            except Exception as e:
                logger.error(f"Error saving message to database: {e}")

            # Forward to AI Social Engine after DB save so that any engine
            # response (e.g. goods delivery) gets a later create_time.
            try:
                from backend.apps.sns.service_async import _social_engine_instance
                if _social_engine_instance:
                    event = {
                        'body': body,
                        'from': from_jid
                    }
                    await _social_engine_instance.receiveMessage(event)
                    logger.info(f"Message forwarded to AI Social Engine")
            except Exception as e:
                logger.error(f"Error forwarding message to AI Social Engine: {e}")

    async def broadcast_new_message(self, message_data: dict):
        """Broadcast new message to all WebSocket clients"""
        try:
            # Import here to avoid circular dependency
            from backend.shared.websocket_manager import manager as ws_manager
            await ws_manager.broadcast(message_data)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")

    async def on_presence_subscribe(self, presence):
        """Handle incoming subscription requests: accept and reciprocate immediately."""
        from_jid = str(presence['from']).split('/')[0]
        logger.info(f"Subscription request from {from_jid}")

        # Always accept the inbound subscription request.
        self.send_presence(pto=from_jid, ptype='subscribed')

        # Reciprocate only if we are not already subscribed to them.
        # This avoids potential subscribe ping-pong when both sides auto-reciprocate.
        current_sub = None
        try:
            roster_item = self._find_roster_item(from_jid)
            current_sub = self._read_roster_field(roster_item, 'subscription')
        except Exception:
            current_sub = None

        if (current_sub or '').strip() not in ('to', 'both'):
            self.send_presence(pto=from_jid, ptype='subscribe')

        # Sync roster to DB and notify waiters
        try:
            self.update_roster_local(from_jid)
            self._notify_subscription_waiters(from_jid)
        except Exception as e:
            logger.error(f"Error syncing roster after subscribe from {from_jid}: {e}")

    async def on_presence_subscribed(self, presence):
        """Handle acknowledgement that our subscription request was accepted."""
        from_jid = str(presence['from']).split('/')[0]
        logger.info(f"Subscription accepted by {from_jid}")

        # Sync roster to DB and notify waiters
        try:
            self.update_roster_local(from_jid)
            self._notify_subscription_waiters(from_jid)
        except Exception as e:
            logger.error(f"Error syncing roster after subscribed from {from_jid}: {e}")

    async def on_roster_update(self, event):
        """Handle roster updates and notify subscription waiters."""
        logger.info("Roster updated")
        groups = self.client_roster.groups()

        for group in groups:
            for jid in groups[group]:
                self.update_roster_local(jid)
                self._notify_subscription_waiters(str(jid).split('/')[0])

    def update_roster_local(self, jid: str):
        """Update local database with roster information"""
        if jid == self.jid_str:
            return

        if (not jid) or ('@' not in str(jid)):
            logger.warning("Skipping roster update for invalid XMPP account: %s", jid)
            return

        try:
            account = str(jid).split('/')[0]
            roster_item = self._find_roster_item(account)
            if roster_item is None:
                roster_item = self.client_roster[jid]

            nick_name = self._read_roster_field(roster_item, 'name', jid) or jid
            raw_groups = self._read_roster_field(roster_item, 'groups')
            if isinstance(raw_groups, (set, list, tuple)):
                groups = ','.join([str(g) for g in raw_groups]) if raw_groups else ""
            else:
                groups = str(raw_groups) if raw_groups else ""
            subscription = self._read_roster_field(roster_item, 'subscription', 'none') or 'none'

            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                return

            owner_account = config.account

            # Check if friend exists and upsert via write queue
            from db.write_queue import db_write
            _account = account
            _nick_name = nick_name
            _groups = groups
            _subscription = subscription
            _owner_account = owner_account

            def _upsert_roster(session):
                friend = session.query(AIFriend).filter(
                    AIFriend.account == _account,
                    AIFriend.owner_sns_account == _owner_account
                ).first()
                if friend:
                    friend.nick_name = _nick_name
                    friend.groups = _groups
                    friend.subscription = _subscription
                else:
                    friend = AIFriend(
                        account=_account,
                        nick_name=_nick_name,
                        groups=_groups,
                        owner_sns_account=_owner_account,
                        subscription=_subscription
                    )
                    session.add(friend)

            db_write(_upsert_roster, description="xmpp_client_upsert_roster")
        except Exception as e:
            logger.error(f"Error updating roster for {jid}: {e}")

    async def on_disconnected(self, event):
        """Handle disconnection event"""
        logger.warning(f"XMPP client disconnected for {self.jid_str}")
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
        self._consecutive_failures = 0

    async def on_connection_failed(self, event):
        """Handle connection failure event"""
        logger.error(f"XMPP connection failed for {self.jid_str}")

    async def heartbeat(self):
        """Send periodic pings to keep connection alive"""
        logger.info(f"Heartbeat started for {self.jid_str} (interval={self.heartbeat_interval}s, timeout={self.ping_timeout}s)")
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self['xep_0199'].ping(timeout=self.ping_timeout)
                if self._consecutive_failures > 0:
                    logger.info(f"Heartbeat recovered after {self._consecutive_failures} failure(s)")
                self._consecutive_failures = 0
            except asyncio.CancelledError:
                logger.info("Heartbeat task cancelled")
                return
            except Exception as e:
                self._consecutive_failures += 1
                logger.warning(f"Heartbeat failed ({self._consecutive_failures}/{self._max_failures}): {e}")
                if self._consecutive_failures >= self._max_failures:
                    logger.error(f"Heartbeat failed {self._max_failures} consecutive times, triggering reconnect")
                    try:
                        self.disconnect()
                    except Exception:
                        pass
                    return

    async def send_message_to_jid(self, to_jid: str, content: str):
        """Send a message after ensuring mutual subscription."""
        await self.ensure_mutual_subscription(to_jid)
        self.send_presence()
        self.send_message(
            mto=to_jid,
            mbody=content,
            mtype='chat'
        )

    async def upload_and_send_file(self, to_jid: str, file_path: str, filename: str):
        """Upload file via XEP-0363 and send URL to recipient"""
        await self.ensure_mutual_subscription(to_jid)
        try:
            import os
            import mimetypes

            # Get file info
            file_size = os.path.getsize(file_path)
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            if os.path.splitext(filename)[1].lower() == '.txt':
                content_type = 'text/plain; charset=utf-8'

            # Upload file using XEP-0363
            with open(file_path, 'rb') as file_handle:
                url = await self['xep_0363'].upload_file(
                    filename,
                    size=file_size,
                    content_type=content_type,
                    input_file=file_handle
                )

            # Send URL to recipient (subscription already ensured above)
            file_message = f"📎 File: {filename}\n{url}"
            self.send_presence()
            self.send_message(
                mto=to_jid,
                mbody=file_message,
                mtype='chat'
            )

            return url
        except Exception as e:
            logger.error(f"Error uploading file via XEP-0363: {e}")
            raise

    async def ensure_mutual_subscription(self, to_jid: str, timeout: float = 30.0) -> bool:
        """Ensure mutual subscription with the target JID before sending.

        Checks DB for subscription=='both'. If not, sends subscribe +
        subscribed stanzas and waits up to *timeout* seconds for the
        remote side to reciprocate. Returns True if mutual subscription
        is confirmed, False on timeout (caller should still send).
        """
        bare_jid = str(to_jid).split('/')[0]
        try:
            # Prefer in-memory roster state when available.
            # DB may lag behind roster updates (e.g. due to async write queue).
            try:
                roster_item = self._find_roster_item(bare_jid)
                roster_sub = (str(self._read_roster_field(roster_item, 'subscription') or '')).strip()
                if roster_sub == 'both':
                    try:
                        self.update_roster_local(bare_jid)
                    except Exception:
                        pass
                    return True
            except Exception:
                pass

            sub = self._get_subscription_from_db(bare_jid)
            if sub == 'both':
                return True

            logger.info(f"Subscription with {bare_jid} is '{sub}', requesting mutual subscription")
            try:
                self._dump_roster_to_logs(reason=f"ensure_mutual_subscription:{bare_jid}:{sub}")
            except Exception:
                pass
            self.send_presence(pto=bare_jid, ptype='subscribe')

            event = self._subscription_waiters.get(bare_jid)
            if event is None:
                event = asyncio.Event()
                self._subscription_waiters[bare_jid] = event

            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
                logger.info(f"Mutual subscription established with {bare_jid}")
                return True
            except asyncio.TimeoutError:
                logger.warning(
                    f"Subscription wait timed out after {timeout}s for {bare_jid}, proceeding anyway"
                )
                return False
            finally:
                self._subscription_waiters.pop(bare_jid, None)
        except Exception as e:
            logger.error(f"Error in ensure_mutual_subscription for {bare_jid}: {e}")
            self._subscription_waiters.pop(bare_jid, None)
            return False

    def _get_subscription_from_db(self, bare_jid: str) -> str:
        """Read the subscription field for a JID from the ai_friend table."""
        try:
            try:
                self.db.expire_all()
            except Exception:
                pass
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()
            if not config:
                return 'none'
            friend = self.db.query(AIFriend).filter(
                AIFriend.account == bare_jid,
                AIFriend.owner_sns_account == config.account,
                AIFriend.is_delete == False,
            ).first()
            if friend:
                return (friend.subscription or 'none').strip()
            return 'none'
        except Exception as e:
            logger.error(f"Error reading subscription from DB for {bare_jid}: {e}")
            return 'none'

    def _notify_subscription_waiters(self, bare_jid: str):
        """If a waiter exists for the given JID and subscription is now 'both', signal it."""
        bare_jid = str(bare_jid).split('/')[0]
        event = self._subscription_waiters.get(bare_jid)
        if event is None:
            return
        try:
            sub = self._get_subscription_from_db(bare_jid)
            if sub == 'both':
                event.set()
                logger.info(f"Subscription waiter notified for {bare_jid} (now 'both')")
        except Exception as e:
            logger.error(f"Error notifying subscription waiter for {bare_jid}: {e}")

    def _dump_roster_to_logs(self, reason: str = ""):
        now = 0.0
        try:
            import time

            now = time.time()
        except Exception:
            now = 0.0

        # Throttle full roster dumps to avoid excessive log spam.
        # This is diagnostic-only and should not impact service performance.
        if now and (now - (self._last_roster_dump_ts or 0.0)) < 60.0:
            return

        self._last_roster_dump_ts = now or 0.0

        try:
            roster_keys = []
            try:
                roster_keys = list(self.client_roster.keys())
            except Exception:
                roster_keys = []

            logger.info(
                "XMPP roster dump start (reason=%s, jid=%s, items=%s)",
                reason or "",
                self.jid_str,
                len(roster_keys),
            )

            for jid in roster_keys:
                bare = str(jid).split('/')[0]
                if not bare or bare == self.jid_str:
                    continue
                try:
                    item = self.client_roster[jid]
                except Exception as e:
                    logger.info("XMPP roster item jid=%s error=%s", bare, e)
                    continue

                try:
                    name = self._read_roster_field(item, 'name')
                    subscription = self._read_roster_field(item, 'subscription')
                    ask = self._read_roster_field(item, 'ask')
                    approved = self._read_roster_field(item, 'approved')
                    groups = self._read_roster_field(item, 'groups')

                    groups_str = None
                    try:
                        if isinstance(groups, (set, list, tuple)):
                            groups_str = ','.join([str(g) for g in groups])
                        elif groups is None:
                            groups_str = ''
                        else:
                            groups_str = str(groups)
                    except Exception:
                        groups_str = ''

                    logger.info(
                        "XMPP roster item jid=%s subscription=%s ask=%s approved=%s name=%s groups=%s raw=%s",
                        bare,
                        (str(subscription) if subscription is not None else ''),
                        (str(ask) if ask is not None else ''),
                        (str(approved) if approved is not None else ''),
                        (str(name) if name is not None else ''),
                        groups_str,
                        repr(item),
                    )
                except Exception as e:
                    logger.info("XMPP roster item jid=%s parse_error=%s raw=%s", bare, e, repr(item))

            logger.info("XMPP roster dump end (reason=%s)", reason or "")
        except Exception as e:
            logger.error(f"XMPP roster dump failed: {e}")

    def is_client_connected(self) -> bool:
        """Check if client is connected"""
        return self.is_connected()


class XMPPClientManager:
    """Singleton manager for XMPP client with automatic reconnection"""

    _instance = None
    _client: Optional[XMPPClient] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _stopping: bool = False
    _reconnect_task: Optional[asyncio.Task] = None

    # Reconnection parameters
    _initial_reconnect_delay = 5    # seconds
    _max_reconnect_delay = 300      # 5 minutes cap
    _current_reconnect_delay = 5

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_client(self) -> Optional[XMPPClient]:
        """Get XMPP client"""
        return self._client

    def _reset_reconnect_delay(self):
        """Reset reconnect delay after a successful connection"""
        self._current_reconnect_delay = self._initial_reconnect_delay

    async def start(self):
        """Start XMPP client"""
        self._stopping = False
        try:
            # Get database session
            db = get_db_sync()

            # Get first aichat_cfg record
            config = db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                logger.warning("No XMPP configuration found in database")
                db.close()
                return

            if not config.account or not config.password:
                logger.warning("XMPP account or password not configured")
                db.close()
                return

            # Create XMPP client
            self._client = XMPPClient(config.account, config.password, db)

            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
                self._loop = loop
            except RuntimeError:
                # No running loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop

            # Connect and process in background task
            logger.info(f"Connecting XMPP client: {config.account}")

            # Connect (non-blocking, connect() returns None)
            self._client.connect()
            # Create background task for processing with auto-reconnect
            self._reconnect_task = loop.create_task(self._run_client())
            logger.info("XMPP client connect initiated")
        except Exception as e:
            logger.error(f"Error starting XMPP client: {e}")

    async def _run_client(self):
        """Run XMPP client processing loop with automatic reconnection"""
        while not self._stopping:
            try:
                await self._client.disconnected
            except Exception as e:
                logger.error(f"XMPP client processing error: {e}")

            if self._stopping:
                logger.info("XMPP manager stopping, skip reconnect")
                break

            # Attempt reconnection with exponential backoff
            logger.info(f"Will attempt reconnect in {self._current_reconnect_delay}s")
            try:
                await asyncio.sleep(self._current_reconnect_delay)
            except asyncio.CancelledError:
                logger.info("Reconnect sleep cancelled")
                return

            if self._stopping:
                break

            # Increase delay for next attempt (exponential backoff)
            next_delay = min(self._current_reconnect_delay * 2, self._max_reconnect_delay)

            try:
                logger.info(f"Reconnecting XMPP client (backoff={self._current_reconnect_delay}s)...")
                self._current_reconnect_delay = next_delay
                self._client.connect()
                # Reset delay on successful session start via event callback
            except Exception as e:
                logger.error(f"Reconnect attempt failed: {e}")

        logger.info("XMPP _run_client loop exited")

    def on_session_start_reset(self):
        """Called when a session is successfully started to reset backoff"""
        self._reset_reconnect_delay()
        logger.info("Reconnect backoff reset after successful session start")

    async def stop(self):
        """Stop XMPP client gracefully"""
        self._stopping = True
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
        if self._client:
            self._client.disconnect()
            self._client = None
            logger.info("XMPP client stopped")
