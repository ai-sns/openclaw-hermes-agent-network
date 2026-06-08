"""
A2A Server - Greeting exchange logic.
Handles the greeting JSON-RPC method for agent-to-agent social interaction.

Supported greeting types:
  handshake, hug, bow, high_five, fist_bump, nod, wave

When a greeting is received, the service randomly picks a greeting type
to respond with, stores both the incoming and outgoing greetings in the
database, and returns the response greeting to the caller.
"""
import random
import logging
from a2aserver.db import add_or_update_greeting, normalize_bare_jid

logger = logging.getLogger(__name__)

GREETING_TYPES = [
    "handshake",
    "hug",
    "bow",
    "high_five",
    "fist_bump",
    "nod",
    "wave",
]


def random_greeting() -> str:
    """Return a random greeting type from the supported list."""
    return random.choice(GREETING_TYPES)


def exchange_greeting(sender_jid: str, sender_greeting: str = "") -> dict:
    """
    Process an incoming greeting request.

    If the sender did not specify a greeting type, one is chosen randomly.
    A random response greeting is always generated. Both are stored in DB.

    Args:
        sender_jid: The XMPP JID (or identifier) of the sender.
        sender_greeting: The greeting type sent by the caller (optional).

    Returns:
        dict with keys:
          - sender_jid: who sent the greeting
          - sender_greeting: the greeting type they used
          - my_greeting: the greeting type we responded with
          - message: a human-readable description of the exchange
    """
    # If caller did not specify, pick one at random
    if not sender_greeting or sender_greeting not in GREETING_TYPES:
        sender_greeting = random_greeting()

    my_greeting = random_greeting()

    # Persist to database (upsert per bare JID)
    row_id = add_or_update_greeting(normalize_bare_jid(sender_jid), sender_greeting, my_greeting)
    logger.info(
        "Greeting exchange id=%d: %s sent '%s', replied '%s'",
        row_id, sender_jid or "unknown", sender_greeting, my_greeting,
    )

    return {
        "sender_jid": sender_jid,
        "sender_greeting": sender_greeting,
        "my_greeting": my_greeting,
        "message": (
            f"Received a {sender_greeting} from {sender_jid or 'you'}, "
            f"responded with a {my_greeting}!"
        ),
    }
