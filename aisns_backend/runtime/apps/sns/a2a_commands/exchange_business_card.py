"""
Built-in ad-hoc command: Exchange Business Card.

Handles XEP-0050 ad-hoc command for business card exchange between peers.
Migrated from xmpp_a2a.py.
"""
import json
import logging
import sys
import os
from typing import Dict, Any

from runtime.apps.sns.a2a_commands.base import AdhocCommand, CommandContext

logger = logging.getLogger(__name__)

A2A_ADHOC_EXCHANGE_NODE = "urn:xmpp:a2a:cmd:exchange_business_card"


class ExchangeBusinessCardCommand(AdhocCommand):
    """Exchange business cards between XMPP peers via ad-hoc command."""

    node = A2A_ADHOC_EXCHANGE_NODE
    name = "Exchange Business Card"
    description = "Exchange business cards between agents. Send your card and receive theirs."
    form_fields = [
        {"var": "name", "type": "text-single", "label": "Name"},
        {"var": "company", "type": "text-single", "label": "Company"},
        {"var": "title", "type": "text-single", "label": "Title"},
        {"var": "email", "type": "text-single", "label": "Email"},
        {"var": "xmpp", "type": "text-single", "label": "XMPP"},
        {"var": "website", "type": "text-single", "label": "Website"},
        {"var": "phone", "type": "text-single", "label": "Phone"},
    ]

    _source = "builtin"

    async def handle_execute(self, iq, session, ctx: CommandContext) -> dict:
        """Stage 1: Return form requesting sender's business card."""
        try:
            form = ctx.make_form(ftype='form', title='Exchange Business Card')
            form.addField(var='name', ftype='text-single', label='Name', value='')
            form.addField(var='company', ftype='text-single', label='Company', value='')
            form.addField(var='title', ftype='text-single', label='Title', value='')
            form.addField(var='email', ftype='text-single', label='Email', value='')
            form.addField(var='xmpp', ftype='text-single', label='XMPP', value='')
            form.addField(var='website', ftype='text-single', label='Website', value='')
            form.addField(var='phone', ftype='text-single', label='Phone', value='')

            session['payload'] = form
            session['next'] = None  # Will be wired by registry
            session['has_next'] = True
            session['allow_complete'] = True
            return session

        except Exception as e:
            logger.error("Error in exchange command handler: %s", e)
            session['notes'] = [('error', f'Internal error: {e}')]
            return session

    async def handle_submit(self, payload, session, ctx: CommandContext) -> dict:
        """Stage 2: Process submitted card and return our own card."""
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
            my_card = self._do_exchange(their_card, sender_jid)

            # Build response form with our card
            result_form = ctx.make_form(ftype='result', title='Business Card Exchange Result')
            for key in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone'):
                result_form.addField(
                    var=key, ftype='text-single',
                    label=key.capitalize(),
                    value=my_card.get(key, ''),
                )

            session['payload'] = result_form
            session['next'] = None
            session['has_next'] = False
            return session

        except Exception as e:
            logger.error("Error processing exchange submission: %s", e)
            session['notes'] = [('error', f'Processing error: {e}')]
            return session

    @staticmethod
    def _do_exchange(their_card: Dict[str, Any], sender_jid: str) -> Dict[str, Any]:
        """Perform the card exchange via a2aserver module."""
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
            from a2aserver.business_card import exchange_business_card
            return exchange_business_card(their_card, sender_jid=sender_jid)
        except Exception as e:
            logger.error("Failed to process card exchange: %s", e)
            return _load_my_business_card_fallback()


def _load_my_business_card_fallback() -> Dict[str, Any]:
    """Load own business card as fallback when exchange fails."""
    try:
        # 6 dirname() calls (see _do_exchange)
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
        logger.warning("Failed to load business card fallback: %s", e)
        return {}
