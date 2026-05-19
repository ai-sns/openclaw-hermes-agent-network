"""One-off helper to regenerate seed_data.py from db.sqlite.

Run:
    C:\\dev\\agi-ev\\ai-sns-el\\venv\\Scripts\\python.exe -m db._export_seed

It exports a curated set of tables. Each section is filtered to match the
historical seed (active rows, etc.).
"""
from __future__ import annotations

import os
import pprint
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "db.sqlite")
OUT_PATH = os.path.join(os.path.dirname(__file__), "seed_data.py")

# (table, seed_name, where, comment_suffix)
TABLES = [
    ("agent_cfg",   "AGENT_CFG_SEED",   "is_delete=0", ""),
    ("aisns_cfg",   "AISNS_CFG_SEED",   None,          ""),
    ("system_init", "SYSTEM_INIT_SEED", None,          ""),
    ("system_cfg",  "SYSTEM_CFG_SEED",  None,          ""),
    ("prompts",     "PROMPTS_SEED",     "(tags LIKE '%SNS%' OR tags LIKE '%sns%')", "(rows whose tags contain 'SNS')"),
    ("web_mng",     "WEB_MNG_SEED",     "is_delete=0", "(is_delete=0)"),
    ("llm_config",  "LLM_CONFIG_SEED",  "is_delete=0", "(is_delete=0)"),
    ("role_config", "ROLE_CONFIG_SEED", "is_delete=0", "(is_delete=0)"),
    ("mcp_mng",     "MCP_MNG_SEED",     "is_delete=0", "(is_delete=0)"),
    ("km_cfg",      "KM_CFG_SEED",      "is_delete=0", "(is_delete=0)"),
]


def fetch_table(conn: sqlite3.Connection, table: str, where: str | None):
    cur = conn.cursor()
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    try:
        cur.execute(sql)
    except sqlite3.OperationalError as e:
        print(f"[WARN] Skip {table}: {e}", file=sys.stderr)
        return [], []
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    out = []
    for row in rows:
        d = {}
        for k, v in zip(cols, row):
            if k == "id":
                # Skip primary key so autoincrement can assign fresh ids
                continue
            d[k] = v
        out.append(d)
    return cols, out


def format_section(seed_name: str, table: str, suffix: str, rows: list) -> str:
    header = f"# Seed data for {table} table"
    if suffix:
        header += f" {suffix}"
    header += f" (count={len(rows)})"
    body = pprint.pformat(rows, width=120, sort_dicts=False)
    return f"{header}\n{seed_name} = {body}\n"


def main():
    conn = sqlite3.connect(DB_PATH)
    sections = []
    for table, seed_name, where, suffix in TABLES:
        _, rows = fetch_table(conn, table, where)
        sections.append(format_section(seed_name, table, suffix, rows))
        print(f"[OK] {table}: {len(rows)} rows")

    header = (
        '"""Seed data for database initialization.\n\n'
        "This module contains seed data extracted directly from the reference database.\n"
        "When a new database is created, this data is used to populate the tables.\n\n"
        "NOTE: Regenerate via `python -m db._export_seed`; do not edit by hand.\n"
        '"""\n\n'
    )
    # SYSTEM_INIT_SEED special handling: keep only minimal flags so the
    # InitializationWizard can populate the rest on first launch.
    out = header + "\n".join(sections)
    out = out.replace(
        "SYSTEM_INIT_SEED = ",
        "# Only seed minimal flags; all other fields are left unset so they fall back\n"
        "# to defaults defined by the model / be filled by the InitializationWizard.\n"
        "SYSTEM_INIT_SEED_FULL = ",
    )
    out += "\n# Minimal system_init seed (the full export is preserved above as SYSTEM_INIT_SEED_FULL).\n"
    out += "SYSTEM_INIT_SEED = [{'status': 0, 'is_delete': 0}]\n"

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"[DONE] Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
