"""
Agent 和 AI 交互相关的 Mixin
包含与 AI Agent 的对话、指令获取、任务规划等功能
"""
import logging
import json
import asyncio
import re
from typing import List, Dict, Optional
from db.DBFactory import get_prompt_by_title
from backend.apps.sns.adapter.agent_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class AgentInteractionMixin:

    def get_agent_adapter(self) -> AgentAdapter:
        agent_adapter = getattr(self, "agent_adapter", None)
        if agent_adapter is None:
            agent_adapter = AgentAdapter()
            setattr(self, "agent_adapter", agent_adapter)
        return agent_adapter

    def get_agent_for_current_chat(self, *, command_status: Optional[str] = None):
        agent_adapter = self.get_agent_adapter()

        if hasattr(self.ai_chat_cfg, 'agent_id') and self.ai_chat_cfg.agent_id:
            agent = agent_adapter.get_agent_for_ai_chat_cfg(self.ai_chat_cfg, command_status=command_status)
            if not agent:
                logger.error(f"Failed to load agent with ID: {self.ai_chat_cfg.agent_id}")
                return None
            self.agent = agent
            return agent

        logger.warning("No agent_id configured in ai_chat_cfg")
        return None

    async def chat_with_agent(
        self,
        message: str,
        *,
        conversation_suffix: str,
        use_tools: bool,
        use_memory: bool = False,
        use_knowledge_base: bool = False,
        command_status: Optional[str] = None,
        agent=None,
    ) -> str:
        agent_adapter = self.get_agent_adapter()
        if agent is None:
            agent = self.get_agent_for_current_chat(command_status=command_status)
        if agent is None:
            raise RuntimeError("agent not configured for current user")

        reply = await agent_adapter.chat(
            agent=agent,
            message=message,
            conversation_id=agent_adapter.build_conversation_id(prefix="sns", suffix=conversation_suffix),
            use_tools=use_tools,
            use_memory=use_memory,
            use_knowledge_base=use_knowledge_base,
        )
        return reply

    # a.请求agent指示
    async def ask_agent_and_get_instruction(self, question, system_role_prompt, type_flag="command"):
        if self.stopping_ai_process_flag:
            self.stop_AI_process_finished()
            return

        command_status = self.command_status
        title_str = "Ask agent to get instruction"
        content_str = f"""🟪 *The function is*:

ask_agent_and_get_instruction

🟦 *The Command_status is*:

{command_status}

🟩 *The system_role_prompt is*:

{system_role_prompt}

🟨 *The content send to ai llm is*:

{question} 
    """

        self.write_thinking_process_to_pane(title_str, content_str)

        agent_adapter = self.get_agent_adapter()

        self.agent = self.get_agent_for_current_chat(command_status=command_status)
        if not self.agent:
            return

        agent = self.agent
        # agent.give_it_plugin(pluginname)#使用配置里面的第一个
        # agent.give_it_km(vector_path, embedding_model_name)
        self.messages_command = []
        self.messages_command.append({"role": "user", "content": question})

        if self.messages_command[0]["role"] != "system":
            self.messages_command.insert(0, {"role": "system", "content": f"{system_role_prompt}"})
        else:
            self.messages_command[0]["content"] = system_role_prompt

        messages = self.messages_command
        # 保存原始system prompt
        original_prompt = agent.role_config.get('system_prompt', '')

        modified_prompt = agent_adapter.build_system_prompt(
            system_role_prompt=system_role_prompt,
            original_prompt=original_prompt,
            ai_chat_cfg=getattr(self, "ai_chat_cfg", None),
            command_status=command_status,
            agent=agent,
        )

        # 临时修改system prompt
        agent.role_config['system_prompt'] = modified_prompt

        restore_role = agent_adapter.apply_role_config_overrides(
            agent=agent,
            overrides=agent_adapter.get_role_config_overrides_for_command_status(
                command_status=command_status,
                ai_chat_cfg=getattr(self, "ai_chat_cfg", None),
                agent=agent,
            ),
        )

        try:
            # 调用Agent进行对话
            use_tools = getattr(getattr(self, "ai_chat_cfg", None), "use_tools", None)
            if use_tools is None:
                use_tools = getattr(self, "use_tools", None)
            reply = await agent_adapter.chat(
                agent=agent,
                message=question,
                conversation_id=agent_adapter.build_conversation_id(prefix="sns", suffix="cjrtesting"),
                use_tools=use_tools,
                use_memory=False,
                use_knowledge_base=False,
            )
            # return reply
        finally:
            # 恢复原始system prompt
            agent.role_config['system_prompt'] = original_prompt
            restore_role()

        self.on_agent_return_instruction(question, reply)

        agent.role_config['system_prompt'] = original_prompt

    # b.agent返回指示
    def on_agent_return_instruction(self, question, content):
        self.agent_replying_flag = False
        if self.stopping_ai_process_flag:
            self.stop_AI_process_finished()
            return
        # content = content.strip('```json').strip('```').strip()
        content = re.sub(r'^\s*```json\s*|\s*```\s*$', '', content, flags=re.DOTALL)
        command_status = self.command_status
        title_str = "Agent return the instruction"
        content_str = f"""🟪 *The function is*:

on_agent_return_instruction

🟫 *The Content Returned is*:

{content}
            """

        self.write_thinking_process_to_pane(title_str, content_str)

        # self.loading_tab.stop_loading()

        if command_status == "ask_agent_instruction_to_process_activity":
            asyncio.create_task(self.taskmng.process_task(event="agent_instruction_to_process_activity_returned", instruction=content))

        elif command_status == "ask_agent_instruction_to_process_human_instruction":
            asyncio.create_task(self.taskmng.process_task(event="agent_instruction_to_process_human_instruction_returned", instruction=content))

        elif command_status == "ask_agent_to_review_conversation":
            asyncio.create_task(self.taskmng.process_task(event="ask_agent_to_review_conversation_returned", result=content))

        elif command_status == "ask_agent_to_review_conversation_sell":
            asyncio.create_task(self.taskmng.process_task(event="ask_agent_to_review_conversation_sell_returned", result=content))

        elif command_status == "ask_agent_to_review_conversation_buy":
            asyncio.create_task(self.taskmng.process_task(event="ask_agent_to_review_conversation_buy_returned", result=content))

        elif command_status == "ask_agent_start_to_talk_to_a_people":
            asyncio.create_task(self.taskmng.process_task(event="ask_agent_start_to_talk_to_a_people_returned", result=content))

        elif command_status == "ask_agent_start_to_sell_to_a_people":
            asyncio.create_task(self.taskmng.process_task(event="ask_agent_start_to_sell_to_a_people_returned", result=content))

        elif command_status == "ask_agent_start_to_buy_from_a_people":
            asyncio.create_task(self.taskmng.process_task(event="ask_agent_start_to_buy_from_a_people_returned", result=content))


        elif command_status == "ask_agent_to_use_service":
            self.on_ask_agent_to_use_service_return(content)

        elif command_status == "run_tool_before_send_good":
            self.handle_send_goods(content)

        else:
            pass

        # self.loading_tab.stop_loading()

