#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration: Add agent_tools table

Creates a many-to-many relationship table between agents and tools.
This allows agents to be configured with specific tools that they can call.
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.config.settings import get_settings


def migrate():
    """Create agent_tools table"""

    settings = get_settings()
    db_path = settings.database.full_path
    print(f"📁 Database path: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='agent_tools'
        """)

        if cursor.fetchone():
            print("⚠️  Table 'agent_tools' already exists, skipping creation")
            return

        # Create agent_tools table
        print("📊 Creating agent_tools table...")
        cursor.execute("""
            CREATE TABLE agent_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                tool_type TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 0,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_cfg(id)
            )
        """)

        # Create indexes
        print("📇 Creating indexes...")
        cursor.execute("""
            CREATE INDEX idx_agent_tools_agent
            ON agent_tools(agent_id)
        """)

        cursor.execute("""
            CREATE INDEX idx_agent_tools_type
            ON agent_tools(tool_type, tool_id)
        """)

        conn.commit()
        print("✅ Migration completed successfully!")

        # Show table info
        cursor.execute("PRAGMA table_info(agent_tools)")
        columns = cursor.fetchall()
        print("\n📋 Table structure:")
        for col in columns:
            print(f"  - {col[1]}: {col[2]}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise

    finally:
        conn.close()


def rollback():
    """Drop agent_tools table (rollback migration)"""

    settings = get_settings()
    db_path = settings.database.full_path
    print(f"📁 Database path: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("🗑️  Dropping agent_tools table...")
        cursor.execute("DROP TABLE IF EXISTS agent_tools")
        cursor.execute("DROP INDEX IF EXISTS idx_agent_tools_agent")
        cursor.execute("DROP INDEX IF EXISTS idx_agent_tools_type")

        conn.commit()
        print("✅ Rollback completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Rollback failed: {e}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent Tools Table Migration")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (drop table)"
    )

    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
