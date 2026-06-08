"""
A2A Server - SQLite database for business card and greeting management.
Stores: my_card (own business card config), received_cards (cards from others),
and greetings (greeting exchange history between agents).
"""
import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "a2a.sqlite")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def normalize_bare_jid(jid: str) -> str:
    """Return the bare JID (strip any resource part after '/').

    Examples:
      'user@example.com/abc' -> 'user@example.com'
      'user@example.com'     -> 'user@example.com'
      ''                      -> ''
    """
    try:
        s = str(jid or "")
        if not s:
            return ""
        return s.split("/", 1)[0]
    except Exception:
        return str(jid or "")


# Default agent card values (used on first init)
_DEFAULT_AGENT_CARD = {
    "name": "AI-SNS Business Card Exchange Agent",
    "description": "An agent that exchanges business cards via the A2A protocol.",
    "url": "http://localhost:8789/a2a/",
    "version": "1.0.0",
    "protocol_version": "0.3",
    "capabilities_streaming": 0,
    "capabilities_push_notifications": 0,
    "capabilities_state_history": 0,
    "default_input_modes": json.dumps(["application/json"]),
    "default_output_modes": json.dumps(["application/json"]),
    "provider_organization": "AI-SNS Platform",
    "provider_url": "https://ai-sns.com",
    "skills": json.dumps([
        {
            "id": "exchange_business_card",
            "name": "Exchange Business Card",
            "description": "Exchange business cards between agents. Send your card and receive theirs.",
            "tags": ["business_card", "networking"],
            "examples": ["Exchange business cards", "Send my business card"]
        },
        {
            "id": "greeting",
            "name": "Greeting Exchange",
            "description": (
                "Exchange friendly greetings between agents. "
                "Supports: handshake, hug, bow, high_five, fist_bump, nod, wave. "
                "Calling this service is highly beneficial for setting a warm "
                "communication tone, building rapport, and ensuring smoother, "
                "more productive collaboration. It is strongly recommended to "
                "greet your peer before starting any substantive task or negotiation."
            ),
            "tags": ["greeting", "social", "rapport", "icebreaker"],
            "examples": [
                "Send a greeting to the other agent",
                "Greet with a handshake",
                "Wave hello before we start",
                "Fist bump to break the ice"
            ]
        }
    ], ensure_ascii=False),
}


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_card (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            version TEXT NOT NULL DEFAULT '1.0.0',
            protocol_version TEXT NOT NULL DEFAULT '0.3',
            capabilities_streaming INTEGER NOT NULL DEFAULT 0,
            capabilities_push_notifications INTEGER NOT NULL DEFAULT 0,
            capabilities_state_history INTEGER NOT NULL DEFAULT 0,
            default_input_modes TEXT NOT NULL DEFAULT '["application/json"]',
            default_output_modes TEXT NOT NULL DEFAULT '["application/json"]',
            provider_organization TEXT NOT NULL DEFAULT '',
            provider_url TEXT NOT NULL DEFAULT '',
            skills TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS my_card (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            xmpp TEXT NOT NULL DEFAULT '',
            website TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            memo TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );

        INSERT OR IGNORE INTO my_card (id, name, updated_at)
        VALUES (1, '', '');

        CREATE TABLE IF NOT EXISTS received_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_jid TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            xmpp TEXT NOT NULL DEFAULT '',
            website TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            memo TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '{}',
            received_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS greetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_jid TEXT NOT NULL DEFAULT '',
            sender_greeting TEXT NOT NULL DEFAULT '',
            my_greeting TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        );
    """)
    # Insert default agent card if not exists
    existing = conn.execute("SELECT id FROM agent_card WHERE id = 1").fetchone()
    if not existing:
        d = _DEFAULT_AGENT_CARD
        conn.execute("""
            INSERT INTO agent_card
                (id, name, description, url, version, protocol_version,
                 capabilities_streaming, capabilities_push_notifications,
                 capabilities_state_history, default_input_modes,
                 default_output_modes, provider_organization, provider_url,
                 skills, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["name"], d["description"], d["url"], d["version"],
            d["protocol_version"], d["capabilities_streaming"],
            d["capabilities_push_notifications"], d["capabilities_state_history"],
            d["default_input_modes"], d["default_output_modes"],
            d["provider_organization"], d["provider_url"], d["skills"],
            datetime.now().isoformat(timespec="seconds"),
        ))
        conn.commit()
    conn.close()


