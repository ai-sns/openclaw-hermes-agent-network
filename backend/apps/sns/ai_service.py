# -*- coding: utf-8 -*-
"""
SNS AI Service - Provides AI chat service for the SNS module
"""
import logging
from typing import Optional
from backend.apps.sns.adapter.agent_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class SNSAIService:
    """SNS AI service class."""

    @staticmethod
    async def chat_with_agent(
        agent_identifier: str,
        message: str,
        mode: str = "ai"
    ) -> str:
        """
        Chat with an agent.

        Args:
            agent_identifier: Agent ID or name
            message: User message
            mode: Chat mode ("ai" or "friends")

        Returns:
            Agent reply
        """
        try:
            agent_adapter = AgentAdapter()
            agent = agent_adapter.get_agent_by_identifier(agent_identifier)

            if not agent:
                return f"Error: Agent '{agent_identifier}' not found"

            # Save original system prompt
            original_prompt = agent.role_config.get('system_prompt', '')

            # Update system prompt based on mode
            if mode == "ai":
                modified_prompt = "I am your AI assistant. " + original_prompt
            else:  # friends
                modified_prompt = "I am your friend. " + original_prompt

            # Temporarily override system prompt
            agent.role_config['system_prompt'] = modified_prompt

            try:
                # Call agent to chat
                reply = await agent_adapter.chat(
                    agent=agent,
                    message=message,
                    conversation_id=f"sns_{mode}",
                    use_memory=False,
                    use_knowledge_base=False,
                )
                return reply
            finally:
                # Restore original system prompt
                agent.role_config['system_prompt'] = original_prompt

        except Exception as e:
            logger.error(f"SNS AI chat failed: {e}", exc_info=True)
            return f"Error: {str(e)}"
