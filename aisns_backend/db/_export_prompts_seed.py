"""One-off helper to regenerate ONLY the PROMPTS_SEED block in seed_data.py
from db.sqlite, leaving all other *_SEED sections untouched.

Run:
    C:\\dev\\agi-ev\\ai-sns-el\\venv\\Scripts\\python.exe -m db._export_prompts_seed

Filter matches db/_export_seed.py: rows whose tags contain 'SNS' (case-insensitive).
"""
from __future__ import annotations

import os
import pprint
import re
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "db.sqlite")
OUT_PATH = os.path.join(os.path.dirname(__file__), "seed_data.py")

WHERE = "(tags LIKE '%SNS%' OR tags LIKE '%sns%')"
SECTION_NAME = "PROMPTS_SEED"
SECTION_HEADER_PREFIX = "# Seed data for prompts table"


def fetch_prompts(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.cursor()
    sql = f"SELECT * FROM prompts WHERE {WHERE}"
    try:
        cur.execute(sql)
    except sqlite3.OperationalError as e:
        print(f"[ERR] cannot read prompts: {e}", file=sys.stderr)
        sys.exit(1)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    out: list[dict] = []
    for row in rows:
        d: dict = {}
        for k, v in zip(cols, row):
            if k == "id":
                # Skip primary key so autoincrement can assign fresh ids
                continue
            d[k] = v
        out.append(d)
    return out


def format_section(rows: list[dict]) -> str:
    header = (
        f"{SECTION_HEADER_PREFIX} (rows whose tags contain 'SNS') (count={len(rows)})"
    )
    body = pprint.pformat(rows, width=120, sort_dicts=False)
    return f"{header}\n{SECTION_NAME} = {body}\n"


def replace_prompts_section(src: str, new_section: str) -> str:
    # Match from the section header comment line up to (but not including) the
    # next "# Seed data for" header or end-of-file. This keeps every other
    # *_SEED block intact.
    pattern = re.compile(
        r"^# Seed data for prompts table[^\n]*\n"
        r"PROMPTS_SEED\s*=\s*\[.*?\}\]\s*\n(?:\r?\n)?",
        re.MULTILINE | re.DOTALL,
    )
    if not pattern.search(src):
        print("[ERR] PROMPTS_SEED block not found in seed_data.py", file=sys.stderr)
        sys.exit(2)
    # Ensure a blank line follows the section so it's visually separated from
    # the next # Seed data for ... block.
    if not new_section.endswith("\n"):
        new_section += "\n"
    if not new_section.endswith("\n\n"):
        new_section += "\n"
    # Use a callable replacement so that backslash sequences inside the
    # generated source (e.g. '\n' escapes inside string reprs) are NOT
    # interpreted by re.sub.
    return pattern.sub(lambda _m: new_section, src, count=1)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = fetch_prompts(conn)
    finally:
        conn.close()
    print(f"[OK] prompts: {len(rows)} rows")

    with open(OUT_PATH, "r", encoding="utf-8") as f:
        src = f.read()

    new_section = format_section(rows)
    updated = replace_prompts_section(src, new_section)

    if updated == src:
        print("[NOOP] PROMPTS_SEED unchanged")
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"[DONE] Updated PROMPTS_SEED in {OUT_PATH}")


if __name__ == "__main__":
    main()