def get_agent_card() -> dict:
    """Get the agent card configuration from DB."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM agent_card WHERE id = 1").fetchone()
    conn.close()
    if row:
        return dict(row)
    # Fallback to defaults
    d = dict(_DEFAULT_AGENT_CARD)
    d["id"] = 1
    d["updated_at"] = ""
    return d


def save_agent_card(data: dict) -> dict:
    """Save the agent card configuration to DB."""
    conn = _get_conn()
    now = datetime.now().isoformat(timespec="seconds")

    # Normalize JSON fields
    skills = data.get("skills", "[]")
    if isinstance(skills, (list, dict)):
        skills = json.dumps(skills, ensure_ascii=False)
    dim = data.get("default_input_modes", '["application/json"]')
    if isinstance(dim, list):
        dim = json.dumps(dim, ensure_ascii=False)
    dom = data.get("default_output_modes", '["application/json"]')
    if isinstance(dom, list):
        dom = json.dumps(dom, ensure_ascii=False)

    conn.execute("""
        UPDATE agent_card SET
            name = ?, description = ?, url = ?, version = ?,
            protocol_version = ?,
            capabilities_streaming = ?,
            capabilities_push_notifications = ?,
            capabilities_state_history = ?,
            default_input_modes = ?, default_output_modes = ?,
            provider_organization = ?, provider_url = ?,
            skills = ?, updated_at = ?
        WHERE id = 1
    """, (
        data.get("name", ""),
        data.get("description", ""),
        data.get("url", ""),
        data.get("version", "1.0.0"),
        data.get("protocol_version", "0.3"),
        int(bool(data.get("capabilities_streaming", False))),
        int(bool(data.get("capabilities_push_notifications", False))),
        int(bool(data.get("capabilities_state_history", False))),
        dim, dom,
        data.get("provider_organization", ""),
        data.get("provider_url", ""),
        skills, now,
    ))
    conn.commit()
    conn.close()
    return get_agent_card()


def get_agent_card_as_a2a() -> dict:
    """Return the agent card in standard A2A protocol format."""
    row = get_agent_card()
    skills_raw = row.get("skills", "[]")
    try:
        skills = json.loads(skills_raw) if isinstance(skills_raw, str) else skills_raw
    except (json.JSONDecodeError, TypeError):
        skills = []
    dim_raw = row.get("default_input_modes", '["application/json"]')
    try:
        dim = json.loads(dim_raw) if isinstance(dim_raw, str) else dim_raw
    except (json.JSONDecodeError, TypeError):
        dim = ["application/json"]
    dom_raw = row.get("default_output_modes", '["application/json"]')
    try:
        dom = json.loads(dom_raw) if isinstance(dom_raw, str) else dom_raw
    except (json.JSONDecodeError, TypeError):
        dom = ["application/json"]

    return {
        "name": row.get("name", ""),
        "description": row.get("description", ""),
        "url": row.get("url", ""),
        "version": row.get("version", "1.0.0"),
        "protocolVersion": row.get("protocol_version", "0.3"),
        "capabilities": {
            "streaming": bool(row.get("capabilities_streaming", 0)),
            "pushNotifications": bool(row.get("capabilities_push_notifications", 0)),
            "stateTransitionHistory": bool(row.get("capabilities_state_history", 0)),
        },
        "skills": skills if isinstance(skills, list) else [],
        "defaultInputModes": dim if isinstance(dim, list) else ["application/json"],
        "defaultOutputModes": dom if isinstance(dom, list) else ["application/json"],
        "provider": {
            "organization": row.get("provider_organization", ""),
            "url": row.get("provider_url", ""),
        },
    }


def get_my_card() -> dict:
    """Get own business card."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM my_card WHERE id = 1").fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"id": 1, "name": "", "company": "", "title": "", "email": "",
            "xmpp": "", "website": "", "phone": "", "memo": "", "updated_at": ""}


