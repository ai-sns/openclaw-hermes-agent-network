import re


_INQUIRY_PREFIX = "[AISNS_INT_003_INQUIRY]"
_SEPARATOR = "__AISNS_INT_SEPARATOR__"


def format_internal_xmpp_message_for_storage(raw: str) -> str:
    """Format internal protocol messages for storage/display.

    This function is intentionally display-focused and should not be used for
    business logic routing.

    Rules:
    - Inquiry: [AISNS_INT_003_INQUIRY]xxxxx -> 💬💲xxxxx
    - Pay: AISNS_INT_001_PAY_SEND_START ... trad__AISNS_INT_SEPARATOR__price ... END -> 💰✔️price
    - Good: AISNS_INT_002_GOOD_SEND_START ... trad__AISNS_INT_SEPARATOR__text ... END -> 🤝📦text

    If no rule matches, the original string is returned.
    """

    s = "" if raw is None else str(raw)

    if s.startswith(_INQUIRY_PREFIX):
        return f"💬💲{s[len(_INQUIRY_PREFIX):]}"

    pay_match = re.search(r"AISNS_INT_001_PAY_SEND_START(.*?)AISNS_INT_001_PAY_SEND_END", s, re.DOTALL)
    if pay_match:
        payload = (pay_match.group(1) or "").strip()
        parts = payload.split(_SEPARATOR)
        price = (parts[1] if len(parts) > 1 else "").strip()
        return f"💰✔️{price}"

    good_match = re.search(r"AISNS_INT_002_GOOD_SEND_START(.*?)AISNS_INT_002_GOOD_SEND_END", s, re.DOTALL)
    if good_match:
        payload = (good_match.group(1) or "").strip()
        parts = payload.split(_SEPARATOR)
        text = (parts[1] if len(parts) > 1 else "").strip()
        return f"🤝📦{text}"

    return s
