# -*- coding: utf-8 -*-
"""
Chat module - Service layer
"""
import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml

from db.DBFactory import (
    query_AiChatCfg_All,
    add_AiChatCfg,
    query_AIChatMessages_All as query_AIChatMessages,
    add_AIChatMessages as add_AIChatMessage
)

logger = logging.getLogger(__name__)

# Agent instances management
agent_instances: Dict[str, Any] = {}


class ChatService:
    """Service for managing chat functionality"""

    @staticmethod
    def load_ai_config_from_file():
        """Load AI configuration from config file"""
        config_file = Path(__file__).parent.parent.parent.parent / 'ai_config.yaml'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    ai_config = config.get('ai', {})
                    return {
                        "api_base": ai_config.get('api_base', 'https://api.openai.com/v1'),
                        "api_key": ai_config.get('api_key', ''),
                        "model": ai_config.get('model', 'gpt-4o-mini'),
                        "temperature": ai_config.get('temperature', 1.0),
                        "max_tokens": ai_config.get('max_tokens', 4096)
                    }
            except Exception as e:
                logger.warning(f"Failed to load AI config from file: {e}")
        return None

    @staticmethod
    def get_ai_config():
        """
        Get AI configuration
        Priority: Database > Environment Variables > Config File
        """
        # 1. Try to load from database
        try:
            configs = query_AiChatCfg_All(is_delete=0)
            if configs and len(configs) > 0:
                cfg = configs[0]
                api_key = getattr(cfg, 'api_key', '')
                if api_key and api_key.strip():
                    logger.info("Using AI config from database")
                    return {
                        "api_base": getattr(cfg, 'api_base', 'https://api.openai.com/v1'),
                        "api_key": api_key,
                        "model": getattr(cfg, 'model', 'gpt-4o-mini'),
                        "temperature": getattr(cfg, 'temperature', 1.0),
                        "max_tokens": getattr(cfg, 'max_tokens', 4096)
                    }
        except Exception as e:
            logger.warning(f"Failed to load AI config from database: {e}")

        # 2. Try to load from environment variables
        if os.environ.get('OPENAI_API_KEY'):
            logger.info("Using AI config from environment variables")
            return {
                "api_base": os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1'),
                "api_key": os.environ.get('OPENAI_API_KEY'),
                "model": os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                "temperature": float(os.environ.get('OPENAI_TEMPERATURE', '1.0')),
                "max_tokens": int(os.environ.get('OPENAI_MAX_TOKENS', '4096'))
            }

        # 3. Try to load from config file
        file_config = ChatService.load_ai_config_from_file()
        if file_config and file_config.get('api_key'):
            logger.info("Using AI config from ai_config.yaml")
            return file_config

        # 4. Default configuration
        logger.error("No valid AI config found!")
        return {
            "api_base": 'https://api.openai.com/v1',
            "api_key": '',
            "model": 'gpt-4o-mini',
            "temperature": 1.0,
            "max_tokens": 4096
        }

    @staticmethod
    def get_all_ai_chat_configs() -> List[Dict[str, Any]]:
        """Get all AI chat configurations"""
        configs = query_AiChatCfg_All(is_delete=0)
        result = []
        for cfg in configs:
            result.append({
                "id": cfg.id,
                "name": getattr(cfg, 'name', ''),
                "model": getattr(cfg, 'model', 'gpt-4'),
                "api_base": getattr(cfg, 'api_base', ''),
                "temperature": getattr(cfg, 'temperature', 0.7)
            })
        return result

    @staticmethod
    def create_ai_chat_config(**kwargs) -> int:
        """Create AI chat configuration"""
        config_id = add_AiChatCfg(**kwargs)
        return config_id

    @staticmethod
    async def send_chat_message(
        agent_id: int,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send chat message and get response"""
        # Get or create Agent instance
        agent_key = f"agent_{agent_id}"
        if agent_key not in agent_instances:
            from Agent import Agent
            agent_instances[agent_key] = Agent()

        agent = agent_instances[agent_key]

        # Send message and get reply
        response = await asyncio.to_thread(
            agent.chat,
            message,
            conversation_id
        )

        # Save messages to database
        add_AIChatMessage(
            agent_id=agent_id,
            role="user",
            content=message,
            conversation_id=conversation_id
        )
        add_AIChatMessage(
            agent_id=agent_id,
            role="assistant",
            content=response,
            conversation_id=conversation_id
        )

        return {
            "response": response,
            "conversation_id": conversation_id
        }

    @staticmethod
    def get_chat_history(
        agent_id: int,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get chat history"""
        messages = query_AIChatMessages(
            limit=None,  # 获取所有消息
            agent_id=agent_id,
            conversation_id=conversation_id
        )
        result = []
        for msg in messages:
            result.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": str(msg.timestamp) if hasattr(msg, 'timestamp') else None
            })
        return result

    @staticmethod
    def get_conversations(limit: int = 50, agent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation list (ordered by last message time)

        Args:
            limit: Maximum number of conversations to return
            agent_id: Filter by agent ID (optional)

        Returns:
            List of conversations with title and last message time
        """
        try:
            # Query all first messages (is_first=True) to get conversations
            query_params = {'is_first': True, 'is_delete': False}
            if agent_id is not None:
                query_params['agent_id'] = agent_id
            # 使用 _All 版本获取所有记录（已通过别名导入为query_AIChatMessages），传递limit参数
            conversations = query_AIChatMessages(limit=limit, **query_params)

            # Group by conversation_id and get latest timestamp
            conversation_dict = {}
            for msg in conversations:
                conv_id = msg.conversation_id
                if conv_id not in conversation_dict:
                    conversation_dict[conv_id] = {
                        "conversation_id": conv_id,
                        "agent_id": getattr(msg, 'agent_id', None),  # 添加agent_id字段
                        "title": msg.title or msg.content[:50],
                        "last_message_time": msg.create_time,
                        "first_message": msg.content[:100]
                    }
                else:
                    # Update if this message is newer
                    if msg.create_time > conversation_dict[conv_id]["last_message_time"]:
                        conversation_dict[conv_id]["last_message_time"] = msg.create_time

            # Convert to list and sort by last message time (descending)
            result = list(conversation_dict.values())
            result.sort(key=lambda x: x["last_message_time"], reverse=True)

            # Limit results
            return result[:limit]
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []

    @staticmethod
    def get_conversation_messages(conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages in a conversation

        Args:
            conversation_id: The conversation ID

        Returns:
            List of messages in chronological order
        """
        try:
            messages = query_AIChatMessages(
                limit=None,  # 获取所有消息
                conversation_id=conversation_id,
                is_delete=False
            )

            result = []
            for msg in messages:
                # Determine role from flag (0=user, 1=assistant)
                role = "user" if msg.flag == 0 else "assistant"

                result.append({
                    "id": msg.id,
                    "role": role,
                    "content": msg.content,
                    "create_time": str(msg.create_time) if hasattr(msg, 'create_time') else None
                })

            # Sort by create_time
            result.sort(key=lambda x: x.get("create_time", ""))

            return result
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return []

