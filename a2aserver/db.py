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


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
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
    conn.close()


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
    conn = _get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute("""
        INSERT INTO received_cards
            (sender_jid, name, company, title, email, xmpp, website, phone, memo, raw_json, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        card.get("sender_jid", ""),
        card.get("name", ""),
        card.get("company", ""),
        card.get("title", ""),
        card.get("email", ""),
        card.get("xmpp", ""),
        card.get("website", ""),
        card.get("phone", ""),
        card.get("memo", ""),
        json.dumps(card, ensure_ascii=False),
        now,
    ))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


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
    """Store a greeting exchange record. Returns the new row ID."""
    conn = _get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute("""
        INSERT INTO greetings (sender_jid, sender_greeting, my_greeting, created_at)
        VALUES (?, ?, ?, ?)
    """, (sender_jid, sender_greeting, my_greeting, now))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


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
