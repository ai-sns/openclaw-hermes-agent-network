# -*- coding: utf-8 -*-
"""
Agent Instance - Independent Agent object instance
Each agent has its own LLM configuration, role, tools, knowledge bases, and memory
"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
import openai
from openai import AsyncOpenAI

from .tool_executor import tool_executor
from .code_executor import CodeExecutor
from .tool_router import ToolRouter
from .tool_converter import ToolConverter
from backend.modules.tools.tool_executor import get_tool_executor

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

        # Memory - stores conversation history
        self.memory: Dict[str, List[Dict[str, Any]]] = {}

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
            api_endpoint = self.llm_config.get('api_endpoint', 'https://api.openai.com/v1')
            api_key = self.llm_config.get('api_key', '')

            if not api_key:
                logger.warning(f"Agent {self.name} has no API key configured")
                self.client = None
                return

            # Create async OpenAI client
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=api_endpoint
            )

            logger.info(f"LLM client initialized: {api_endpoint}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.client = None

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
            from backend.modules.skills_registry.service import get_docskills_service

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
            from backend.modules.agent.service import AgentService

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
            from backend.modules.km.vector_service import get_vector_service

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
                    from backend.modules.skills_registry.service import get_docskills_service

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
                    from backend.modules.skills_registry.service import get_docskills_service

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
        if not self.client:
            return "Error: LLM client is not configured"

        try:
            # Ensure tools are loaded from the database
            if use_tools and not self.tools_loaded:
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
            tools = self._prepare_tools_schema() if use_tools else []

            print("[info]:Message Send to llm:", messages)

            # Call LLM
            kwargs = {
                'model': self.get_model_name(),
                'messages': messages,
                'temperature': self.get_temperature(),
                'max_tokens': self.get_max_tokens()
            }

            if use_tools and tools:
                kwargs['tools'] = tools
                kwargs['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

            response = await self.client.chat.completions.create(**kwargs)

            # Process response
            assistant_message = response.choices[0].message

            # Handle tool calls
            reply = assistant_message.content or ""
            if use_tools and assistant_message.tool_calls:
                # allow multi-round tool chaining (e.g. read_skill -> run_doc_skill)
                max_rounds = 5
                current_assistant_message = assistant_message

                for _ in range(max_rounds):
                    if not (use_tools and current_assistant_message.tool_calls):
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
                        tool_calls_payload.append({
                            'id': tc.id,
                            'type': 'function',
                            'function': {
                                'name': tc.function.name,
                                'arguments': tc.function.arguments
                            }
                        })

                    messages.append({
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': tool_calls_payload
                    })
                    messages.extend(tool_messages)

                    tools_schema = self._prepare_tools_schema() if use_tools else []
                    kwargs2 = {
                        'model': self.get_model_name(),
                        'messages': messages,
                        'temperature': self.get_temperature(),
                        'max_tokens': self.get_max_tokens()
                    }
                    if use_tools and tools_schema:
                        kwargs2['tools'] = tools_schema
                        kwargs2['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

                    response2 = await self.client.chat.completions.create(**kwargs2)
                    current_assistant_message = response2.choices[0].message
                    reply = current_assistant_message.content or ""

            # Save to memory
            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', reply, conversation_id)

            return reply

        except Exception as e:
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
        if not self.client:
            error_msg = (
                f"Agent '{self.name}' has no LLM client configured."
                f"Please select a valid model configuration in the top toolbar of the Agent chat page."
                f"If no models are available, add a model configuration in the 'Model Management' page first."
            )
            logger.error(error_msg)
            yield f"Error: {error_msg}"
            return

        try:
            # Ensure tools are loaded from the database
            if use_tools and not self.tools_loaded:
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
            tools = self._prepare_tools_schema() if use_tools else []

            # Call LLM (streaming)
            kwargs = {
                'model': self.get_model_name(),
                'messages': messages,
                'temperature': self.get_temperature(),
                'max_tokens': self.get_max_tokens(),
                'stream': True
            }

            if use_tools and tools:
                kwargs['tools'] = tools
                kwargs['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

            stream = await self.client.chat.completions.create(**kwargs)

            # Collect full reply and tool calls
            full_reply = ""
            tool_calls_accumulator = {}

            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Handle content
                if delta.content:
                    full_reply += delta.content
                    yield delta.content

                # Handle tool calls (accumulate delta)
                if use_tools and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_accumulator:
                            tool_calls_accumulator[idx] = {
                                'id': tc_delta.id or f'tc_{idx}',
                                'type': 'function',
                                'function': {'name': '', 'arguments': ''}
                            }
                        if tc_delta.id:
                            tool_calls_accumulator[idx]['id'] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_accumulator[idx]['function']['name'] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_accumulator[idx]['function']['arguments'] += tc_delta.function.arguments

            # If there are tool calls, execute tools and get final reply (allow multi-round tool chaining)
            if use_tools and tool_calls_accumulator:
                max_rounds = 5
                round_idx = 0
                pending_tool_calls = tool_calls_accumulator

                while use_tools and pending_tool_calls and round_idx < max_rounds:
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

                    messages.append({
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': list(pending_tool_calls.values())
                    })
                    messages.extend(tool_messages)

                    # ask model again, still allowing tools
                    kwargs_final = {
                        'model': self.get_model_name(),
                        'messages': messages,
                        'temperature': self.get_temperature(),
                        'max_tokens': self.get_max_tokens(),
                        'stream': True
                    }
                    if use_tools and tools:
                        kwargs_final['tools'] = tools
                        kwargs_final['tool_choice'] = tool_choice if tool_choice is not None else 'auto'

                    final_stream = await self.client.chat.completions.create(**kwargs_final)

                    full_reply = ""
                    pending_tool_calls = {}
                    async for chunk in final_stream:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if delta.content:
                            content = delta.content
                            full_reply += content
                            yield content
                        if use_tools and delta.tool_calls:
                            for tc_delta in delta.tool_calls:
                                idx = tc_delta.index
                                if idx not in pending_tool_calls:
                                    pending_tool_calls[idx] = {
                                        'id': tc_delta.id or f'tc_{round_idx}_{idx}',
                                        'type': 'function',
                                        'function': {'name': '', 'arguments': ''}
                                    }
                                if tc_delta.id:
                                    pending_tool_calls[idx]['id'] = tc_delta.id
                                if tc_delta.function:
                                    if tc_delta.function.name:
                                        pending_tool_calls[idx]['function']['name'] = tc_delta.function.name
                                    if tc_delta.function.arguments:
                                        pending_tool_calls[idx]['function']['arguments'] += tc_delta.function.arguments

                    round_idx += 1

            # Save to memory
            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', full_reply, conversation_id)

            # Save to database (optimization: use a single session for batch ops)
            if conversation_id:
                try:
                    from backend.database.base import get_session
                    from backend.database.models.chat import AIChatMessages

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
                        session.add_all(messages_to_save)
                        session.commit()
                        logger.info(f"Saved conversation messages to database: conversation_id={conversation_id}, count={len(messages_to_save)}")

                    except Exception as save_error:
                        session.rollback()
                        logger.error(f"Failed to save conversation messages to database: {save_error}", exc_info=True)
                    finally:
                        session.close()

                except Exception as e:
                    logger.error(f"Database connection failed: {e}", exc_info=True)

        except Exception as e:
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
