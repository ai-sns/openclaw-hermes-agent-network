"""
Migration: Add agent_id column to ai_chat_messages table
"""
import sqlite3
import os
from pathlib import Path

def migrate():
    """Add agent_id column to ai_chat_messages table"""
    # Get database path
    db_path = Path(__file__).parent.parent.parent.parent / 'db' / 'db.sqlite'

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(ai_chat_messages)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'agent_id' in columns:
            print("agent_id column already exists in ai_chat_messages table")
        else:
            # Add agent_id column
            print("Adding agent_id column to ai_chat_messages table...")
            cursor.execute("""
                ALTER TABLE ai_chat_messages
                ADD COLUMN agent_id INTEGER DEFAULT NULL
            """)
            conn.commit()
            print("✓ agent_id column added successfully")

        # Create index for better query performance
        print("Creating index on agent_id column...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_agent_id
            ON ai_chat_messages(agent_id)
        """)
        conn.commit()
        print("✓ Index created successfully")

        print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
