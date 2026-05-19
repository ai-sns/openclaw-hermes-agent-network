# -*- coding: utf-8 -*-
"""
Agent Instance - Independent Agent object instance
Each agent has its own LLM configuration, role, tools, knowledge bases, and memory
"""
import logging
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
import openai
from openai import AsyncOpenAI
import httpx

from runtime.shared.llm_endpoints import normalize_openai_base_url, normalize_provider
from runtime.shared.claude_client import ClaudeClient, build_tool_result_block

from .tool_executor import tool_executor
from .code_executor import CodeExecutor
from .tool_router import ToolRouter
from .tool_converter import ToolConverter
from runtime.modules.tools.tool_executor import get_tool_executor
from runtime.shared.llm_log_writer import (
    new_request_id,
    log_llm_request,
    log_llm_response,
    log_llm_stream_chunk,
    log_llm_error,
)

logger = logging.getLogger(__name__)


class AgentInstance:
    """
    Agent instance class - each agent is an independent object

    Attributes:
        agent_id: Agent ID
        name: Agent name
        description: Agent description
        llm_config: LLM configuration (api_endpoint, api_key, model_name, etc.)
        role_config: Role configuration (system_prompt, greeting, etc.)
        tools: List of available tools
        knowledge_bases: Associated knowledge bases
        memory: Conversation history memory
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        description: str = "",
        llm_config: Optional[Dict[str, Any]] = None,
        role_config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        knowledge_bases: Optional[List[Dict[str, Any]]] = None,
        plugins: Optional[List[str]] = None,
        enable_code_execution: bool = False
    ):
        """
        Initialize the agent instance

        Args:
            agent_id: Agent ID
            name: Agent name
            description: Agent description
            llm_config: LLM configuration dict
            role_config: Role configuration dict
            tools: Tool list
            knowledge_bases: Knowledge base list
            plugins: Plugin ID list
            enable_code_execution: Whether to enable code execution
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.llm_config = llm_config or {}
        self.role_config = role_config or {}
        self.tools = tools or []
        self.knowledge_bases = knowledge_bases or []
        self.plugins = plugins or []
        self.enable_code_execution = enable_code_execution

        self._provider = normalize_provider(self.llm_config.get('provider'))
        self._openai_client: Optional[AsyncOpenAI] = None
        self._claude_client: Optional[ClaudeClient] = None

        # Memory - stores conversation history
        self.memory: Dict[str, List[Dict[str, Any]]] = {}

        self._usage_cache: Dict[str, Dict[str, Any]] = {}

        # Initialize the OpenAI client
        self._init_llm_client()

        # Initialize code executor (if enabled)
        self.code_executor = None
        if self.enable_code_execution:
            self.code_executor = CodeExecutor()

        # Initialize tool router (for the new tool-calling system)
        self.tool_router = ToolRouter(get_tool_executor())
        self.tools_loaded = False
        self.db_tools = []  # Tools loaded from DB (OpenAI format)

        logger.info(f"Agent instance created: {self.name} (ID: {self.agent_id})")

    def _init_llm_client(self):
        """Initialize the LLM client."""
        try:
            self._provider = normalize_provider(self.llm_config.get('provider'))
            api_endpoint = self.llm_config.get('api_endpoint', 'https://api.openai.com/v1')
            api_key = self.llm_config.get('api_key', '')

            if not api_key:
                logger.warning(f"Agent {self.name} has no API key configured")
                self._openai_client = None
                self._claude_client = None
                return

            if self._provider == 'claude':
                self._openai_client = None
                self._claude_client = ClaudeClient(api_key=api_key, api_endpoint=api_endpoint)
                logger.info("LLM client initialized: provider=claude endpoint=%s", api_endpoint)
                return

            base_url = normalize_openai_base_url(api_endpoint)
            self._claude_client = None
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )

            logger.info("LLM client initialized: provider=%s endpoint=%s", self._provider, base_url)
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self._openai_client = None
            self._claude_client = None

    def _get_openai_compatible_chat_completions_url(self) -> str:
        api_endpoint = str(self.llm_config.get('api_endpoint', 'https://api.openai.com/v1') or '')
        base_url = normalize_openai_base_url(api_endpoint)
        return f"{base_url.rstrip('/')}/chat/completions"

    async def _httpx_stream_openai_compatible_chat_completions(
        self,
        *,
        request_json: Dict[str, Any],
        request_id: str,
        source: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        url = self._get_openai_compatible_chat_completions_url()
        api_key = str(self.llm_config.get('api_key') or '')

        try:
            extra_body = request_json.get('extra_body')
            if isinstance(extra_body, dict) and extra_body:
                merged = dict(request_json)
                merged.pop('extra_body', None)
                for k, v in extra_body.items():
                    if k not in merged:
                        merged[k] = v
                request_json = merged
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                'POST',
                url,
                json=request_json,
                headers={
                    'Authorization': f"Bearer {api_key}",
                    'Content-Type': 'application/json',
                },
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    try:
                        log_llm_error(request_id=request_id, source=source, error=f"HTTP {response.status_code}: {body.decode(errors='ignore')}")
                    except Exception:
                        pass
                    raise RuntimeError(f"HTTP {response.status_code}: {body.decode(errors='ignore')}")

                buffer = ""
                async for chunk in response.aiter_bytes():
                    try:
                        chunk_str = chunk.decode('utf-8', errors='ignore')
                    except Exception:
                        continue
                    buffer += chunk_str

                    lines = buffer.split('\n')
                    buffer = lines.pop() if lines else ""

                    for line in lines:
                        line = line.strip()
                        if not line.startswith('data: '):
                            continue
                        data = line[6:]
                        if data == '[DONE]':
                            try:
                                log_llm_response(request_id=request_id, source=source, response_json={"status": "completed"})
                            except Exception:
                                pass
                            return
                        parsed = json.loads(data)
                        try:
                            log_llm_stream_chunk(request_id=request_id, source=source, stream_raw=parsed)
                        except Exception:
                            pass
                        yield parsed

    async def _claude_chat(
        self,
        *,
        message: str,
        conversation_id: Optional[str],
        use_tools: bool,
        use_memory: bool,
        use_knowledge_base: bool,
        attachments_text: str,
        image_data_urls: Optional[List[str]],
        tool_choice: Optional[dict],
        show_token_usage: bool,
    ) -> str:
        if not self._claude_client:
            return "Error: LLM client is not configured"

        effective_use_tools = bool(use_tools)
        try:
            if isinstance(tool_choice, str) and tool_choice.strip().lower() == "none":
                effective_use_tools = False
        except Exception:
            pass

        if effective_use_tools and not self.tools_loaded:
            await self.load_tools_from_db()

        messages: List[Dict[str, Any]] = []

        system_prompt = self.get_system_prompt()
        if use_knowledge_base and self.knowledge_bases:
            kb_context = await self._search_knowledge_base(message)
            if kb_context:
                system_prompt += f"\n\nRelated knowledge base information:\n{kb_context}"

        messages.append({'role': 'system', 'content': system_prompt})

        if use_memory:
            history = self._get_conversation_memory(conversation_id)
            for msg in history:
                if msg['role'] in ['user', 'assistant']:
                    messages.append({'role': msg['role'], 'content': msg['content']})

        user_text = message
        if attachments_text:
            user_text += f"\n\nAttachment content:\n{attachments_text}"

        if image_data_urls:
            messages.append({'role': 'user', 'content': user_text})
        else:
            messages.append({'role': 'user', 'content': user_text})

        tools_openai = self._prepare_tools_schema() if effective_use_tools else []
        tools_anthropic = ClaudeClient.openai_tools_to_anthropic(tools_openai) if tools_openai else []
        system_text, anthropic_messages = ClaudeClient.openai_messages_to_anthropic(messages)

        thinking_cfg: Optional[Dict[str, Any]] = None
        output_cfg: Optional[Dict[str, Any]] = None
        if self.get_thinking_effort_enabled():
            mapped = self._map_effort_level(self.get_thinking_effort_level(), 'claude', self.get_model_name())
            if mapped:
                if self._is_claude_effort_model(self.get_model_name()):
                    output_cfg = {'effort': mapped}
                if self._is_claude_adaptive_model(self.get_model_name()):
                    thinking_cfg = {'type': 'adaptive'}

        try:
            max_rounds = 5
            reply = ""
            for _round in range(max_rounds):
                request_id = new_request_id()
                request_json = {
                    "provider": "claude",
                    "round": _round,
                    "model": self.get_model_name(),
                    "system": system_text,
                    "messages": anthropic_messages,
                    "tools": tools_anthropic if effective_use_tools and tools_anthropic else None,
                    "tool_choice": tool_choice if effective_use_tools else None,
                    "max_tokens": self.get_max_tokens(),
                    "temperature": self.get_temperature(),
                    "thinking": thinking_cfg,
                    "output_config": output_cfg,
                }
                try:
                    log_llm_request(
                        request_id=request_id,
                        source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat",
                        request_json=request_json,
                    )
                except Exception:
                    pass

                try:
                    result = await self._claude_client.create(
                        model=self.get_model_name(),
                        system=system_text,
                        messages=anthropic_messages,
                        tools=tools_anthropic if effective_use_tools and tools_anthropic else None,
                        tool_choice=tool_choice,
                        max_tokens=self.get_max_tokens(),
                        temperature=self.get_temperature(),
                        thinking=thinking_cfg,
                        output_config=output_cfg,
                    )
                except Exception as e:
                    try:
                        log_llm_error(
                            request_id=request_id,
                            source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat",
                            error=e,
                        )
                    except Exception:
                        pass
                    raise

                reply = (result.get('text') or "")
                if show_token_usage and result.get('usage'):
                    self._set_last_usage(conversation_id, result.get('usage'))

                try:
                    raw_obj = result.get('raw')
                    if hasattr(raw_obj, 'model_dump'):
                        raw_dump = raw_obj.model_dump()
                    else:
                        raw_dump = getattr(raw_obj, '__dict__', str(raw_obj))
                    log_llm_response(
                        request_id=request_id,
                        source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat",
                        response_json={
                            "text": reply,
                            "tool_uses": result.get('tool_uses') or [],
                            "usage": result.get('usage'),
                            "raw": raw_dump,
                        },
                    )
                except Exception:
                    pass

                tool_uses = result.get('tool_uses') or []
                raw_result = result.get('raw')
                raw_stop_reason = getattr(raw_result, 'stop_reason', None)
                if raw_stop_reason is None and isinstance(raw_result, dict):
                    raw_stop_reason = raw_result.get('stop_reason')
                if effective_use_tools and not tool_uses and raw_stop_reason == 'tool_use' and _round < (max_rounds - 1):
                    logger.warning(
                        "Claude returned stop_reason=tool_use without tool_use blocks; retrying round",
                        extra={
                            'agent_id': self.agent_id,
                            'round': _round,
                            'model': self.get_model_name(),
                        },
                    )
                    anthropic_messages.append({'role': 'assistant', 'content': reply or ''})
                    anthropic_messages.append({'role': 'user', 'content': 'Please proceed by calling the appropriate tool now.'})
                    continue
                if not (effective_use_tools and tool_uses):
                    break

                assistant_blocks: List[Dict[str, Any]] = []
                if reply:
                    assistant_blocks.append({'type': 'text', 'text': reply})
                for tu in tool_uses:
                    try:
                        assistant_blocks.append({
                            'type': 'tool_use',
                            'id': tu.get('id'),
                            'name': tu.get('name'),
                            'input': tu.get('input') or {},
                        })
                    except Exception:
                        continue
                anthropic_messages.append({'role': 'assistant', 'content': assistant_blocks or ''})

                tool_result_blocks: List[Dict[str, Any]] = []
                for tu in tool_uses:
                    tool_name = tu.get('name')
                    tool_args = tu.get('input') or {}
                    tool_id = tu.get('id')
                    if not (tool_name and tool_id):
                        continue
                    tool_result = await self._execute_tool(tool_name, tool_args)
                    formatted_result = self._format_tool_result(tool_result)
                    tool_result_blocks.append(build_tool_result_block(tool_id, formatted_result))

                anthropic_messages.append({'role': 'user', 'content': tool_result_blocks})

            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', reply, conversation_id)

            return reply
        except Exception as e:
            logger.error(f"Claude chat failed: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def _claude_chat_stream(
        self,
        *,
        message: str,
        conversation_id: Optional[str],
        use_tools: bool,
        use_memory: bool,
        use_knowledge_base: bool,
        attachments_text: str,
        image_data_urls: Optional[List[str]],
        attachments_meta: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[dict],
        show_token_usage: bool,
    ) -> AsyncIterator[str]:
        if not self._claude_client:
            yield "Error: LLM client is not configured"
            return

        effective_use_tools = bool(use_tools)
        try:
            if isinstance(tool_choice, str) and tool_choice.strip().lower() == "none":
                effective_use_tools = False
        except Exception:
            pass

        if effective_use_tools and not self.tools_loaded:
            await self.load_tools_from_db()

        messages: List[Dict[str, Any]] = []

        system_prompt = self.get_system_prompt()
        if use_knowledge_base and self.knowledge_bases:
            kb_context = await self._search_knowledge_base(message)
            if kb_context:
                system_prompt += f"\n\nRelated knowledge base information:\n{kb_context}"

        messages.append({'role': 'system', 'content': system_prompt})

        if use_memory:
            history = self._get_conversation_memory(conversation_id)
            for msg in history:
                if msg['role'] in ['user', 'assistant']:
                    messages.append({'role': msg['role'], 'content': msg['content']})

        user_text = message
        if attachments_text:
            user_text += f"\n\nAttachment content:\n{attachments_text}"

        if image_data_urls:
            messages.append({'role': 'user', 'content': user_text})
        else:
            messages.append({'role': 'user', 'content': user_text})

        tools_openai = self._prepare_tools_schema() if effective_use_tools else []
        tools_anthropic = ClaudeClient.openai_tools_to_anthropic(tools_openai) if tools_openai else []
        system_text, anthropic_messages = ClaudeClient.openai_messages_to_anthropic(messages)

        thinking_cfg: Optional[Dict[str, Any]] = None
        output_cfg: Optional[Dict[str, Any]] = None
        if self.get_thinking_effort_enabled():
            mapped = self._map_effort_level(self.get_thinking_effort_level(), 'claude', self.get_model_name())
            if mapped:
                if self._is_claude_effort_model(self.get_model_name()):
                    output_cfg = {'effort': mapped}
                if self._is_claude_adaptive_model(self.get_model_name()):
                    thinking_cfg = {'type': 'adaptive'}

        try:
            full_reply = ""
            max_rounds = 5
            round_idx = 0
            while round_idx < max_rounds:
                request_id = new_request_id()
                request_json = {
                    "provider": "claude",
                    "round": round_idx,
                    "model": self.get_model_name(),
                    "system": system_text,
                    "messages": anthropic_messages,
                    "tools": tools_anthropic if effective_use_tools and tools_anthropic else None,
                    "tool_choice": tool_choice if effective_use_tools else None,
                    "max_tokens": self.get_max_tokens(),
                    "temperature": self.get_temperature(),
                    "stream": True,
                    "thinking": thinking_cfg,
                    "output_config": output_cfg,
                }
                try:
                    log_llm_request(
                        request_id=request_id,
                        source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat_stream",
                        request_json=request_json,
                    )
                except Exception:
                    pass

                try:
                    gen, done_fut = self._claude_client.stream(
                        model=self.get_model_name(),
                        system=system_text,
                        messages=anthropic_messages,
                        tools=tools_anthropic if effective_use_tools and tools_anthropic else None,
                        tool_choice=tool_choice,
                        max_tokens=self.get_max_tokens(),
                        temperature=self.get_temperature(),
                        thinking=thinking_cfg,
                        output_config=output_cfg,
                    )
                except Exception as e:
                    try:
                        log_llm_error(
                            request_id=request_id,
                            source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat_stream",
                            error=e,
                        )
                    except Exception:
                        pass
                    raise

                round_text = ""
                async for chunk in gen:
                    round_text += chunk
                    full_reply += chunk
                    try:
                        log_llm_stream_chunk(
                            request_id=request_id,
                            source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat_stream",
                            stream_raw={"type": "text_delta", "text": chunk, "round": round_idx},
                        )
                    except Exception:
                        pass
                    yield chunk

                try:
                    result = await done_fut
                except Exception as e:
                    try:
                        log_llm_error(
                            request_id=request_id,
                            source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat_stream",
                            error=e,
                        )
                    except Exception:
                        pass
                    raise

                if show_token_usage and result.get('usage'):
                    self._set_last_usage(conversation_id, result.get('usage'))

                try:
                    raw_obj = result.get('raw')
                    if hasattr(raw_obj, 'model_dump'):
                        raw_dump = raw_obj.model_dump()
                    else:
                        raw_dump = getattr(raw_obj, '__dict__', str(raw_obj))
                    log_llm_response(
                        request_id=request_id,
                        source="runtime.modules.agent.agent_instance.AgentInstance._claude_chat_stream",
                        response_json={
                            "text": result.get('text') or "",
                            "tool_uses": result.get('tool_uses') or [],
                            "usage": result.get('usage'),
                            "raw": raw_dump,
                        },
                    )
                except Exception:
                    pass

                tool_uses = result.get('tool_uses') or []
                raw_result = result.get('raw')
                raw_stop_reason = getattr(raw_result, 'stop_reason', None)
                if raw_stop_reason is None and isinstance(raw_result, dict):
                    raw_stop_reason = raw_result.get('stop_reason')
                if effective_use_tools and not tool_uses and raw_stop_reason == 'tool_use' and round_idx < (max_rounds - 1):
                    logger.warning(
                        "Claude streaming response returned stop_reason=tool_use without tool_use blocks; retrying round",
                        extra={
                            'agent_id': self.agent_id,
                            'round': round_idx,
                            'model': self.get_model_name(),
                        },
                    )
                    anthropic_messages.append({'role': 'assistant', 'content': round_text or ''})
                    anthropic_messages.append({'role': 'user', 'content': 'Please proceed by calling the appropriate tool now.'})
                    round_idx += 1
                    continue
                if not (effective_use_tools and tool_uses):
                    break

                assistant_blocks: List[Dict[str, Any]] = []
                if round_text:
                    assistant_blocks.append({'type': 'text', 'text': round_text})
                for tu in tool_uses:
                    try:
                        assistant_blocks.append({
                            'type': 'tool_use',
                            'id': tu.get('id'),
                            'name': tu.get('name'),
                            'input': tu.get('input') or {},
                        })
                    except Exception:
                        continue
                anthropic_messages.append({'role': 'assistant', 'content': assistant_blocks or ''})

                tool_result_blocks: List[Dict[str, Any]] = []
                for tu in tool_uses:
                    tool_name = tu.get('name')
                    tool_args = tu.get('input') or {}
                    tool_id = tu.get('id')
                    if not (tool_name and tool_id):
                        continue
                    tool_result = await self._execute_tool(tool_name, tool_args)
                    formatted_result = self._format_tool_result(tool_result)
                    tool_result_blocks.append(build_tool_result_block(tool_id, formatted_result))

                anthropic_messages.append({'role': 'user', 'content': tool_result_blocks})
                round_idx += 1

            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', full_reply, conversation_id)

            if show_token_usage and self.get_last_usage(conversation_id):
                pass
        except Exception as e:
            logger.error(f"Claude streaming chat failed: {e}", exc_info=True)
            yield f"Error: {str(e)}"
            return

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        base_prompt = self.role_config.get('system_prompt', 'You are a helpful AI assistant.')

        prompt = base_prompt

        # If the agent has tools, append tool usage guidance
        if self.db_tools or self.tools:
            tool_guidance = """

IMPORTANT Tool Usage Guidelines:
- You have access to tools that can perform actions (screenshots, calculations, weather queries, etc.)
- When a user requests an action that matches an available tool, ALWAYS call the tool first
- DO NOT say \"I cannot\" or \"I don't have the ability\" if a matching tool exists
- Wait for tool results before providing your final answer
- Base your response on the actual tool execution results, not assumptions"""

            prompt += tool_guidance

        # Inject DocSkill list (agent-filtered)
        try:
            from runtime.modules.skills_registry.service import get_docskills_service

            skills_prompt = get_docskills_service().build_prompt_for_agent(self.agent_id)
            if skills_prompt:
                prompt += skills_prompt
        except Exception:
            pass

        return prompt

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.llm_config.get('model_name', 'gpt-4o-mini')

    def get_temperature(self) -> float:
        """Get the temperature parameter."""
        return self.llm_config.get('temperature', 0.7)

    def get_max_tokens(self) -> int:
        """Get the max_tokens parameter."""
        return self.llm_config.get('max_tokens', 2048)

    def get_top_p(self) -> Optional[float]:
        v = self.llm_config.get('top_p', None)
        return None if v is None else float(v)

    def get_frequency_penalty(self) -> Optional[float]:
        v = self.llm_config.get('frequency_penalty', None)
        return None if v is None else float(v)

    def get_presence_penalty(self) -> Optional[float]:
        v = self.llm_config.get('presence_penalty', None)
        return None if v is None else float(v)

    def get_custom_params(self) -> Optional[Dict[str, Any]]:
        v = self.llm_config.get('custom_params', None)
        return v if isinstance(v, dict) else None

    def get_thinking_effort_enabled(self) -> bool:
        return bool(self.llm_config.get('thinking_effort_enabled', False))

    def get_thinking_effort_level(self) -> str:
        v = self.llm_config.get('thinking_effort_level', None)
        if not v:
            return 'medium'
        s = str(v).strip().lower()
        if s in {'minimal', 'low', 'medium', 'high', 'max'}:
            return s
        return 'medium'

    def _map_effort_level(self, level: str, provider: str, model_name: Optional[str] = None) -> Optional[str]:
        l = str(level or '').strip().lower()
        p = str(provider or '').strip().lower()
        model = str(model_name or '').strip().lower()
        if not l:
            return None

        if p == 'claude':
            if l == 'minimal':
                l = 'low'
            if l == 'max' and model and ('claude-opus-4-6' not in model):
                l = 'high'
            if l in {'low', 'medium', 'high', 'max'}:
                return l
            return None

        if p == 'gemini':
            if l in {'minimal', 'low', 'medium', 'high'}:
                return l
            if l == 'max':
                return 'high'
            return None

        if p in {'openai', 'custom'}:
            # `custom` is treated as OpenAI-compatible (e.g. DeepSeek, Qwen,
            # third-party gateways). The user explicitly opts into custom and
            # is responsible for backend compatibility, so we honor their
            # Thinking effort toggle and forward reasoning_effort verbatim.
            if l in {'minimal', 'low'}:
                return 'low'
            if l == 'medium':
                return 'medium'
            if l in {'high', 'max'}:
                return 'high'
            return None

        return None

    def _is_openai_reasoning_model(self, model_name: Optional[str]) -> bool:
        """Return True only for OpenAI models that accept `reasoning_effort`.

        Non-reasoning chat models (e.g. gpt-4o, gpt-4o-mini, gpt-4.1) reject
        this parameter with HTTP 400, and some OpenAI-compatible gateways
        translate the rejection into 503. We therefore restrict the parameter
        to known reasoning-capable model families.
        """
        m = str(model_name or '').strip().lower()
        if not m:
            return False
        # Known OpenAI reasoning model prefixes
        reasoning_prefixes = ('o1', 'o3', 'o4', 'gpt-5')
        for p in reasoning_prefixes:
            if m == p or m.startswith(p + '-') or m.startswith(p + '.'):
                return True
        return False

    def _is_claude_adaptive_model(self, model_name: Optional[str]) -> bool:
        m = str(model_name or '').strip().lower()
        return m in {'claude-opus-4-6', 'claude-sonnet-4-6'}

    def _is_claude_effort_model(self, model_name: Optional[str]) -> bool:
        m = str(model_name or '').strip().lower()
        return m in {'claude-opus-4-6', 'claude-sonnet-4-6', 'claude-opus-4-5'}

    def get_last_usage(self, conversation_id: Optional[str]) -> Optional[Dict[str, Any]]:
        key = conversation_id or 'default'
        return self._usage_cache.get(key)

    def _set_last_usage(self, conversation_id: Optional[str], usage: Optional[Dict[str, Any]]):
        if not usage:
            return
        key = conversation_id or 'default'
        self._usage_cache[key] = usage

    def _usage_to_dict(self, usage_obj: Any) -> Optional[Dict[str, Any]]:
        if not usage_obj:
            return None
        if isinstance(usage_obj, dict):
            return usage_obj
        try:
            return usage_obj.model_dump()
        except Exception:
            return {
                'prompt_tokens': getattr(usage_obj, 'prompt_tokens', None),
                'completion_tokens': getattr(usage_obj, 'completion_tokens', None),
                'total_tokens': getattr(usage_obj, 'total_tokens', None)
            }

    def _build_llm_kwargs(self, *, stream: bool, show_token_usage: bool = False) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            'model': self.get_model_name(),
            'temperature': self.get_temperature(),
            'max_tokens': self.get_max_tokens(),
        }

        top_p = self.get_top_p()
        if top_p is not None:
            kwargs['top_p'] = top_p
        fp = self.get_frequency_penalty()
        if fp is not None:
            kwargs['frequency_penalty'] = fp
        pp = self.get_presence_penalty()
        if pp is not None:
            kwargs['presence_penalty'] = pp

        custom = self.get_custom_params()
        if custom:
            for k, v in custom.items():
                if k not in kwargs:
                    kwargs[k] = v

        if stream:
            kwargs['stream'] = True
            if show_token_usage:
                kwargs['stream_options'] = {'include_usage': True}

        if self.get_thinking_effort_enabled() and self._provider in {'openai', 'gemini', 'custom'}:
            model_name = self.get_model_name()
            # For provider=openai (api.openai.com), only reasoning-capable
            # models accept `reasoning_effort`; sending it to non-reasoning
            # models (e.g. gpt-4o-mini) causes 400 on OpenAI and 503 on some
            # OpenAI-compatible gateways. For provider=custom we trust the
            # user's choice (DeepSeek/Qwen/etc. reasoning models handle the
            # parameter themselves).
            allow_effort = True
            if self._provider == 'openai' and not self._is_openai_reasoning_model(model_name):
                allow_effort = False
            effort = self._map_effort_level(self.get_thinking_effort_level(), self._provider, model_name) if allow_effort else None
            if effort:
                extra_body = kwargs.get('extra_body')
                if not isinstance(extra_body, dict):
                    extra_body = {}
                if 'reasoning_effort' not in extra_body:
                    extra_body['reasoning_effort'] = effort
                kwargs['extra_body'] = extra_body

        if self._provider == 'gemini':
            kwargs.pop('frequency_penalty', None)
            kwargs.pop('presence_penalty', None)
            kwargs.pop('stream_options', None)

        return kwargs

    def _get_conversation_memory(self, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get conversation memory.

        Args:
            conversation_id: Conversation ID; if None, uses the default conversation

        Returns:
            List of conversation history messages
        """
        conv_id = conversation_id or 'default'
        if conv_id not in self.memory:
            self.memory[conv_id] = []
        return self.memory[conv_id]

    def _add_to_memory(self, role: str, content: str, conversation_id: Optional[str] = None):
        """
        Add a message to memory.

        Args:
            role: Role (user/assistant/system)
            content: Message content
            conversation_id: Conversation ID
        """
        conv_id = conversation_id or 'default'
        if conv_id not in self.memory:
            self.memory[conv_id] = []

        self.memory[conv_id].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })

        # Limit memory size (keep the most recent 50 messages)
        if len(self.memory[conv_id]) > 50:
            # Keep system prompt messages
            system_messages = [msg for msg in self.memory[conv_id] if msg['role'] == 'system']
            recent_messages = [msg for msg in self.memory[conv_id] if msg['role'] != 'system'][-49:]
            self.memory[conv_id] = system_messages + recent_messages

    def clear_memory(self, conversation_id: Optional[str] = None):
        """
        Clear conversation memory.

        Args:
            conversation_id: Conversation ID; if None, clears all
        """
        if conversation_id:
            self.memory.pop(conversation_id, None)
        else:
            self.memory.clear()

    async def load_tools_from_db(self):
        """
        Load tools from the database and convert them into OpenAI format.

        This method will:
        1. Fetch all tools associated with this agent from the database
        2. Convert tools to OpenAI Function Calling format
        3. Store them in self.db_tools for later use
        """
        try:
            from runtime.modules.agent.service import AgentService

            # Get the agent's tool list (including full tool details)
            tools_data = AgentService.get_agent_tools(self.agent_id)

            # Convert to OpenAI format
            self.db_tools = ToolConverter.convert_tools(tools_data)

            self.tools_loaded = True
            logger.info(f"Agent {self.name} (ID: {self.agent_id}) loaded {len(self.db_tools)} tools")

            # Print tool list (for debugging)
            if self.db_tools:
                tool_names = [t['function']['name'] for t in self.db_tools]
                logger.info(f"Loaded tools: {', '.join(tool_names)}")

        except Exception as e:
            logger.error(f"Failed to load tools from database (Agent {self.name}): {e}", exc_info=True)
            self.db_tools = []
            self.tools_loaded = True  # Mark as loaded to avoid repeated attempts

    async def _search_knowledge_base(self, query: str) -> str:
        """
        Retrieve related information from the knowledge base.

        Args:
            query: Query text

        Returns:
            Retrieved related text
        """
        if not self.knowledge_bases:
            return ""

        try:
            from runtime.modules.km.vector_service import get_vector_service

            vector_service = get_vector_service()

            kb_results = []
            for kb in self.knowledge_bases:
                km_id = kb.get('km_id') or kb.get('id') or kb.get('name')
                kb_name = kb.get('name', km_id)

                try:
                    hits = vector_service.search(str(km_id), query, top_k=5)
                    if not hits:
                        continue

                    chunks = []
                    for h in hits:
                        content = (h or {}).get('content', '')
                        if content:
                            chunks.append(content)

                    if chunks:
                        kb_results.append(f"[From knowledge base {kb_name}]\n" + "\n---\n".join(chunks))

                except Exception as e:
                    logger.error(f"Failed to search knowledge base {km_id}: {e}")

            return "\n\n".join(kb_results) if kb_results else ""
        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            return ""

    def _prepare_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Prepare the tool schema (OpenAI function calling format).

        Returns:
            Tool definition list
        """
        tools_schema = []

        # 1. Add tools loaded from database (new system)
        if self.db_tools:
            tools_schema.extend(self.db_tools)
            logger.debug(f"Added {len(self.db_tools)} database tools")

        # 2. Add legacy self.tools config (backward compatible)
        if self.tools:
            for tool in self.tools:
                try:
                    tool_name = tool.get('name', '')

                    # Try to get signature from tool_executor
                    signature = tool_executor.get_tool_signature(tool_name)
                    if signature:
                        tool_def = {
                            "type": "function",
                            "function": signature
                        }
                    else:
                        # Use definition from config
                        tool_def = {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "description": tool.get('description', ''),
                                "parameters": tool.get('parameters', {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                })
                            }
                        }
                    tools_schema.append(tool_def)
                except Exception as e:
                    logger.error(f"Failed to prepare tool schema: {e}")

        # 3. Ensure read_skill is available when DocSkills are enabled (safe SKILL.md reader)
        try:
            signature = tool_executor.get_tool_signature('read_skill')
            if signature:
                existing_names = {
                    (t.get('function') or {}).get('name')
                    for t in tools_schema
                    if isinstance(t, dict)
                }
                if signature.get('name') not in existing_names:
                    tools_schema.append({"type": "function", "function": signature})
        except Exception:
            pass

        # 4. Ensure run_doc_skill is available (DocSkill runner)
        try:
            existing_names = {
                (t.get('function') or {}).get('name')
                for t in tools_schema
                if isinstance(t, dict)
            }
            if 'run_doc_skill' not in existing_names:
                tools_schema.append({
                    "type": "function",
                    "function": {
                        "name": "run_doc_skill",
                        "description": "Run a DocSkill by skill_key using its declared runner, returning structured execution result.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "skill_key": {"type": "string", "description": "DocSkill skill_key"},
                                "params": {"type": "object", "description": "Optional params passed to the runner", "additionalProperties": True},
                            },
                            "required": ["skill_key"],
                        },
                    },
                })
        except Exception:
            pass

        # 5. Ensure a2a_xmpp_adhoc is available (generic XMPP ad-hoc command invocation)
        try:
            existing_names = {
                (t.get('function') or {}).get('name')
                for t in tools_schema
                if isinstance(t, dict)
            }
            if 'a2a_xmpp_adhoc' not in existing_names:
                tools_schema.append({
                    "type": "function",
                    "function": {
                        "name": "a2a_xmpp_adhoc",
                        "description": "Invoke any XEP-0050 ad-hoc command on an XMPP peer. "
                                       "Use the command nodes listed in the discovered commands section. "
                                       "form_data keys should match the form fields the peer's command expects. "
                                       "Set inspect_only=true to retrieve form fields without submitting.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "peer_jid": {"type": "string", "description": "Peer's XMPP JID (e.g. user@domain)"},
                                "command_node": {"type": "string", "description": "Ad-hoc command node URI (e.g. urn:xmpp:a2a:cmd:tasks)"},
                                "form_data": {"type": "object", "description": "Key-value pairs to fill into the command form"},
                                "inspect_only": {"type": "boolean", "description": "If true, return form fields without submitting (default: false)"},
                            },
                            "required": ["peer_jid", "command_node"],
                        },
                    },
                })
            if 'a2a_jsonrpc_call' not in existing_names:
                tools_schema.append({
                    "type": "function",
                    "function": {
                        "name": "a2a_jsonrpc_call",
                        "description": (
                            "Invoke a peer's HTTP JSON-RPC service directly. "
                            "Use this when the peer's agent card lists a skill with "
                            "transport='http_jsonrpc' (it will provide endpoint, method, "
                            "and params_schema fields). The tool wraps the request in "
                            "JSON-RPC 2.0 envelope and returns the parsed response. "
                            "Example skill in card: greeting-jsonrpc with method "
                            "'greeting/exchange' — call with endpoint=<skill.endpoint>, "
                            "method=<skill.method>, params={greeting_type:'handshake', "
                            "metadata:{sender_jid:'<your jid>'}}."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "endpoint": {
                                    "type": "string",
                                    "description": "Full URL of the JSON-RPC endpoint (from skill.endpoint or agent_card.url, e.g. http://localhost:8789/a2a/)",
                                },
                                "method": {
                                    "type": "string",
                                    "description": "JSON-RPC method name (e.g. 'greeting/exchange', 'tasks/send')",
                                },
                                "params": {
                                    "type": "object",
                                    "description": "JSON-RPC params object — fill according to the skill's params_schema",
                                },
                            },
                            "required": ["endpoint", "method"],
                        },
                    },
                })
        except Exception:
            pass

        logger.info(f"Prepared {len(tools_schema)} tools for LLM tool calling")
        return tools_schema

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute a tool call.

        Args:
            tool_name: Tool name
            tool_args: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            if tool_name in ('run_doc_skill', 'read_skill'):
                try:
                    from runtime.modules.skills_registry.service import get_docskills_service

                    requested_key = str((tool_args or {}).get('skill_key') or '').strip()
                    if requested_key:
                        enabled_keys = get_docskills_service().get_agent_skill_keys(self.agent_id)
                        if requested_key not in set(enabled_keys or []):
                            if tool_name == 'run_doc_skill':
                                return json.dumps(
                                    {"success": False, "error": f"DocSkill not enabled for agent: {requested_key}"},
                                    ensure_ascii=False,
                                )
                            return f"Error: DocSkill not enabled for agent: {requested_key}"
                except Exception:
                    # Fail open for unexpected errors to avoid breaking non-docskill usage.
                    pass

            if tool_name == 'run_doc_skill':
                try:
                    from runtime.modules.skills_registry.service import get_docskills_service

                    skill_key = str((tool_args or {}).get('skill_key') or '').strip()
                    params = (tool_args or {}).get('params')
                    if not isinstance(params, dict):
                        params = {}
                    if not skill_key:
                        return json.dumps({"success": False, "error": "skill_key is required"}, ensure_ascii=False)

                    res = await get_docskills_service().run_skill(skill_key, params)
                    return json.dumps(res, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"run_doc_skill failed: {e}", exc_info=True)
                    return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

            # Handle generic XMPP ad-hoc command invocation
            if tool_name == 'a2a_xmpp_adhoc':
                return await self._execute_a2a_xmpp_adhoc(tool_args or {})

            # Handle generic HTTP JSON-RPC peer invocation
            if tool_name == 'a2a_jsonrpc_call':
                return await self._execute_a2a_jsonrpc_call(tool_args or {})

            # Check whether this is a code execution request
            if tool_name == 'execute_python_code' and self.code_executor:
                code = tool_args.get('code', '')
                result = self.code_executor.execute_python(code)
                return json.dumps(result, ensure_ascii=False)

            if tool_name == 'execute_shell_command' and self.code_executor:
                command = tool_args.get('command', '')
                result = self.code_executor.execute_shell(command)
                return json.dumps(result, ensure_ascii=False)

            # Check whether this is a DB tool (new system)
            # Tool name format: plugin_{id}, mcp_{id}_{tool}, function_{id}, skill_{id}
            if tool_name.startswith(('plugin_', 'mcp_', 'function_', 'skill_')):
                logger.info(f"Executing database tool via ToolRouter: {tool_name}")
                result = await self.tool_router.execute_tool(tool_name, tool_args)
                return json.dumps(result, ensure_ascii=False)

            # Execute tool using legacy tool_executor (backward compatible)
            logger.info(f"Executing tool via legacy tool_executor: {tool_name}")
            result = await asyncio.to_thread(
                tool_executor.execute_tool,
                tool_name,
                **tool_args
            )

            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return f"Tool execution error: {str(e)}"

    async def _execute_a2a_xmpp_adhoc(self, tool_args: Dict[str, Any]) -> str:
        """
        Execute a generic XMPP ad-hoc command on a peer.

        Uses XMPPA2AManager.call_adhoc_command() which handles the full
        XEP-0050 flow generically for any command node.
        """
        peer_jid = str(tool_args.get('peer_jid') or '').strip()
        command_node = str(tool_args.get('command_node') or '').strip()
        form_data = tool_args.get('form_data')
        inspect_only = bool(tool_args.get('inspect_only', False))

        if not peer_jid:
            return json.dumps({"ok": False, "error": "'peer_jid' is required"}, ensure_ascii=False)
        if not command_node:
            return json.dumps({"ok": False, "error": "'command_node' is required"}, ensure_ascii=False)
        if form_data is not None and not isinstance(form_data, dict):
            return json.dumps({"ok": False, "error": "'form_data' must be an object"}, ensure_ascii=False)

        logger.info(
            "[XMPP-A2A] tool adhoc: peer=%s node=%s inspect_only=%s form_keys=%s",
            peer_jid, command_node, inspect_only, list((form_data or {}).keys()),
        )

        # Get XMPP client and A2A manager
        try:
            from runtime.apps.sns.xmpp_client import XMPPClientManager
            client = XMPPClientManager.get_instance().get_client()
            if not client or not client.is_client_connected():
                return json.dumps({"ok": False, "error": "XMPP client not connected"}, ensure_ascii=False)
            a2a_mgr = getattr(client, '_a2a_manager', None)
            if a2a_mgr is None:
                return json.dumps({"ok": False, "error": "XMPP A2A manager not initialized"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Failed to get XMPP client: {e}"}, ensure_ascii=False)

        result = await a2a_mgr.call_adhoc_command(
            peer_jid=peer_jid,
            command_node=command_node,
            form_data=form_data,
            inspect_only=inspect_only,
        )
        return json.dumps(result, ensure_ascii=False)

    async def _execute_a2a_jsonrpc_call(self, tool_args: Dict[str, Any]) -> str:
        """
        Execute a JSON-RPC 2.0 call against a peer's HTTP endpoint.

        Wraps the request in a standard JSON-RPC envelope and POSTs it.
        Returns the raw response body as a JSON-serialized string so the LLM
        can read either the result or the error directly.
        """
        endpoint = str(tool_args.get('endpoint') or '').strip()
        method = str(tool_args.get('method') or '').strip()
        params = tool_args.get('params')

        if not endpoint:
            return json.dumps({"ok": False, "error": "'endpoint' is required"}, ensure_ascii=False)
        if not method:
            return json.dumps({"ok": False, "error": "'method' is required"}, ensure_ascii=False)
        if params is not None and not isinstance(params, dict):
            return json.dumps({"ok": False, "error": "'params' must be an object"}, ensure_ascii=False)

        rpc_id = uuid.uuid4().hex[:12]
        envelope = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params or {},
        }

        logger.info(
            "[A2A-JSONRPC] tool call: endpoint=%s method=%s params_keys=%s",
            endpoint, method, list((params or {}).keys()),
        )

        def _do_post() -> Dict[str, Any]:
            import urllib.request
            import urllib.error
            body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as he:
                try:
                    raw = he.read().decode("utf-8", errors="replace")
                except Exception:
                    raw = ""
                return {
                    "ok": False,
                    "error": f"HTTP {he.code}: {he.reason}",
                    "body": raw,
                }
            except Exception as e:
                return {"ok": False, "error": str(e)}

            try:
                parsed = json.loads(raw)
            except Exception:
                return {"ok": True, "raw": raw}

            if isinstance(parsed, dict) and "error" in parsed and parsed.get("error"):
                return {"ok": False, "jsonrpc_error": parsed["error"], "response": parsed}
            return {"ok": True, "response": parsed}

        try:
            result = await asyncio.to_thread(_do_post)
        except Exception as e:
            logger.error("[A2A-JSONRPC] tool call failed: %s", e, exc_info=True)
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

        return json.dumps(result, ensure_ascii=False)

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        use_tools: bool = True,
        use_memory: bool = True,
        use_knowledge_base: bool = True,
        stream: bool = False,
        attachments_text: str = "",
        image_data_urls: Optional[List[str]] = None,
        tool_choice: Optional[dict] = None,
        show_token_usage: bool = False,
    ) -> str:
        """
        Non-streaming Q&A.

        Args:
            message: User message
            conversation_id: Conversation ID
            use_memory: Whether to use memory
            use_knowledge_base: Whether to use the knowledge base
            stream: Whether streaming is enabled (this method is non-streaming only)

        Returns:
            Agent reply
        """
        if self._provider == 'claude':
            return await self._claude_chat(
                message=message,
                conversation_id=conversation_id,
                use_tools=use_tools,
                use_memory=use_memory,
                use_knowledge_base=use_knowledge_base,
                attachments_text=attachments_text,
                image_data_urls=image_data_urls,
                tool_choice=tool_choice,
                show_token_usage=show_token_usage,
            )

        if not self._openai_client:
            return "Error: LLM client is not configured"

        try:
            effective_use_tools = bool(use_tools)
            try:
                if isinstance(tool_choice, str) and tool_choice.strip().lower() == "none":
                    effective_use_tools = False
            except Exception:
                pass

            # Ensure tools are loaded from the database
            if effective_use_tools and not self.tools_loaded:
                await self.load_tools_from_db()

            # Build message list
            messages = []

            # Add system prompt
            system_prompt = self.get_system_prompt()

            # If using the knowledge base, retrieve related information first
            if use_knowledge_base and self.knowledge_bases:
                kb_context = await self._search_knowledge_base(message)
                if kb_context:
                    system_prompt += f"\n\nRelated knowledge base information:\n{kb_context}"

            messages.append({
                'role': 'system',
                'content': system_prompt
            })

            # Add conversation history (if using memory)
            if use_memory:
                history = self._get_conversation_memory(conversation_id)
                # Only add user and assistant messages, excluding system
                for msg in history:
                    if msg['role'] in ['user', 'assistant']:
                        messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })

            user_text = message
            if attachments_text:
                user_text += f"\n\nAttachment content:\n{attachments_text}"

            if image_data_urls and self.get_model_name().lower().startswith('gpt-4o'):
                content_parts = [{'type': 'text', 'text': user_text}]
                for url in image_data_urls:
                    if url:
                        content_parts.append({'type': 'image_url', 'image_url': {'url': url}})
                messages.append({'role': 'user', 'content': content_parts})
            else:
                messages.append({'role': 'user', 'content': user_text})

            # Prepare tools
            tools = self._prepare_tools_schema() if effective_use_tools else []

            # print("[info]:Message Send to llm:", messages)
            """
            You can print the message sent to llm here.
            print("[info]:Message Send to llm:", messages)
            """
            logger.info(f"Message Sent to llm")

            # Call LLM
            kwargs = self._build_llm_kwargs(stream=False, show_token_usage=show_token_usage)
            kwargs['messages'] = messages

            if effective_use_tools and tools:
                kwargs['tools'] = tools
                kwargs['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

            request_id = new_request_id()
            try:
                log_llm_request(request_id=request_id, source="runtime.modules.agent.agent_instance.AgentInstance.chat", request_json=kwargs)
            except Exception:
                pass

            response = await self._openai_client.chat.completions.create(**kwargs)

            try:
                raw = response.model_dump() if hasattr(response, 'model_dump') else getattr(response, '__dict__', str(response))
                log_llm_response(request_id=request_id, source="runtime.modules.agent.agent_instance.AgentInstance.chat", response_json=raw)
            except Exception:
                pass

            if show_token_usage:
                self._set_last_usage(conversation_id, self._usage_to_dict(getattr(response, 'usage', None)))

            # Process response
            assistant_message = response.choices[0].message

            # Handle tool calls
            reply = assistant_message.content or ""
            if effective_use_tools and assistant_message.tool_calls:
                # allow multi-round tool chaining (e.g. read_skill -> run_doc_skill)
                max_rounds = 5
                current_assistant_message = assistant_message

                for _ in range(max_rounds):
                    if not (effective_use_tools and current_assistant_message.tool_calls):
                        break

                    tool_messages = []
                    tool_calls_payload = []
                    for tc in current_assistant_message.tool_calls:
                        tool_name = tc.function.name
                        tool_args = json.loads(tc.function.arguments)

                        logger.info(f"[AgentInstance] Tool call: {tool_name}, args: {tool_args}")
                        tool_result = await self._execute_tool(tool_name, tool_args)

                        formatted_result = self._format_tool_result(tool_result)
                        tool_messages.append({
                            'role': 'tool',
                            'tool_call_id': tc.id,
                            'name': tool_name,
                            'content': formatted_result
                        })
                        payload = {
                            'id': tc.id,
                            'type': 'function',
                            'function': {
                                'name': tc.function.name,
                                'arguments': tc.function.arguments
                            }
                        }
                        try:
                            ts = getattr(tc, 'thought_signature', None)
                            extra_content: Optional[Dict[str, Any]] = None
                            if ts is None:
                                extra = getattr(tc, 'model_extra', None)
                                if isinstance(extra, dict):
                                    ts = extra.get('thought_signature')
                                    if ts is None:
                                        extra_content = extra.get('extra_content')
                                        if isinstance(extra_content, dict):
                                            google = extra_content.get('google')
                                            if isinstance(google, dict):
                                                ts = google.get('thought_signature')
                            else:
                                extra = getattr(tc, 'model_extra', None)
                                if isinstance(extra, dict):
                                    extra_content = extra.get('extra_content') if isinstance(extra.get('extra_content'), dict) else None

                            if ts:
                                payload['thought_signature'] = ts
                                if self._provider == 'gemini':
                                    if not isinstance(extra_content, dict):
                                        extra_content = {}
                                    google = extra_content.get('google')
                                    if not isinstance(google, dict):
                                        google = {}
                                    if not google.get('thought_signature'):
                                        google['thought_signature'] = ts
                                    extra_content['google'] = google
                                    payload['extra_content'] = extra_content
                        except Exception:
                            pass
                        tool_calls_payload.append(payload)

                    messages.append({
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': tool_calls_payload
                    })
                    messages.extend(tool_messages)

                    tools_schema = self._prepare_tools_schema() if effective_use_tools else []
                    kwargs2 = self._build_llm_kwargs(stream=False, show_token_usage=show_token_usage)
                    kwargs2['messages'] = messages
                    if effective_use_tools and tools_schema:
                        kwargs2['tools'] = tools_schema
                        kwargs2['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

                    request_id2 = new_request_id()
                    try:
                        log_llm_request(request_id=request_id2, source="runtime.modules.agent.agent_instance.AgentInstance.chat", request_json=kwargs2)
                    except Exception:
                        pass

                    response2 = await self._openai_client.chat.completions.create(**kwargs2)

                    try:
                        raw2 = response2.model_dump() if hasattr(response2, 'model_dump') else getattr(response2, '__dict__', str(response2))
                        log_llm_response(request_id=request_id2, source="runtime.modules.agent.agent_instance.AgentInstance.chat", response_json=raw2)
                    except Exception:
                        pass
                    if show_token_usage:
                        self._set_last_usage(conversation_id, self._usage_to_dict(getattr(response2, 'usage', None)))
                    current_assistant_message = response2.choices[0].message
                    reply = current_assistant_message.content or ""

            # Save to memory
            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', reply, conversation_id)

            return reply

        except Exception as e:
            try:
                log_llm_error(request_id=new_request_id(), source="runtime.modules.agent.agent_instance.AgentInstance.chat", error=e)
            except Exception:
                pass
            logger.error(f"Agent chat failed: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        use_tools: bool = True,
        use_memory: bool = True,
        use_knowledge_base: bool = True,
        attachments_text: str = "",
        image_data_urls: Optional[List[str]] = None,
        attachments_meta: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[dict] = None,
        show_token_usage: bool = False,
    ) -> AsyncIterator[str]:
        """
        Streaming chat.

        Args:
            message: User message
            conversation_id: Conversation ID
            use_memory: Whether to use memory
            use_knowledge_base: Whether to use knowledge base

        Yields:
            Streamed text chunks
        """
        if self._provider == 'claude':
            async for chunk in self._claude_chat_stream(
                message=message,
                conversation_id=conversation_id,
                use_tools=use_tools,
                use_memory=use_memory,
                use_knowledge_base=use_knowledge_base,
                attachments_text=attachments_text,
                image_data_urls=image_data_urls,
                attachments_meta=attachments_meta,
                tool_choice=tool_choice,
                show_token_usage=show_token_usage,
            ):
                yield chunk
            return

        if not self._openai_client:
            error_msg = (
                f"Agent '{self.name}' has no LLM client configured."
                f"Please select a valid model configuration in the top toolbar of the Agent chat page."
                f"If no models are available, add a model configuration in the 'Model Management' page first."
            )
            logger.error(error_msg)
            yield f"Error: {error_msg}"
            return

        try:
            effective_use_tools = bool(use_tools)
            try:
                if isinstance(tool_choice, str) and tool_choice.strip().lower() == "none":
                    effective_use_tools = False
            except Exception:
                pass

            # Ensure tools are loaded from the database
            if effective_use_tools and not self.tools_loaded:
                await self.load_tools_from_db()

            # Build message list (same as chat method)
            messages = []

            # Add system prompt
            system_prompt = self.get_system_prompt()

            # If using knowledge base, retrieve related info first
            if use_knowledge_base and self.knowledge_bases:
                kb_context = await self._search_knowledge_base(message)
                if kb_context:
                    system_prompt += f"\n\nRelated knowledge base information:\n{kb_context}"

            messages.append({
                'role': 'system',
                'content': system_prompt
            })

            # Add conversation history
            if use_memory:
                history = self._get_conversation_memory(conversation_id)
                for msg in history:
                    if msg['role'] in ['user', 'assistant']:
                        messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })

            user_text = message
            if attachments_text:
                user_text += f"\n\nAttachment content:\n{attachments_text}"

            if image_data_urls and self.get_model_name().lower().startswith('gpt-4o'):
                content_parts = [{'type': 'text', 'text': user_text}]
                for url in image_data_urls:
                    if url:
                        content_parts.append({'type': 'image_url', 'image_url': {'url': url}})
                messages.append({'role': 'user', 'content': content_parts})
            else:
                messages.append({'role': 'user', 'content': user_text})

            # Prepare tools
            tools = self._prepare_tools_schema() if effective_use_tools else []

            kwargs = self._build_llm_kwargs(stream=True, show_token_usage=show_token_usage)
            kwargs['messages'] = messages

            if effective_use_tools and tools:
                kwargs['tools'] = tools
                kwargs['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

            request_id = new_request_id()
            try:
                log_llm_request(request_id=request_id, source="runtime.modules.agent.agent_instance.AgentInstance.chat_stream", request_json=kwargs)
            except Exception:
                pass

            stream = await self._openai_client.chat.completions.create(**kwargs)

            # Collect full reply and tool calls
            full_reply = ""
            tool_calls_accumulator = {}
            last_usage: Optional[Dict[str, Any]] = None

            raw_tool_sig_accumulator_by_index: Dict[int, Any] = {}
            raw_tool_sig_accumulator_by_id: Dict[str, Any] = {}
            raw_tool_extra_accumulator_by_index: Dict[int, Any] = {}
            raw_tool_extra_accumulator_by_id: Dict[str, Any] = {}

            async for chunk in stream:
                try:
                    raw_chunk = chunk.model_dump() if hasattr(chunk, 'model_dump') else getattr(chunk, '__dict__', str(chunk))
                    log_llm_stream_chunk(request_id=request_id, source="runtime.modules.agent.agent_instance.AgentInstance.chat_stream", stream_raw=raw_chunk)
                except Exception:
                    pass

                if effective_use_tools and isinstance(raw_chunk, dict):
                    try:
                        choices0 = (raw_chunk.get('choices') or [None])[0] or {}
                        raw_delta = choices0.get('delta') or {}
                        for raw_tc_pos, raw_tc in enumerate(raw_delta.get('tool_calls') or []):
                            if not isinstance(raw_tc, dict):
                                continue
                            idx = raw_tc.get('index')
                            tc_id = raw_tc.get('id')
                            extra_content = raw_tc.get('extra_content')

                            ts = raw_tc.get('thought_signature')
                            if not ts and isinstance(extra_content, dict):
                                google = extra_content.get('google')
                                if isinstance(google, dict):
                                    ts = google.get('thought_signature')

                            if ts:
                                try:
                                    use_idx = int(idx) if idx is not None else int(raw_tc_pos)
                                    raw_tool_sig_accumulator_by_index[use_idx] = ts
                                    if isinstance(extra_content, dict):
                                        raw_tool_extra_accumulator_by_index[use_idx] = extra_content
                                except Exception:
                                    pass
                                if tc_id:
                                    raw_tool_sig_accumulator_by_id[str(tc_id)] = ts
                                    if isinstance(extra_content, dict):
                                        raw_tool_extra_accumulator_by_id[str(tc_id)] = extra_content
                    except Exception:
                        pass
                if show_token_usage and getattr(chunk, 'usage', None):
                    last_usage = self._usage_to_dict(getattr(chunk, 'usage', None))

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Handle content
                if delta.content:
                    full_reply += delta.content
                    yield delta.content

                # Handle tool calls (accumulate delta)
                if effective_use_tools and delta.tool_calls:
                    for tc_pos, tc_delta in enumerate(delta.tool_calls):
                        acc_key: Any
                        if tc_delta.index is not None:
                            acc_key = tc_delta.index
                        elif tc_delta.id:
                            acc_key = tc_delta.id
                        else:
                            acc_key = tc_pos

                        if acc_key not in tool_calls_accumulator:
                            tool_calls_accumulator[acc_key] = {
                                'id': tc_delta.id or f'tc_{tc_pos}',
                                'type': 'function',
                                'function': {'name': '', 'arguments': ''},
                                'thought_signature': None,
                                'extra_content': None,
                            }
                        if tc_delta.id:
                            tool_calls_accumulator[acc_key]['id'] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_accumulator[acc_key]['function']['name'] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_accumulator[acc_key]['function']['arguments'] += tc_delta.function.arguments

                        if tool_calls_accumulator[acc_key].get('thought_signature') is None:
                            try:
                                ts = getattr(tc_delta, 'thought_signature', None)
                                extra_content: Optional[Dict[str, Any]] = None
                                if ts is None:
                                    extra = getattr(tc_delta, 'model_extra', None)
                                    if isinstance(extra, dict):
                                        ts = extra.get('thought_signature')
                                        if ts is None:
                                            extra_content = extra.get('extra_content')
                                            if isinstance(extra_content, dict):
                                                google = extra_content.get('google')
                                                if isinstance(google, dict):
                                                    ts = google.get('thought_signature')
                                else:
                                    extra = getattr(tc_delta, 'model_extra', None)
                                    if isinstance(extra, dict):
                                        extra_content = extra.get('extra_content') if isinstance(extra.get('extra_content'), dict) else None

                                if not ts:
                                    if tc_delta.id:
                                        ts = raw_tool_sig_accumulator_by_id.get(str(tc_delta.id))
                                        if tc_delta.id:
                                            extra_content = raw_tool_extra_accumulator_by_id.get(str(tc_delta.id))
                                if not ts:
                                    if tc_delta.index is not None:
                                        ts = raw_tool_sig_accumulator_by_index.get(int(tc_delta.index))
                                        if tc_delta.index is not None:
                                            extra_content = raw_tool_extra_accumulator_by_index.get(int(tc_delta.index))
                                    else:
                                        ts = raw_tool_sig_accumulator_by_index.get(int(tc_pos))
                                        extra_content = raw_tool_extra_accumulator_by_index.get(int(tc_pos))
                                if ts:
                                    tool_calls_accumulator[acc_key]['thought_signature'] = ts
                                    if isinstance(extra_content, dict):
                                        tool_calls_accumulator[acc_key]['extra_content'] = extra_content
                            except Exception:
                                pass

            # If there are tool calls, execute tools and get final reply (allow multi-round tool chaining)
            if effective_use_tools and tool_calls_accumulator:
                def _normalize_tool_calls_for_request(raw_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                    out: List[Dict[str, Any]] = []
                    for c in raw_calls or []:
                        if not isinstance(c, dict):
                            continue
                        c2 = dict(c)
                        if self._provider != 'gemini':
                            c2.pop('thought_signature', None)
                            c2.pop('extra_content', None)
                        else:
                            if not c2.get('thought_signature'):
                                raise RuntimeError(
                                    "Gemini tool call is missing thought_signature. "
                                    "This value must be replayed in follow-up requests for function calling to work."
                                )
                            ts = c2.get('thought_signature')
                            extra_content = c2.get('extra_content')
                            if not isinstance(extra_content, dict):
                                extra_content = {}
                            google = extra_content.get('google')
                            if not isinstance(google, dict):
                                google = {}
                            if not google.get('thought_signature'):
                                google['thought_signature'] = ts
                            extra_content['google'] = google
                            c2['extra_content'] = extra_content
                        if c2.get('thought_signature', None) is None:
                            c2.pop('thought_signature', None)
                        out.append(c2)
                    return out

                max_rounds = 5
                round_idx = 0
                pending_tool_calls = tool_calls_accumulator

                while effective_use_tools and pending_tool_calls and round_idx < max_rounds:
                    logger.info(f"Detected {len(pending_tool_calls)} tool calls")

                    tool_messages = []
                    for tc_data in pending_tool_calls.values():
                        tool_name = tc_data['function']['name']
                        tool_args = json.loads(tc_data['function']['arguments'])

                        logger.info(f"[AgentInstance] Tool call: {tool_name}, args: {tool_args}")
                        tool_result = await self._execute_tool(tool_name, tool_args)
                        logger.info(f"[AgentInstance] Tool result: {tool_result[:500] if len(str(tool_result)) > 500 else tool_result}")

                        formatted_result = self._format_tool_result(tool_result)
                        tool_messages.append({
                            'role': 'tool',
                            'tool_call_id': tc_data['id'],
                            'name': tool_name,
                            'content': formatted_result
                        })

                    tool_calls_for_request = _normalize_tool_calls_for_request(list(pending_tool_calls.values()))

                    messages.append({
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': tool_calls_for_request
                    })
                    messages.extend(tool_messages)

                    # ask model again, still allowing tools
                    kwargs_final = {
                        **self._build_llm_kwargs(stream=True, show_token_usage=show_token_usage),
                        'messages': messages,
                    }
                    if effective_use_tools and tools:
                        kwargs_final['tools'] = tools
                        kwargs_final['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

                    request_id_round = new_request_id()
                    try:
                        log_llm_request(request_id=request_id_round, source="runtime.modules.agent.agent_instance.AgentInstance.chat_stream", request_json=kwargs_final)
                    except Exception:
                        pass

                    if self._provider == 'gemini':
                        final_stream = self._httpx_stream_openai_compatible_chat_completions(
                            request_json=kwargs_final,
                            request_id=request_id_round,
                            source="runtime.modules.agent.agent_instance.AgentInstance.chat_stream",
                        )
                    else:
                        final_stream = await self._openai_client.chat.completions.create(**kwargs_final)

                    full_reply = ""
                    pending_tool_calls = {}

                    async for chunk in final_stream:
                        if isinstance(chunk, dict):
                            raw_chunk = chunk
                            if show_token_usage:
                                usage_obj = raw_chunk.get('usage')
                                if isinstance(usage_obj, dict):
                                    last_usage = usage_obj

                            choices0 = (raw_chunk.get('choices') or [None])[0] or {}
                            raw_delta = choices0.get('delta') or {}
                            content = raw_delta.get('content')
                            if content:
                                full_reply += str(content)
                                yield str(content)

                            if effective_use_tools and raw_delta.get('tool_calls'):
                                for tc_pos, raw_tc in enumerate(raw_delta.get('tool_calls') or []):
                                    if not isinstance(raw_tc, dict):
                                        continue
                                    acc_key: Any = raw_tc.get('id') or raw_tc.get('index') or tc_pos
                                    entry = pending_tool_calls.get(acc_key)
                                    if not isinstance(entry, dict):
                                        entry = {
                                            'id': raw_tc.get('id') or f'tc_{round_idx}_{tc_pos}',
                                            'type': 'function',
                                            'function': {'name': '', 'arguments': ''},
                                            'thought_signature': None,
                                            'extra_content': None,
                                        }
                                        pending_tool_calls[acc_key] = entry

                                    if raw_tc.get('id'):
                                        entry['id'] = raw_tc.get('id')
                                    func = raw_tc.get('function') or {}
                                    if isinstance(func, dict):
                                        if func.get('name'):
                                            entry['function']['name'] = func.get('name')
                                        if func.get('arguments'):
                                            entry['function']['arguments'] += str(func.get('arguments'))

                                    extra_content = raw_tc.get('extra_content')
                                    if isinstance(extra_content, dict):
                                        entry['extra_content'] = extra_content

                                    if entry.get('thought_signature') is None:
                                        ts = raw_tc.get('thought_signature')
                                        if not ts and isinstance(extra_content, dict):
                                            google = extra_content.get('google')
                                            if isinstance(google, dict):
                                                ts = google.get('thought_signature')
                                        if ts:
                                            entry['thought_signature'] = ts
                            continue

                        try:
                            raw_chunk = chunk.model_dump() if hasattr(chunk, 'model_dump') else getattr(chunk, '__dict__', str(chunk))
                            log_llm_stream_chunk(request_id=request_id_round, source="runtime.modules.agent.agent_instance.AgentInstance.chat_stream", stream_raw=raw_chunk)
                        except Exception:
                            pass

                        if show_token_usage and getattr(chunk, 'usage', None):
                            last_usage = self._usage_to_dict(getattr(chunk, 'usage', None))

                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if delta.content:
                            content = delta.content
                            full_reply += content
                            yield content
                        if effective_use_tools and delta.tool_calls:
                            for tc_delta in delta.tool_calls:
                                idx = tc_delta.index
                                if idx not in pending_tool_calls:
                                    pending_tool_calls[idx] = {
                                        'id': tc_delta.id or f'tc_{round_idx}_{idx}',
                                        'type': 'function',
                                        'function': {'name': '', 'arguments': ''},
                                        'thought_signature': None,
                                    }
                                if tc_delta.id:
                                    pending_tool_calls[idx]['id'] = tc_delta.id
                                if tc_delta.function:
                                    if tc_delta.function.name:
                                        pending_tool_calls[idx]['function']['name'] = tc_delta.function.name
                                    if tc_delta.function.arguments:
                                        pending_tool_calls[idx]['function']['arguments'] += tc_delta.function.arguments

                    round_idx += 1

            if show_token_usage and last_usage:
                self._set_last_usage(conversation_id, last_usage)

            # Save to memory
            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', full_reply, conversation_id)

            try:
                log_llm_response(
                    request_id=request_id,
                    source="runtime.modules.agent.agent_instance.AgentInstance.chat_stream",
                    response_json={"status": "completed"},
                )
            except Exception:
                pass

            # Save to database (optimization: use a single session for batch ops)
            if conversation_id:
                try:
                    from db.database import get_db_session as get_session
                    from db.models.aisns import AIChatMessages

                    session = get_session()
                    try:
                        # Check whether this is a new conversation
                        is_new_conversation = not session.query(AIChatMessages).filter_by(
                            conversation_id=conversation_id,
                            is_first=True
                        ).first()

                        messages_to_save = []
                        current_time = datetime.now()

                        if is_new_conversation:
                            # Save user message as conversation title
                            messages_to_save.append(AIChatMessages(
                                conversation_id=conversation_id,
                                agent_id=self.agent_id,  # Add agent_id
                                flag=0,  # 0=send
                                title=message[:50] if len(message) > 50 else message,
                                content=message,
                                attachment_list=json.dumps(attachments_meta, ensure_ascii=False) if attachments_meta else None,
                                owner_name="User",
                                owner_account="user",
                                friend_name=self.name,
                                friend_account=str(self.agent_id),
                                is_first=True,
                                create_time=current_time
                            ))
                        else:
                            # Save normal user message
                            messages_to_save.append(AIChatMessages(
                                conversation_id=conversation_id,
                                agent_id=self.agent_id,  # Add agent_id
                                flag=0,  # 0=send
                                content=message,
                                attachment_list=json.dumps(attachments_meta, ensure_ascii=False) if attachments_meta else None,
                                owner_name="User",
                                owner_account="user",
                                friend_name=self.name,
                                friend_account=str(self.agent_id),
                                is_first=False,
                                create_time=current_time
                            ))

                        # Save AI reply
                        messages_to_save.append(AIChatMessages(
                            conversation_id=conversation_id,
                            agent_id=self.agent_id,  # Add agent_id
                            flag=1,  # 1=receive
                            content=full_reply,
                            owner_name="User",
                            owner_account="user",
                            friend_name=self.name,
                            friend_account=str(self.agent_id),
                            is_first=False,
                            create_time=current_time
                        ))

                        # Batch save
                        from db.write_queue import db_write
                        _msgs = messages_to_save
                        _cid = conversation_id
                        _count = len(messages_to_save)
                        def _do(sess):
                            sess.add_all(_msgs)
                        db_write(_do, description="agent_instance_save_messages")
                        logger.info(f"Saved conversation messages to database: conversation_id={_cid}, count={_count}")

                    except Exception as save_error:
                        logger.error(f"Failed to save conversation messages to database: {save_error}", exc_info=True)
                    finally:
                        session.close()

                except Exception as e:
                    logger.error(f"Database connection failed: {e}", exc_info=True)

        except Exception as e:
            try:
                log_llm_error(request_id=new_request_id(), source="runtime.modules.agent.agent_instance.AgentInstance.chat_stream", error=e)
            except Exception:
                pass
            logger.error(f"Agent streaming chat failed: {e}", exc_info=True)
            yield f"Error: {str(e)}"

    def _format_tool_result(self, tool_result: Any) -> str:
        """
        Format tool result to be more LLM-friendly.

        Args:
            tool_result: Raw tool result (may be a JSON string or dict)

        Returns:
            Formatted string
        """
        try:
            # If string, try parsing as JSON
            if isinstance(tool_result, str):
                try:
                    result_dict = json.loads(tool_result)
                except:
                    # Not JSON, return as-is
                    return tool_result
            else:
                result_dict = tool_result

            # If not a dict, stringify and return
            if not isinstance(result_dict, dict):
                return str(tool_result)

            # Extract key information in a more readable format
            formatted_parts = []

            # 1. Status
            status = result_dict.get('status') or result_dict.get('success')
            if status:
                if status == 'success' or status is True:
                    formatted_parts.append("✓ Succeeded")
                else:
                    formatted_parts.append(f"✗ Failed: {result_dict.get('error', 'Unknown error')}")

            # 2. Main message
            message = result_dict.get('message')
            if message:
                formatted_parts.append(f"Message: {message}")

            # 3. Result data
            result_data = result_dict.get('result')
            if result_data:
                if isinstance(result_data, dict):
                    # Extract stdout (if present)
                    stdout = result_data.get('stdout', '')
                    if stdout:
                        formatted_parts.append(f"Output:\n{stdout.strip()}")

                    stderr = result_data.get('stderr', '')
                    if stderr:
                        formatted_parts.append(f"Error output:\n{stderr.strip()}")
                else:
                    formatted_parts.append(f"Result: {result_data}")

            # 4. Skill/plugin-specific action data
            action = result_dict.get('action')
            if action and isinstance(action, dict):
                action_parts = []

                # Screenshot
                if action.get('performed') == 'screenshot_capture':
                    filepath = action.get('filepath', '')
                    size = action.get('size', '')
                    action_parts.append(f"Screenshot saved: {filepath}")
                    if size:
                        action_parts.append(f"Size: {size}")

                # Mouse click
                elif action.get('performed') == 'mouse_click':
                    coords = action.get('coordinates', '')
                    button = action.get('button', '')
                    action_parts.append(f"Clicked {button} button at {coords}")

                # Keyboard input
                elif action.get('performed') == 'keyboard_input':
                    text_len = action.get('text_length', 0)
                    action_parts.append(f"Typed {text_len} characters")

                # Generic action output
                elif action.get('stdout'):
                    action_parts.append(f"Execution output:\n{action.get('stdout', '').strip()}")

                if action_parts:
                    formatted_parts.extend(action_parts)

            # 5. Output (plugin/function execution result)
            output = result_dict.get('output')
            if output and isinstance(output, dict):
                stdout = output.get('stdout', '')
                if stdout:
                    formatted_parts.append(f"Execution output:\n{stdout.strip()}")

            # 6. Timestamp
            timestamp = result_dict.get('timestamp')
            if timestamp:
                formatted_parts.append(f"Time: {timestamp}")

            # If we have formatted parts, return them
            if formatted_parts:
                return "\n".join(formatted_parts)

            # Otherwise return compact JSON
            return json.dumps(result_dict, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to format tool result: {e}")
            # Fallback: return stringified raw result
            return str(tool_result)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict.

        Returns:
            Agent info dict
        """
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'description': self.description,
            'llm_config': {
                'model_name': self.get_model_name(),
                'temperature': self.get_temperature(),
                'max_tokens': self.get_max_tokens()
            },
            'role_config': {
                'system_prompt': self.get_system_prompt()[:100] + '...' if len(self.get_system_prompt()) > 100 else self.get_system_prompt()
            },
            'tools_count': len(self.tools),
            'knowledge_bases_count': len(self.knowledge_bases),
            'plugins_count': len(self.plugins),
            'enable_code_execution': self.enable_code_execution,
            'memory_conversations': len(self.memory)
        }
