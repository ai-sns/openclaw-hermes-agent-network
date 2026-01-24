"""
Migration: Add agent_id column to aichat_cfg table
"""
import sqlite3
import os

def migrate():
    """Add agent_id column to aichat_cfg table"""
    db_path = os.path.join(os.path.dirname(__file__), '../../../db/db.sqlite')

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(aichat_cfg)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'agent_id' not in columns:
            print("Adding agent_id column to aichat_cfg table...")
            cursor.execute("ALTER TABLE aichat_cfg ADD COLUMN agent_id INTEGER")
            conn.commit()
            print("Successfully added agent_id column")
        else:
            print("agent_id column already exists")

        conn.close()
        return True
    except Exception as e:
        print("Error during migration: " + str(e))
        return False

if __name__ == "__main__":
    migrate()