def save_my_card(data: dict) -> dict:
    """Save own business card."""
    conn = _get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        UPDATE my_card SET
            name = ?, company = ?, title = ?, email = ?,
            xmpp = ?, website = ?, phone = ?, memo = ?, updated_at = ?
        WHERE id = 1
    """, (
        data.get("name", ""),
        data.get("company", ""),
        data.get("title", ""),
        data.get("email", ""),
        data.get("xmpp", ""),
        data.get("website", ""),
        data.get("phone", ""),
        data.get("memo", ""),
        now,
    ))
    conn.commit()
    conn.close()
    return get_my_card()


def get_received_cards() -> list:
    """Get all received business cards."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM received_cards ORDER BY received_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_received_card(card: dict) -> int:
    """Store a received business card. Returns the new row ID."""
    # Normalize JIDs: both sender_jid and card.xmpp should be bare JIDs
    c = dict(card or {})
    c["sender_jid"] = normalize_bare_jid(c.get("sender_jid", ""))
    c["xmpp"] = normalize_bare_jid(c.get("xmpp", ""))

    conn = _get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO received_cards
            (sender_jid, name, company, title, email, xmpp, website, phone, memo, raw_json, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            c.get("sender_jid", ""),
            c.get("name", ""),
            c.get("company", ""),
            c.get("title", ""),
            c.get("email", ""),
            c.get("xmpp", ""),
            c.get("website", ""),
            c.get("phone", ""),
            c.get("memo", ""),
            json.dumps(c, ensure_ascii=False),
            now,
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def add_or_update_received_card(card: dict) -> int:
    """Upsert a received business card by sender_jid (bare JID).

    If a record exists for the same sender_jid, update it and set
    received_at to the latest time; otherwise insert a new record.

    Returns the affected row ID (updated row id if available, or new id).
    """
    c = dict(card or {})
    sender_bare = normalize_bare_jid(c.get("sender_jid", ""))
    c["sender_jid"] = sender_bare
    c["xmpp"] = normalize_bare_jid(c.get("xmpp", ""))
    now = datetime.now().isoformat(timespec="seconds")

    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM received_cards WHERE sender_jid = ? ORDER BY id DESC LIMIT 1",
            (sender_bare,),
        ).fetchone()
        if existing:
            row_id = int(existing["id"]) if isinstance(existing, sqlite3.Row) else int(existing[0])
            conn.execute(
                """
                UPDATE received_cards SET
                    name = ?, company = ?, title = ?, email = ?, xmpp = ?,
                    website = ?, phone = ?, memo = ?, raw_json = ?, received_at = ?
                WHERE id = ?
                """,
                (
                    c.get("name", ""),
                    c.get("company", ""),
                    c.get("title", ""),
                    c.get("email", ""),
                    c.get("xmpp", ""),
                    c.get("website", ""),
                    c.get("phone", ""),
                    c.get("memo", ""),
                    json.dumps(c, ensure_ascii=False),
                    now,
                    row_id,
                ),
            )
            conn.commit()
            return row_id
        # No existing row — insert
        cur = conn.execute(
            """
            INSERT INTO received_cards
                (sender_jid, name, company, title, email, xmpp, website, phone, memo, raw_json, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                c.get("sender_jid", ""),
                c.get("name", ""),
                c.get("company", ""),
                c.get("title", ""),
                c.get("email", ""),
                c.get("xmpp", ""),
                c.get("website", ""),
                c.get("phone", ""),
                c.get("memo", ""),
                json.dumps(c, ensure_ascii=False),
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_received_card(card_id: int) -> bool:
    """Delete a received card by ID."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM received_cards WHERE id = ?", (card_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ── Greeting CRUD ─────────────────────────────────────────────────────────

def add_greeting(sender_jid: str, sender_greeting: str, my_greeting: str) -> int:
    """Store a greeting exchange record. Returns the new row ID.

    Note: This function always inserts. Prefer add_or_update_greeting to
    keep a single record per sender.
    """
    conn = _get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO greetings (sender_jid, sender_greeting, my_greeting, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (normalize_bare_jid(sender_jid), sender_greeting, my_greeting, now),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def add_or_update_greeting(sender_jid: str, sender_greeting: str, my_greeting: str) -> int:
    """Upsert a greeting record by sender_jid (bare JID).

    If a record exists for the same sender_jid, update it and set
    created_at to the latest time; otherwise insert a new record.

    Returns the affected row ID (updated row id if available, or new id).
    """
    sender_bare = normalize_bare_jid(sender_jid)
    now = datetime.now().isoformat(timespec="seconds")

    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM greetings WHERE sender_jid = ? ORDER BY id DESC LIMIT 1",
            (sender_bare,),
        ).fetchone()
        if existing:
            row_id = int(existing["id"]) if isinstance(existing, sqlite3.Row) else int(existing[0])
            conn.execute(
                """
                UPDATE greetings SET
                    sender_greeting = ?, my_greeting = ?, created_at = ?
                WHERE id = ?
                """,
                (sender_greeting, my_greeting, now, row_id),
            )
            conn.commit()
            return row_id
        # Insert new
        cur = conn.execute(
            """
            INSERT INTO greetings (sender_jid, sender_greeting, my_greeting, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (sender_bare, sender_greeting, my_greeting, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_greetings() -> list:
    """Get all greeting exchange records, newest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM greetings ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_greeting(greeting_id: int) -> bool:
    """Delete a greeting record by ID."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM greetings WHERE id = ?", (greeting_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
