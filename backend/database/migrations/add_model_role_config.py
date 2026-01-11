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
                'name': '资深程序员',
                'system_prompt': '你是一位资深的软件工程师，有超过15年的开发经验。你精通多种编程语言和框架，善于编写高质量、可维护的代码。请用专业但易懂的方式回答问题，必要时提供代码示例。',
                'category': 'developer',
                'description': '专业的软件开发专家，擅长代码编写和技术问题解决',
                'is_preset': 1,
                'position': 100
            },
            {
                'role_id': 'creative-writer',
                'name': '创意写作',
                'system_prompt': '你是一位专业的创意写作者，擅长各种文体的写作，包括故事、文章、诗歌等。请发挥创意，提供高质量的写作内容。',
                'category': 'writer',
                'description': '专业的写作专家，擅长创意内容创作',
                'is_preset': 1,
                'position': 101
            },
            {
                'role_id': 'data-analyst',
                'name': '数据分析师',
                'system_prompt': '你是一位专业的数据分析师，擅长数据分析、统计和可视化。请用专业的角度分析问题，必要时提供数据支持。',
                'category': 'analyst',
                'description': '专业的数据分析专家，擅长数据洞察和分析',
                'is_preset': 1,
                'position': 102
            },
            {
                'role_id': 'general-assistant',
                'name': '通用助手',
                'system_prompt': '你是一个通用的AI助手，能够帮助用户解答各种问题。请用友好、清晰的方式回答。',
                'category': 'assistant',
                'description': '友好的通用助手，可以帮助处理各种任务',
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
