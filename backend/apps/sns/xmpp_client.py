"""XMPP Client Manager for SNS Module"""
import logging
import asyncio
import slixmpp
from typing import Optional
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
        self.add_event_handler("disconnected", self.on_disconnected)
        self.add_event_handler("connection_failed", self.on_connection_failed)

        # Register plugins
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0199', {'keepalive': False})  # XMPP Ping (we manage our own heartbeat)
        self.register_plugin('xep_0363')  # HTTP File Upload

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

        # Reset reconnect backoff on successful session
        try:
            manager = XMPPClientManager.get_instance()
            manager.on_session_start_reset()
        except Exception:
            pass

        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

    async def on_message(self, msg):
        """Handle incoming messages"""
        if msg['type'] in ('chat', 'normal'):
            from_jid = str(msg['from']).split('/')[0]
            body = msg['body']

            if (not from_jid) or ('@' not in from_jid):
                logger.warning("Ignoring message from invalid XMPP account: %s", from_jid)
                return

            logger.info(f"Received message from {from_jid}: {body}")

            # Forward to AI Social Engine
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

            # Save to database
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
                    # handled1 in await _social_engine_instance.receiveMessage(event)
                    # await self.broadcast_new_message({
                    #     'type': 'map_chat_message',
                    #     'from_user': from_jid,
                    #     'to_user': config.account,
                    #     'content': body,
                    #     'timestamp': message.create_time.isoformat() if message.create_time else None
                    # })
            except Exception as e:
                logger.error(f"Error saving message to database: {e}")

    async def broadcast_new_message(self, message_data: dict):
        """Broadcast new message to all WebSocket clients"""
        try:
            # Import here to avoid circular dependency
            from backend.shared.websocket_manager import manager as ws_manager
            await ws_manager.broadcast(message_data)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")

    async def on_presence_subscribe(self, presence):
        """Handle subscription requests"""
        from_jid = str(presence['from'])
        logger.info(f"Subscription request from {from_jid}")

        # Auto-accept subscription requests
        self.send_presence(pto=from_jid, ptype='subscribed')
        self.send_presence(pto=from_jid, ptype='subscribe')

    async def on_roster_update(self, event):
        """Handle roster updates"""
        logger.info("Roster updated")
        groups = self.client_roster.groups()

        for group in groups:
            for jid in groups[group]:
                self.update_roster_local(jid)

    def update_roster_local(self, jid: str):
        """Update local database with roster information"""
        if jid == self.jid_str:
            return

        if (not jid) or ('@' not in str(jid)):
            logger.warning("Skipping roster update for invalid XMPP account: %s", jid)
            return

        try:
            roster_item = self.client_roster[jid]
            account = jid

            # Handle both dict and object access patterns for RosterItem
            if isinstance(roster_item, dict):
                nick_name = roster_item.get('name', jid) or jid
                groups = ','.join(roster_item.get('groups', set())) if roster_item.get('groups') else ""
                subscription = roster_item.get('subscription', 'none') or 'none'
            else:
                # Access as object attributes
                nick_name = getattr(roster_item, 'name', jid) or jid
                groups_set = getattr(roster_item, 'groups', set())
                groups = ','.join(groups_set) if groups_set else ""
                subscription = getattr(roster_item, 'subscription', 'none') or 'none'

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

    def send_message_to_jid(self, to_jid: str, content: str):
        """Send a message"""
        self.send_presence()
        self.send_message(
            mto=to_jid,
            mbody=content,
            mtype='chat'
        )

    async def upload_and_send_file(self, to_jid: str, file_path: str, filename: str):
        """Upload file via XEP-0363 and send URL to recipient"""
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

            # Send URL to recipient
            file_message = f"📎 File: {filename}\n{url}"
            self.send_message_to_jid(to_jid, file_message)

            return url
        except Exception as e:
            logger.error(f"Error uploading file via XEP-0363: {e}")
            raise

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
