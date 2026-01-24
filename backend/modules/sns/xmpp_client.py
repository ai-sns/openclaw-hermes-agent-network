"""XMPP Client Manager for SNS Module"""
import logging
import asyncio
import slixmpp
from typing import Optional
from sqlalchemy.orm import Session
from backend.config.database import get_db_sync
from backend.database.models.chat import AiChatCfg, AIFriend, AIChatMessages

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

        # Register plugins
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0199')  # XMPP Ping
        self.register_plugin('xep_0363')  # HTTP File Upload

        # Heartbeat
        self.heartbeat_interval = 3  # 3 seconds like ConnectorThread
        self.heartbeat_task = None

    async def on_session_start(self, event):
        """Handle session start"""
        logger.info(f"XMPP session started for {self.jid_str}")
        self.send_presence()
        await self.get_roster()

        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

    async def on_message(self, msg):
        """Handle incoming messages"""
        if msg['type'] in ('chat', 'normal'):
            from_jid = str(msg['from']).split('/')[0]
            body = msg['body']

            logger.info(f"Received message from {from_jid}: {body}")

            # Forward to AI Social Engine
            try:
                from backend.modules.sns.service_async import _social_engine_instance
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
                    message = AIChatMessages(
                        conversation_id=f"{config.account}_{from_jid}",
                        flag=1,  # 1=receive
                        content=body,
                        owner_account=config.account,
                        friend_account=from_jid,
                        owner_name=config.nickname or config.account,
                        friend_name=from_jid
                    )
                    self.db.add(message)
                    self.db.commit()

                    # Update friend's new_message_flag and last_message_time
                    from datetime import datetime
                    friend = self.db.query(AIFriend).filter(
                        AIFriend.account == from_jid,
                        AIFriend.owner_sns_account == config.account
                    ).first()

                    if friend:
                        friend.new_message_flag = True
                        friend.last_message_time = datetime.now()
                        self.db.commit()

                    # Broadcast message to chatWindow (Electron)
                    await self.broadcast_new_message({
                        'type': 'new_message',
                        'data': {
                            'id': message.id,
                            'from_account': from_jid,
                            'content': body,
                            'flag': 1,
                            'create_time': message.create_time.isoformat() if message.create_time else None
                        }
                    })

                    # Also broadcast to map (map_chat_message format)
                    await self.broadcast_new_message({
                        'type': 'map_chat_message',
                        'from_user': from_jid,
                        'to_user': config.account,
                        'content': body,
                        'timestamp': message.create_time.isoformat() if message.create_time else None
                    })
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

            # Check if friend exists
            friend = self.db.query(AIFriend).filter(
                AIFriend.account == account,
                AIFriend.owner_sns_account == owner_account
            ).first()

            if friend:
                # Update existing friend
                friend.nick_name = nick_name
                friend.groups = groups
                friend.subscription = subscription
            else:
                # Add new friend
                friend = AIFriend(
                    account=account,
                    nick_name=nick_name,
                    groups=groups,
                    owner_sns_account=owner_account,
                    subscription=subscription
                )
                self.db.add(friend)

            self.db.commit()
        except Exception as e:
            logger.error(f"Error updating roster for {jid}: {e}")

    async def heartbeat(self):
        """Send periodic pings to keep connection alive"""
        while True:
            try:
                await self['xep_0199'].ping()
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            await asyncio.sleep(self.heartbeat_interval)

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
    """Singleton manager for XMPP client"""

    _instance = None
    _client: Optional[XMPPClient] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_client(self) -> Optional[XMPPClient]:
        """Get XMPP client"""
        return self._client

    async def start(self):
        """Start XMPP client"""
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

            # Connect (non-blocking)
            if self._client.connect():
                # Create background task for processing
                loop.create_task(self._run_client())
                logger.info("XMPP client connected successfully")
            else:
                logger.error("Failed to connect XMPP client")
        except Exception as e:
            logger.error(f"Error starting XMPP client: {e}")

    async def _run_client(self):
        """Run XMPP client processing loop"""
        try:
            await self._client.process(forever=False)
        except Exception as e:
            logger.error(f"Error in XMPP client processing: {e}")

    async def stop(self):
        """Stop XMPP client"""
        if self._client:
            self._client.disconnect()
            self._client = None
            logger.info("XMPP client stopped")
