# -*- coding: utf-8 -*-
"""
Agent Instance - 独立的Agent对象实例
每个Agent拥有自己的LLM配置、角色、工具、知识库和memory
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

logger = logging.getLogger(__name__)


class AgentInstance:
    """
    Agent实例类 - 每个agent是一个独立的对象

    属性:
        agent_id: Agent ID
        name: Agent名称
        description: Agent描述
        llm_config: LLM配置（api_endpoint、api_key、model_name等）
        role_config: 角色配置（system_prompt、greeting等）
        tools: 可用工具列表
        knowledge_bases: 关联的知识库
        memory: 对话历史memory
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
        初始化Agent实例

        Args:
            agent_id: Agent ID
            name: Agent名称
            description: Agent描述
            llm_config: LLM配置字典
            role_config: 角色配置字典
            tools: 工具列表
            knowledge_bases: 知识库列表
            plugins: 插件ID列表
            enable_code_execution: 是否启用代码执行
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

        # Memory - 存储对话历史
        self.memory: Dict[str, List[Dict[str, Any]]] = {}

        # 初始化OpenAI客户端
        self._init_llm_client()

        # 初始化代码执行器（如果启用）
        self.code_executor = None
        if self.enable_code_execution:
            self.code_executor = CodeExecutor()

        logger.info(f"Agent实例已创建: {self.name} (ID: {self.agent_id})")

    def _init_llm_client(self):
        """初始化LLM客户端"""
        try:
            api_endpoint = self.llm_config.get('api_endpoint', 'https://api.openai.com/v1')
            api_key = self.llm_config.get('api_key', '')

            if not api_key:
                logger.warning(f"Agent {self.name} 没有配置API key")
                self.client = None
                return

            # 创建异步OpenAI客户端
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=api_endpoint
            )

            logger.info(f"LLM客户端已初始化: {api_endpoint}")
        except Exception as e:
            logger.error(f"初始化LLM客户端失败: {e}")
            self.client = None

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.role_config.get('system_prompt', 'You are a helpful AI assistant.')

    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.llm_config.get('model_name', 'gpt-4o-mini')

    def get_temperature(self) -> float:
        """获取temperature参数"""
        return self.llm_config.get('temperature', 0.7)

    def get_max_tokens(self) -> int:
        """获取max_tokens参数"""
        return self.llm_config.get('max_tokens', 2048)

    def _get_conversation_memory(self, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取对话记忆

        Args:
            conversation_id: 对话ID，如果为None则使用默认对话

        Returns:
            对话历史消息列表
        """
        conv_id = conversation_id or 'default'
        if conv_id not in self.memory:
            self.memory[conv_id] = []
        return self.memory[conv_id]

    def _add_to_memory(self, role: str, content: str, conversation_id: Optional[str] = None):
        """
        添加消息到memory

        Args:
            role: 角色（user/assistant/system）
            content: 消息内容
            conversation_id: 对话ID
        """
        conv_id = conversation_id or 'default'
        if conv_id not in self.memory:
            self.memory[conv_id] = []

        self.memory[conv_id].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })

        # 限制memory大小（保留最近50条消息）
        if len(self.memory[conv_id]) > 50:
            # 保留system prompt
            system_messages = [msg for msg in self.memory[conv_id] if msg['role'] == 'system']
            recent_messages = [msg for msg in self.memory[conv_id] if msg['role'] != 'system'][-49:]
            self.memory[conv_id] = system_messages + recent_messages

    def clear_memory(self, conversation_id: Optional[str] = None):
        """
        清除对话记忆

        Args:
            conversation_id: 对话ID，如果为None则清除所有
        """
        if conversation_id:
            self.memory.pop(conversation_id, None)
        else:
            self.memory.clear()

    async def _search_knowledge_base(self, query: str) -> str:
        """
        从知识库检索相关信息

        Args:
            query: 查询文本

        Returns:
            检索到的相关文本
        """
        if not self.knowledge_bases:
            return ""

        try:
            # TODO: 实现实际的知识库检索逻辑
            # 这里需要调用 langchainhandler 或向量数据库
            from langchainhandler import getvectorkm_String

            kb_results = []
            for kb in self.knowledge_bases:
                kb_id = kb.get('id') or kb.get('name')
                try:
                    result = getvectorkm_String(kb_id, query)
                    if result:
                        kb_results.append(f"[来自知识库 {kb.get('name', kb_id)}]\n{result}")
                except Exception as e:
                    logger.error(f"检索知识库 {kb_id} 失败: {e}")

            return "\n\n".join(kb_results) if kb_results else ""
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return ""

    def _prepare_tools_schema(self) -> List[Dict[str, Any]]:
        """
        准备工具定义schema（OpenAI function calling格式）

        Returns:
            工具定义列表
        """
        if not self.tools:
            return []

        tools_schema = []
        for tool in self.tools:
            try:
                tool_name = tool.get('name', '')

                # 尝试从tool_executor获取签名
                signature = tool_executor.get_tool_signature(tool_name)
                if signature:
                    tool_def = {
                        "type": "function",
                        "function": signature
                    }
                else:
                    # 使用配置中的定义
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
                logger.error(f"准备工具schema失败: {e}")

        return tools_schema

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            工具执行结果
        """
        try:
            # 检查是否是代码执行请求
            if tool_name == 'execute_python_code' and self.code_executor:
                code = tool_args.get('code', '')
                result = self.code_executor.execute_python(code)
                return json.dumps(result, ensure_ascii=False)

            if tool_name == 'execute_shell_command' and self.code_executor:
                command = tool_args.get('command', '')
                result = self.code_executor.execute_shell(command)
                return json.dumps(result, ensure_ascii=False)

            # 使用tool_executor执行工具
            result = await asyncio.to_thread(
                tool_executor.execute_tool,
                tool_name,
                **tool_args
            )

            return result

        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            return f"工具执行错误: {str(e)}"

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        use_memory: bool = True,
        use_knowledge_base: bool = True,
        stream: bool = False
    ) -> str:
        """
        非流式问答

        Args:
            message: 用户消息
            conversation_id: 对话ID
            use_memory: 是否使用memory
            use_knowledge_base: 是否使用知识库
            stream: 是否流式（此方法仅非流式）

        Returns:
            Agent回复
        """
        if not self.client:
            return "Error: LLM客户端未配置"

        try:
            # 构建消息列表
            messages = []

            # 添加system prompt
            system_prompt = self.get_system_prompt()

            # 如果使用知识库，先检索相关信息
            if use_knowledge_base and self.knowledge_bases:
                kb_context = await self._search_knowledge_base(message)
                if kb_context:
                    system_prompt += f"\n\n以下是相关的知识库信息：\n{kb_context}"

            messages.append({
                'role': 'system',
                'content': system_prompt
            })

            # 添加历史对话（如果使用memory）
            if use_memory:
                history = self._get_conversation_memory(conversation_id)
                # 只添加user和assistant消息，不包括system
                for msg in history:
                    if msg['role'] in ['user', 'assistant']:
                        messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })

            # 添加当前用户消息
            messages.append({
                'role': 'user',
                'content': message
            })

            # 准备工具
            tools = self._prepare_tools_schema()

            # 调用LLM
            kwargs = {
                'model': self.get_model_name(),
                'messages': messages,
                'temperature': self.get_temperature(),
                'max_tokens': self.get_max_tokens()
            }

            if tools:
                kwargs['tools'] = tools
                kwargs['tool_choice'] = 'auto'

            response = await self.client.chat.completions.create(**kwargs)

            # 处理响应
            assistant_message = response.choices[0].message

            # 处理工具调用
            if assistant_message.tool_calls:
                # 收集工具调用结果
                tool_messages = []
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_result = await self._execute_tool(tool_name, tool_args)

                    tool_messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call.id,
                        'name': tool_name,
                        'content': str(tool_result)
                    })

                # 添加assistant消息和工具消息，再次调用LLM
                messages.append({
                    'role': 'assistant',
                    'content': assistant_message.content or '',
                    'tool_calls': [
                        {
                            'id': tc.id,
                            'type': 'function',
                            'function': {
                                'name': tc.function.name,
                                'arguments': tc.function.arguments
                            }
                        } for tc in assistant_message.tool_calls
                    ]
                })
                messages.extend(tool_messages)

                # 再次调用LLM获取最终回复
                response = await self.client.chat.completions.create(
                    model=self.get_model_name(),
                    messages=messages,
                    temperature=self.get_temperature(),
                    max_tokens=self.get_max_tokens()
                )

                reply = response.choices[0].message.content or ""
            else:
                reply = assistant_message.content or ""

            # 保存到memory
            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', reply, conversation_id)

            return reply

        except Exception as e:
            logger.error(f"Agent问答失败: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        use_memory: bool = True,
        use_knowledge_base: bool = True
    ) -> AsyncIterator[str]:
        """
        流式问答

        Args:
            message: 用户消息
            conversation_id: 对话ID
            use_memory: 是否使用memory
            use_knowledge_base: 是否使用知识库

        Yields:
            流式返回的文本片段
        """
        if not self.client:
            error_msg = (
                f"Agent '{self.name}' 的LLM客户端未配置。"
                f"请在前端Agent聊天界面的顶部工具栏中选择一个有效的模型配置。"
                f"如果没有可选的模型，请先在'模型管理'页面添加模型配置。"
            )
            logger.error(error_msg)
            yield f"Error: {error_msg}"
            return

        try:
            # 构建消息列表（同chat方法）
            messages = []

            # 添加system prompt
            system_prompt = self.get_system_prompt()

            # 如果使用知识库，先检索相关信息
            if use_knowledge_base and self.knowledge_bases:
                kb_context = await self._search_knowledge_base(message)
                if kb_context:
                    system_prompt += f"\n\n以下是相关的知识库信息：\n{kb_context}"

            messages.append({
                'role': 'system',
                'content': system_prompt
            })

            # 添加历史对话
            if use_memory:
                history = self._get_conversation_memory(conversation_id)
                for msg in history:
                    if msg['role'] in ['user', 'assistant']:
                        messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })

            # 添加当前用户消息
            messages.append({
                'role': 'user',
                'content': message
            })

            # 准备工具
            tools = self._prepare_tools_schema()

            # 调用LLM（流式）
            kwargs = {
                'model': self.get_model_name(),
                'messages': messages,
                'temperature': self.get_temperature(),
                'max_tokens': self.get_max_tokens(),
                'stream': True
            }

            if tools:
                kwargs['tools'] = tools
                kwargs['tool_choice'] = 'auto'

            stream = await self.client.chat.completions.create(**kwargs)

            # 收集完整回复
            full_reply = ""
            tool_calls_data = []

            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # 处理内容
                if delta.content:
                    full_reply += delta.content
                    yield delta.content

                # 处理工具调用
                if delta.tool_calls:
                    tool_calls_data.extend(delta.tool_calls)

            # 如果有工具调用，执行工具并获取最终回复
            if tool_calls_data:
                # TODO: 处理工具调用的流式场景
                # 这里可以先执行工具，然后再次流式调用LLM
                pass

            # 保存到memory
            if use_memory:
                self._add_to_memory('user', message, conversation_id)
                self._add_to_memory('assistant', full_reply, conversation_id)

            # 保存到数据库（优化：使用单个session进行批量操作）
            if conversation_id:
                try:
                    from backend.database.base import get_session
                    from backend.database.models.chat import AIChatMessages

                    session = get_session()
                    try:
                        # 检查是否是新对话
                        is_new_conversation = not session.query(AIChatMessages).filter_by(
                            conversation_id=conversation_id,
                            is_first=True
                        ).first()

                        messages_to_save = []
                        current_time = datetime.now()

                        if is_new_conversation:
                            # 保存用户消息作为对话标题
                            messages_to_save.append(AIChatMessages(
                                conversation_id=conversation_id,
                                flag=0,  # 0=send
                                title=message[:50] if len(message) > 50 else message,
                                content=message,
                                owner_name="User",
                                owner_account="user",
                                friend_name=self.name,
                                friend_account=str(self.agent_id),
                                is_first=True,
                                create_time=current_time
                            ))
                        else:
                            # 保存普通用户消息
                            messages_to_save.append(AIChatMessages(
                                conversation_id=conversation_id,
                                flag=0,  # 0=send
                                content=message,
                                owner_name="User",
                                owner_account="user",
                                friend_name=self.name,
                                friend_account=str(self.agent_id),
                                is_first=False,
                                create_time=current_time
                            ))

                        # 保存AI回复
                        messages_to_save.append(AIChatMessages(
                            conversation_id=conversation_id,
                            flag=1,  # 1=receive
                            content=full_reply,
                            owner_name="User",
                            owner_account="user",
                            friend_name=self.name,
                            friend_account=str(self.agent_id),
                            is_first=False,
                            create_time=current_time
                        ))

                        # 批量保存
                        session.add_all(messages_to_save)
                        session.commit()
                        logger.info(f"已保存对话记录到数据库: conversation_id={conversation_id}, count={len(messages_to_save)}")

                    except Exception as save_error:
                        session.rollback()
                        logger.error(f"保存对话记录到数据库失败: {save_error}", exc_info=True)
                    finally:
                        session.close()

                except Exception as e:
                    logger.error(f"数据库连接失败: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Agent流式问答失败: {e}", exc_info=True)
            yield f"Error: {str(e)}"

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Agent信息字典
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
