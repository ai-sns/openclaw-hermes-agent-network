# -*- coding: utf-8 -*-
"""Database migration: Add LLM and Role configuration tables."""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from backend.database.base import SQL_DATABASE_URL


def upgrade():
    """Create llm_config and role_config tables."""
    engine = create_engine(SQL_DATABASE_URL)

    print("Starting database migration...")

    with engine.begin() as conn:
        # Create llm_config table
        print("Creating llm_config table...")
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS llm_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            provider VARCHAR(50) NOT NULL,
            plugin_id VARCHAR(100),
            api_endpoint VARCHAR(500),
            api_key TEXT,
            model_name VARCHAR(100),
            temperature FLOAT DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 2048,
            top_p FLOAT DEFAULT 1.0,
            frequency_penalty FLOAT DEFAULT 0.0,
            presence_penalty FLOAT DEFAULT 0.0,
            stream BOOLEAN DEFAULT 1,
            custom_params TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0,
            position INTEGER DEFAULT 9999,
            creator VARCHAR(100),
            is_delete BOOLEAN DEFAULT 0,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP
        )
        """))

        # Create role_config table
        print("Creating role_config table...")
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS role_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            display_name VARCHAR(100),
            system_prompt TEXT NOT NULL,
            greeting_message TEXT,
            role_type VARCHAR(50),
            category VARCHAR(50),
            avatar VARCHAR(200),
            description TEXT,
            tags VARCHAR(200),
            is_active BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0,
            is_preset BOOLEAN DEFAULT 0,
            position INTEGER DEFAULT 9999,
            usage_count INTEGER DEFAULT 0,
            creator VARCHAR(100),
            is_delete BOOLEAN DEFAULT 0,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP
        )
        """))

        # Insert preset roles
        print("Inserting preset roles...")
        preset_roles = [
            {
                'role_id': 'senior-developer',
                'name': 'Senior Developer',
                'system_prompt': 'You are a senior software engineer with over 15 years of development experience. You are proficient in multiple programming languages and frameworks, and excel at writing high-quality, maintainable code. Answer questions in a professional but easy-to-understand way, and provide code examples when necessary.',
                'category': 'developer',
                'description': 'Professional software development expert, skilled in coding and solving technical problems',
                'is_preset': 1,
                'position': 100
            },
            {
                'role_id': 'creative-writer',
                'name': 'Creative Writer',
                'system_prompt': 'You are a professional creative writer skilled in various styles of writing, including stories, articles, poetry, and more. Use your creativity to produce high-quality writing.',
                'category': 'writer',
                'description': 'Professional writing expert, skilled in creating creative content',
                'is_preset': 1,
                'position': 101
            },
            {
                'role_id': 'data-analyst',
                'name': 'Data Analyst',
                'system_prompt': 'You are a professional data analyst skilled in data analysis, statistics, and visualization. Analyze problems from a professional perspective and provide data support when necessary.',
                'category': 'analyst',
                'description': 'Professional data analysis expert, skilled in data insights and analysis',
                'is_preset': 1,
                'position': 102
            },
            {
                'role_id': 'general-assistant',
                'name': 'General Assistant',
                'system_prompt': 'You are a general AI assistant who can help users answer a wide variety of questions. Respond in a friendly and clear manner.',
                'category': 'assistant',
                'description': 'Friendly general assistant that can help with various tasks',
                'is_preset': 1,
                'is_default': 1,
                'position': 0
            }
        ]

        for role in preset_roles:
            conn.execute(text("""
            INSERT OR IGNORE INTO role_config
            (role_id, name, display_name, system_prompt, role_type, category, description,
             is_preset, is_active, is_default, position)
            VALUES
            (:role_id, :name, :name, :system_prompt, 'preset', :category, :description,
             :is_preset, 1, :is_default, :position)
            """), {
                'role_id': role['role_id'],
                'name': role['name'],
                'system_prompt': role['system_prompt'],
                'category': role['category'],
                'description': role.get('description', ''),
                'is_preset': role['is_preset'],
                'is_default': role.get('is_default', 0),
                'position': role['position']
            })

        print("Migration completed successfully!")


def downgrade():
    """Drop llm_config and role_config tables."""
    engine = create_engine(SQL_DATABASE_URL)

    print("Rolling back migration...")

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS llm_config"))
        conn.execute(text("DROP TABLE IF EXISTS role_config"))
        print("Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Database migration for LLM and Role config')
    parser.add_argument('action', choices=['upgrade', 'downgrade'],
                        help='Migration action: upgrade or downgrade')

    args = parser.parse_args()

    if args.action == 'upgrade':
        upgrade()
    else:
        downgrade()
