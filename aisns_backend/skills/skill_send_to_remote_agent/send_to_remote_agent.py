"""
Send to Remote Agent Skill

Calls a remote agent via A2A JSON-RPC protocol (SendMessage method).
Resolves the agent by reading the first aisns_cfg record to get agent_id,
then looks up agent_cfg for the A2A endpoint URL. The xmpp_account,
trade_id, and description are all sent as message content to the remote agent.

Input (stdin JSON):
  xmpp_account - XMPP JID to include in the message content (optional)
  description  - Message content to send (required)
  trade_id     - Trade identifier to include in the message (optional)
  context_id   - A2A conversation context ID (optional, default "default")

Output (stdout JSON):
  ok         - bool
  reply      - Text response from the remote agent
  agent_name - Name of the resolved agent
  rpc_url    - The A2A endpoint URL that was called
  trade_id   - The trade_id included (if any)
  error      - Error message on failure
"""

import sys
import json
import sqlite3
import uuid
import urllib.request
import urllib.error
from pathlib import Path


def main():
    # Parse input params from stdin
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            _output(False, error="No input provided")
            return
        params = json.loads(raw)
    except json.JSONDecodeError as e:
        _output(False, error=f"Invalid JSON input: {e}")
        return

    xmpp_account = (params.get("xmpp_account") or "").strip()
    description = (params.get("description") or "").strip()
    trade_id = (params.get("trade_id") or "").strip()
    context_id = (params.get("context_id") or "default").strip()

    if not description:
        _output(False, error="'description' is required")
        return

    # Resolve agent: get agent_id from the first aisns_cfg record, then look up agent_cfg
    resolved_agent_id = _get_agent_id_from_first_aisns_cfg()
    if not resolved_agent_id:
        _output(False, error="No aisns_cfg record found or no agent_id linked in the first record")
        return

    agent = _get_agent_by_id(resolved_agent_id)
    if not agent:
        _output(False, error=f"Agent not found for agent_id={resolved_agent_id} (from first aisns_cfg record)")
        return

    agent_name = agent.get("name") or "Unknown"
    agent_type = (agent.get("agent_type") or "local").strip().lower()
    rpc_url = (agent.get("url") or "").strip()

    if agent_type not in ("remote", "remote agent", "remote_agent", "remoteagent"):
        _output(False, error=f"Agent '{agent_name}' is not a remote agent (type={agent_type})")
        return

    if not rpc_url:
        _output(False, error=f"Agent '{agent_name}' has no A2A endpoint URL configured")
        return

    # Normalize A2A RPC URL
    rpc_url = _normalize_a2a_rpc_url(rpc_url)

    # Build message text: include xmpp_account, trade_id, and description
    parts = []
    if xmpp_account:
        parts.append(f"XMPP Account: {xmpp_account}")
    if trade_id:
        parts.append(f"Trade ID: {trade_id}")
    parts.append(description)
    message_text = "\n".join(parts)

    # Build A2A JSON-RPC 2.0 payload
    rpc_id = str(uuid.uuid4())[:8]
    payload = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": "SendMessage",
        "params": {
            "stream": False,
            "message": {
                "contextId": context_id,
                "parts": [{"text": message_text}],
            },
        },
    }

    # Send the JSON-RPC request
    try:
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        # Replace localhost with 127.0.0.1 to avoid IPv6 issues on Windows
        fetch_url = rpc_url.replace("://localhost", "://127.0.0.1")
        req = urllib.request.Request(
            fetch_url,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": "localhost" if "localhost" in rpc_url else "",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_text = resp.read().decode("utf-8")

        resp_json = json.loads(resp_text)

    except urllib.error.HTTPError as e:
        resp_body = ""
        try:
            resp_body = e.read().decode("utf-8")[:1000]
        except Exception:
            pass
        _output(False, error=f"A2A HTTP {e.code}: {resp_body or e.reason}")
        return
    except urllib.error.URLError as e:
        _output(False, error=f"A2A URL error: {e.reason}")
        return
    except Exception as e:
        _output(False, error=f"A2A request failed: {e}")
        return

    # Check for JSON-RPC error
    if isinstance(resp_json, dict) and resp_json.get("error"):
        err = resp_json["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        _output(False, error=f"A2A JSON-RPC error: {msg}")
        return

    # Extract reply text from A2A response
    result_obj = (resp_json or {}).get("result", {})
    message_obj = (result_obj or {}).get("message", {})
    reply = _extract_text_from_a2a_message(message_obj)

    out = {
        "ok": True,
        "reply": reply,
        "agent_name": agent_name,
        "rpc_url": rpc_url,
    }
    if trade_id:
        out["trade_id"] = trade_id

    print(json.dumps(out, ensure_ascii=False))


# ── Database helpers ──────────────────────────────────────────────────────────

def _get_db_path():
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "db" / "db.sqlite"


def _parse_agent_row(row):
    """Parse an agent_cfg row into a dict with memo fields extracted."""
    if not row:
        return None

    name = row["name"] or ""
    memo_str = row["memo"] or ""

    extra = {}
    try:
        extra = json.loads(memo_str) if memo_str else {}
    except Exception:
        extra = {}

    return {
        "id": row["id"],
        "name": name,
        "agent_type": extra.get("agent_type", "local"),
        "url": extra.get("url", ""),
        "agent_card_url": extra.get("agent_card_url", ""),
    }


def _get_agent_id_from_first_aisns_cfg():
    """Get agent_id from the first aisns_cfg record."""
    db_path = _get_db_path()
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id FROM aisns_cfg ORDER BY id ASC LIMIT 1",
        )
        row = cursor.fetchone()
        conn.close()
        if row and row["agent_id"]:
            return int(row["agent_id"])
        return None
    except Exception:
        return None


def _get_agent_by_id(agent_id: int):
    """Look up an agent by its ID in agent_cfg."""
    db_path = _get_db_path()
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, memo FROM agent_cfg WHERE id = ? LIMIT 1",
            (agent_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return _parse_agent_row(row)
    except Exception:
        return None


# ── A2A helpers ───────────────────────────────────────────────────────────────

def _normalize_a2a_rpc_url(url: str) -> str:
    """Normalize A2A endpoint URL to ensure it ends with /rpc."""
    u = str(url or "").strip()
    if not u:
        return u
    if u.endswith("/rpc/"):
        return u[:-1]
    if u.endswith("/rpc"):
        return u
    return u.rstrip("/") + "/rpc"


def _extract_text_from_a2a_message(message_obj: dict) -> str:
    """Extract text content from an A2A message object."""
    if not isinstance(message_obj, dict):
        return ""

    parts = message_obj.get("parts")
    if not isinstance(parts, list):
        return ""

    texts = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        t = part.get("text")
        if isinstance(t, str) and t:
            texts.append(t)
            continue
        # Handle OpenAI-style wrapped response
        data = part.get("data")
        if not isinstance(data, dict):
            continue
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            continue
        choice0 = choices[0]
        if not isinstance(choice0, dict):
            continue
        msg = choice0.get("message")
        if isinstance(msg, dict):
            c = msg.get("content")
            if isinstance(c, str) and c:
                texts.append(c)

    return "\n".join(texts)


def _output(ok, error=""):
    """Write error result JSON to stdout."""
    out = {"ok": ok}
    if error:
        out["error"] = error
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
