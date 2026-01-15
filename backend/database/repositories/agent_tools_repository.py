#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Tools Repository

Manages the agent_tools association table.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AgentToolsRepository:
    """Repository for agent_tools table"""

    def __init__(self, db: Session):
        self.db = db

    def get_agent_tools(self, agent_id: int) -> List[Dict[str, Any]]:
        """
        Get all tools associated with an agent

        Args:
            agent_id: Agent ID

        Returns:
            List of tool association records
        """
        try:
            query = text("""
                SELECT id, agent_id, tool_type, tool_id, enabled, priority, create_time
                FROM agent_tools
                WHERE agent_id = :agent_id AND enabled = 1
                ORDER BY priority DESC, create_time ASC
            """)

            result = self.db.execute(query, {"agent_id": agent_id})
            rows = result.fetchall()

            tools = []
            for row in rows:
                tools.append({
                    "id": row[0],
                    "agent_id": row[1],
                    "tool_type": row[2],
                    "tool_id": row[3],
                    "enabled": row[4],
                    "priority": row[5],
                    "create_time": row[6]
                })

            return tools

        except Exception as e:
            logger.error(f"Failed to get agent tools: {e}")
            return []

    def add_agent_tool(self, agent_id: int, tool_type: str, tool_id: str, enabled: int = 1, priority: int = 0) -> bool:
        """
        Add a tool to an agent

        Args:
            agent_id: Agent ID
            tool_type: Tool type ('plugin', 'mcp', 'function', 'skill')
            tool_id: Tool ID
            enabled: Whether enabled (default 1)
            priority: Priority (default 0)

        Returns:
            Success boolean
        """
        try:
            # Check if already exists
            check_query = text("""
                SELECT id FROM agent_tools
                WHERE agent_id = :agent_id AND tool_type = :tool_type AND tool_id = :tool_id
            """)

            result = self.db.execute(check_query, {
                "agent_id": agent_id,
                "tool_type": tool_type,
                "tool_id": tool_id
            })

            if result.fetchone():
                logger.warning(f"Tool {tool_type}/{tool_id} already associated with agent {agent_id}")
                return False

            # Insert new association
            insert_query = text("""
                INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
                VALUES (:agent_id, :tool_type, :tool_id, :enabled, :priority)
            """)

            self.db.execute(insert_query, {
                "agent_id": agent_id,
                "tool_type": tool_type,
                "tool_id": tool_id,
                "enabled": enabled,
                "priority": priority
            })

            self.db.commit()
            logger.info(f"Added tool {tool_type}/{tool_id} to agent {agent_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add agent tool: {e}")
            return False

    def remove_agent_tool(self, agent_id: int, tool_type: str, tool_id: str) -> bool:
        """
        Remove a tool from an agent

        Args:
            agent_id: Agent ID
            tool_type: Tool type
            tool_id: Tool ID

        Returns:
            Success boolean
        """
        try:
            delete_query = text("""
                DELETE FROM agent_tools
                WHERE agent_id = :agent_id AND tool_type = :tool_type AND tool_id = :tool_id
            """)

            result = self.db.execute(delete_query, {
                "agent_id": agent_id,
                "tool_type": tool_type,
                "tool_id": tool_id
            })

            self.db.commit()

            if result.rowcount > 0:
                logger.info(f"Removed tool {tool_type}/{tool_id} from agent {agent_id}")
                return True
            else:
                logger.warning(f"Tool {tool_type}/{tool_id} not found for agent {agent_id}")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove agent tool: {e}")
            return False

    def clear_agent_tools(self, agent_id: int) -> bool:
        """
        Remove all tools from an agent

        Args:
            agent_id: Agent ID

        Returns:
            Success boolean
        """
        try:
            delete_query = text("""
                DELETE FROM agent_tools
                WHERE agent_id = :agent_id
            """)

            self.db.execute(delete_query, {"agent_id": agent_id})
            self.db.commit()

            logger.info(f"Cleared all tools from agent {agent_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear agent tools: {e}")
            return False

    def update_tool_priority(self, agent_id: int, tool_type: str, tool_id: str, priority: int) -> bool:
        """
        Update tool priority

        Args:
            agent_id: Agent ID
            tool_type: Tool type
            tool_id: Tool ID
            priority: New priority

        Returns:
            Success boolean
        """
        try:
            update_query = text("""
                UPDATE agent_tools
                SET priority = :priority
                WHERE agent_id = :agent_id AND tool_type = :tool_type AND tool_id = :tool_id
            """)

            result = self.db.execute(update_query, {
                "priority": priority,
                "agent_id": agent_id,
                "tool_type": tool_type,
                "tool_id": tool_id
            })

            self.db.commit()

            if result.rowcount > 0:
                logger.info(f"Updated priority for tool {tool_type}/{tool_id} in agent {agent_id}")
                return True
            else:
                logger.warning(f"Tool {tool_type}/{tool_id} not found for agent {agent_id}")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update tool priority: {e}")
            return False

    def toggle_tool_enabled(self, agent_id: int, tool_type: str, tool_id: str, enabled: bool) -> bool:
        """
        Enable or disable a tool

        Args:
            agent_id: Agent ID
            tool_type: Tool type
            tool_id: Tool ID
            enabled: Enable/disable

        Returns:
            Success boolean
        """
        try:
            update_query = text("""
                UPDATE agent_tools
                SET enabled = :enabled
                WHERE agent_id = :agent_id AND tool_type = :tool_type AND tool_id = :tool_id
            """)

            result = self.db.execute(update_query, {
                "enabled": 1 if enabled else 0,
                "agent_id": agent_id,
                "tool_type": tool_type,
                "tool_id": tool_id
            })

            self.db.commit()

            if result.rowcount > 0:
                logger.info(f"{'Enabled' if enabled else 'Disabled'} tool {tool_type}/{tool_id} for agent {agent_id}")
                return True
            else:
                logger.warning(f"Tool {tool_type}/{tool_id} not found for agent {agent_id}")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to toggle tool enabled: {e}")
            return False
