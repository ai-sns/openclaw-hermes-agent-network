"""Fetch an A2A agent card from a given endpoint URL.

Input (stdin JSON):
    url  - The A2A endpoint URL.

Output (stdout JSON):
    ok     - True if a card was fetched successfully.
    card   - The raw agent card JSON text (max 2000 chars).
    source - "direct" or "well_known".
    error  - Error description when both attempts fail.
"""

import json
import sys
from urllib.parse import urlparse

try:
    import urllib.request
    import ssl
except ImportError:
    pass

MAX_CARD_LENGTH = 2000
TIMEOUT_SECONDS = 10


def _try_get(url: str) -> str:
    """GET a URL and return the response body if it looks like JSON."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET", headers={
        "Accept": "application/json",
        "User-Agent": "AI-SNS-Skill/1.0",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS, context=ctx) as resp:
        body = resp.read().decode("utf-8", errors="replace").strip()
        if body and (body.startswith("{") or body.startswith("[")):
            return body[:MAX_CARD_LENGTH]
    return ""


def main():
    raw = sys.stdin.read() or "{}"
    try:
        params = json.loads(raw)
    except Exception:
        params = {}

    url = (params.get("url") or "").strip()
    if not url:
        print(json.dumps({"ok": False, "card": "", "source": "", "error": "url parameter is required"}, ensure_ascii=False))
        return

    # Attempt 1: direct GET on the endpoint URL
    try:
        card = _try_get(url)
        if card:
            print(json.dumps({"ok": True, "card": card, "source": "direct", "error": ""}, ensure_ascii=False))
            return
    except Exception as e1:
        pass  # fall through to well-known

    # Attempt 2: fallback to /.well-known/agent.json
    try:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        well_known = f"{origin}/.well-known/agent.json"
        card = _try_get(well_known)
        if card:
            print(json.dumps({"ok": True, "card": card, "source": "well_known", "error": ""}, ensure_ascii=False))
            return
    except Exception as e2:
        pass

    print(json.dumps({
        "ok": False,
        "card": "",
        "source": "",
        "error": f"Both direct and well-known fetch failed for: {url}"
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
