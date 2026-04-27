# -*- coding: utf-8 -*-
"""
Chat module - SSE streaming functionality
"""
import json
import logging
import httpx
from typing import AsyncGenerator, Optional

from runtime.shared.llm_endpoints import normalize_openai_base_url, normalize_provider
from runtime.shared.claude_client import ClaudeClient

from db.DBFactory import add_AIChatMessages, query_AIChatMessages_All
from runtime.shared.llm_log_writer import (
    new_request_id,
    log_llm_request,
    log_llm_response,
    log_llm_stream_chunk,
    log_llm_error,
)

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

        request_id = new_request_id()

        try:
            provider = normalize_provider(str(ai_config.get('provider') or ''))

            if provider == 'claude':
                client = ClaudeClient(api_key=str(ai_config.get('api_key') or ''), api_endpoint=str(ai_config.get('api_base') or ''))
                system_prompt = ""
                anthropic_messages = []
                if isinstance(messages, list):
                    for m in messages:
                        if not isinstance(m, dict):
                            continue
                        role = (m.get('role') or '').strip().lower()
                        if role == 'system':
                            system_prompt = (system_prompt + "\n\n" + str(m.get('content') or '')).strip() if system_prompt else str(m.get('content') or '')
                        elif role in ('user', 'assistant'):
                            anthropic_messages.append({"role": role, "content": str(m.get('content') or '')})

                try:
                    log_llm_request(
                        request_id=request_id,
                        source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                        request_json={
                            "provider": "claude",
                            "model": model,
                            "system": system_prompt,
                            "messages": anthropic_messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                            "stream": True,
                        },
                    )
                except Exception:
                    pass

                gen, done_fut = client.stream(
                    model=model,
                    system=system_prompt,
                    messages=anthropic_messages,
                    tools=None,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                async for chunk in gen:
                    if chunk:
                        try:
                            log_llm_stream_chunk(
                                request_id=request_id,
                                source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                                stream_raw={"content": chunk},
                            )
                        except Exception:
                            pass
                        accumulated_content += chunk
                        yield {
                            "event": "message",
                            "data": json.dumps({"content": chunk})
                        }

                _final = await done_fut
                try:
                    log_llm_response(
                        request_id=request_id,
                        source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                        response_json={"status": "completed", "provider": provider},
                    )
                except Exception:
                    pass

            else:
                base_url = normalize_openai_base_url(str(ai_config.get('api_base') or ''))
                api_url = f"{base_url.rstrip('/')}/chat/completions"

                request_data = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                try:
                    log_llm_request(
                        request_id=request_id,
                        source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                        request_json=request_data,
                    )
                except Exception:
                    pass

                logger.info(f"Streaming chat request to: {api_url}")
                logger.info(f"Using model: {model}")

                async with httpx.AsyncClient(timeout=60.0) as client:
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
                            try:
                                log_llm_error(
                                    request_id=request_id,
                                    source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                                    error=error_text.decode(errors="ignore"),
                                )
                            except Exception:
                                pass
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
                                        try:
                                            log_llm_response(
                                                request_id=request_id,
                                                source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                                                response_json={"status": "completed"},
                                            )
                                        except Exception:
                                            pass
                                        break
                                    try:
                                        parsed = json.loads(data)
                                        try:
                                            log_llm_stream_chunk(
                                                request_id=request_id,
                                                source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                                                stream_raw=parsed,
                                            )
                                        except Exception:
                                            pass
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
                                    try:
                                        log_llm_stream_chunk(
                                            request_id=request_id,
                                            source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                                            stream_raw=parsed,
                                        )
                                    except Exception:
                                        pass
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
            try:
                log_llm_error(
                    request_id=request_id,
                    source="runtime.modules.chat.streaming.StreamingService.stream_chat",
                    error=e,
                )
            except Exception:
                pass
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
