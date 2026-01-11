# -*- coding: utf-8 -*-
"""
Chat module - SSE streaming functionality
"""
import json
import logging
import httpx
from typing import AsyncGenerator, Optional

from db.DBFactory import add_AIChatMessages, query_AIChatMessages_All

logger = logging.getLogger(__name__)


class StreamingService:
    """Service for handling SSE streaming chat"""

    @staticmethod
    async def stream_chat(
        messages: list,
        ai_config: dict,
        model: str,
        temperature: float,
        max_tokens: int,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator:
        """
        Stream chat responses using Server-Sent Events

        Args:
            messages: List of chat messages
            ai_config: AI configuration dictionary
            model: Model name
            temperature: Temperature parameter
            max_tokens: Max tokens parameter
            conversation_id: Conversation ID for saving messages

        Yields:
            SSE event dictionaries
        """
        # Accumulate the complete assistant response
        accumulated_content = ""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                api_url = f"{ai_config['api_base'].rstrip('/')}/chat/completions"

                request_data = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                logger.info(f"Streaming chat request to: {api_url}")
                logger.info(f"Using model: {model}")

                async with client.stream(
                    'POST',
                    api_url,
                    json=request_data,
                    headers={
                        'Authorization': f"Bearer {ai_config['api_key']}",
                        'Content-Type': 'application/json'
                    }
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"API error: {response.status_code} - {error_text.decode()}")
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "error": f"HTTP {response.status_code}: {error_text.decode()}"
                            })
                        }
                        return

                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        chunk_str = chunk.decode('utf-8')
                        buffer += chunk_str

                        lines = buffer.split('\n')
                        buffer = lines.pop() if lines else ""

                        for line in lines:
                            line = line.strip()
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    # Save messages to database if conversation_id is provided
                                    if conversation_id and accumulated_content:
                                        try:
                                            # Extract user message (last user message in the list)
                                            user_message = ""
                                            for msg in reversed(messages):
                                                if msg.get('role') == 'user':
                                                    user_message = msg.get('content', '')
                                                    break

                                            # Check if this is a new conversation
                                            existing_messages = query_AIChatMessages_All(conversation_id=conversation_id)
                                            is_new_conversation = not existing_messages or len(existing_messages) == 0

                                            # Only set title and is_first for new conversations
                                            if is_new_conversation:
                                                title = user_message[:50] + "..." if len(user_message) > 50 else user_message
                                                is_first = True
                                            else:
                                                title = None
                                                is_first = False

                                            # Save user message
                                            add_AIChatMessages(
                                                conversation_id=conversation_id,
                                                flag=0,  # 0 = user message
                                                title=title,
                                                content=user_message,
                                                owner_name="User",
                                                owner_account="user",
                                                friend_name="AI Assistant",
                                                friend_account="assistant",
                                                is_first=is_first
                                            )

                                            # Save assistant message
                                            add_AIChatMessages(
                                                conversation_id=conversation_id,
                                                flag=1,  # 1 = AI message
                                                title=None,
                                                content=accumulated_content,
                                                owner_name="AI Assistant",
                                                owner_account="assistant",
                                                friend_name="User",
                                                friend_account="user",
                                                is_first=False
                                            )

                                            logger.info(f"Saved chat messages to database for conversation {conversation_id}")
                                        except Exception as e:
                                            logger.error(f"Failed to save messages to database: {e}")

                                    yield {
                                        "event": "done",
                                        "data": json.dumps({"status": "completed"})
                                    }
                                    return
                                try:
                                    parsed = json.loads(data)
                                    choices = parsed.get('choices', [])
                                    if choices and len(choices) > 0:
                                        content = choices[0].get('delta', {}).get('content', '')
                                        if content:
                                            accumulated_content += content  # Accumulate content
                                            yield {
                                                "event": "message",
                                                "data": json.dumps({"content": content})
                                            }
                                except json.JSONDecodeError as e:
                                    logger.debug(f"JSON parse error: {e} for line: {line}")
                                    continue

                    # Process remaining buffer
                    if buffer.strip():
                        line = buffer.strip()
                        if line.startswith('data: ') and line[6:] != '[DONE]':
                            try:
                                parsed = json.loads(line[6:])
                                choices = parsed.get('choices', [])
                                if choices and len(choices) > 0:
                                    content = choices[0].get('delta', {}).get('content', '')
                                    if content:
                                        accumulated_content += content  # Accumulate content
                                        yield {
                                            "event": "message",
                                            "data": json.dumps({"content": content})
                                        }
                            except json.JSONDecodeError:
                                pass

                    # Save messages to database if conversation_id is provided
                    if conversation_id and accumulated_content:
                        try:
                            # Extract user message (last user message in the list)
                            user_message = ""
                            for msg in reversed(messages):
                                if msg.get('role') == 'user':
                                    user_message = msg.get('content', '')
                                    break

                            # Check if this is a new conversation
                            existing_messages = query_AIChatMessages_All(conversation_id=conversation_id)
                            is_new_conversation = not existing_messages or len(existing_messages) == 0

                            # Only set title and is_first for new conversations
                            if is_new_conversation:
                                title = user_message[:50] + "..." if len(user_message) > 50 else user_message
                                is_first = True
                            else:
                                title = None
                                is_first = False

                            # Save user message
                            add_AIChatMessages(
                                conversation_id=conversation_id,
                                flag=0,  # 0 = user message
                                title=title,
                                content=user_message,
                                owner_name="User",
                                owner_account="user",
                                friend_name="AI Assistant",
                                friend_account="assistant",
                                is_first=is_first
                            )

                            # Save assistant message
                            add_AIChatMessages(
                                conversation_id=conversation_id,
                                flag=1,  # 1 = AI message
                                title=None,
                                content=accumulated_content,
                                owner_name="AI Assistant",
                                owner_account="assistant",
                                friend_name="User",
                                friend_account="user",
                                is_first=False
                            )

                            logger.info(f"Saved chat messages to database for conversation {conversation_id}")
                        except Exception as e:
                            logger.error(f"Failed to save messages to database: {e}")

                    yield {
                        "event": "done",
                        "data": json.dumps({"status": "completed"})
                    }

        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
