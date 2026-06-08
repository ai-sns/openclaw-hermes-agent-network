"""
A2A Server - Business card exchange logic.
Handles the exchange_business_card JSON-RPC method.
"""
import logging
from a2aserver.db import get_my_card, add_or_update_received_card, normalize_bare_jid

logger = logging.getLogger(__name__)


def exchange_business_card(their_card: dict, sender_jid: str = "") -> dict:
    """
    Process an incoming business card exchange request.
    Stores the sender's card, returns our own card.

    Args:
        their_card: The sender's business card data
        sender_jid: Optional XMPP JID of the sender

    Returns:
        Our own business card
    """
    # Store their card (upsert by bare JID)
    card_to_store = dict(their_card)
    sj = sender_jid or their_card.get("xmpp", "")
    card_to_store["sender_jid"] = normalize_bare_jid(sj)
    card_to_store["xmpp"] = normalize_bare_jid(card_to_store.get("xmpp", ""))
    row_id = add_or_update_received_card(card_to_store)
    logger.info("Stored received card id=%d from %s", row_id, sender_jid or "unknown")

    # Return our card
    my_card = get_my_card()
    # Remove internal fields
    my_card.pop("id", None)
    my_card.pop("updated_at", None)
    return my_card
