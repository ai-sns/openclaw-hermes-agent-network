"""
Mixin related to interactions between Agent and AI.
Includes functions such as chatting with AI agents, fetching instructions, and task planning.
"""
import logging
import json
import asyncio
import re
from typing import List, Dict, Optional
from db.DBFactory import get_prompt_by_title
from runtime.apps.sns.adapter.agent_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class AgentInteractionMixin:

    def _format_goods_or_service_and_price(self) -> str:
        cfg = getattr(self, "aisns_cfg_record", None)
        description = (getattr(cfg, "goods_or_service_description", None) or "").strip()
        price = (getattr(cfg, "goods_or_service_price", None) or "").strip()

        if description and price:
            return f"{description}. Price: {price}."
        if description:
            return description
        if price:
            return f"Price: {price}."
        return ""

    def _apply_sns_prompt_placeholders(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text

        cfg = getattr(self, "aisns_cfg_record", None)
        profession = (getattr(cfg, "profession", None) or "").strip()
        goods_or_service_and_price = self._format_goods_or_service_and_price()

        if "__user_profession_to_be_provided__" in text:
            text = text.replace("__user_profession_to_be_provided__", profession)

        if "__goods_or_service_and_price__" in text:
            text = text.replace("__goods_or_service_and_price__", goods_or_service_and_price)

        return text

    def get_agent_adapter(self) -> AgentAdapter:
        agent_adapter = getattr(self, "agent_adapter", None)
        if agent_adapter is None:
            agent_adapter = AgentAdapter()
            setattr(self, "agent_adapter", agent_adapter)
        return agent_adapter

    def is_current_agent_remote(self) -> bool:
        """Return True if the currently configured agent is a remote agent."""
        try:
            agent_id = getattr(self.aisns_cfg, 'agent_id', None)
            if not agent_id:
                return False
            return self.get_agent_adapter().is_agent_remote(agent_id)
        except Exception:
            return False

    def get_agent_for_current_chat(self, *, command_status: Optional[str] = None):
        agent_adapter = self.get_agent_adapter()

        if hasattr(self.aisns_cfg, 'agent_id') and self.aisns_cfg.agent_id:
            agent = agent_adapter.get_agent_for_aisns_cfg(self.aisns_cfg, command_status=command_status)
            if not agent:
                logger.error(f"Failed to load agent with ID: {self.aisns_cfg.agent_id}")
                return None
            self.agent = agent
            return agent

        logger.warning("No agent_id configured in aisns_cfg")
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
        tool_choice: Optional[dict] = None,
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
            tool_choice=tool_choice,
        )
        return reply

    # a. Request agent instruction
    async def ask_agent_and_get_instruction(self, question, system_role_prompt, type_flag="command"):
        if self.stopping_ai_process_flag:
            self.stop_AI_process_finished()
            return

        try:
            self.agent_replying_flag = True
        except Exception:
            pass

        system_role_prompt = self._apply_sns_prompt_placeholders(system_role_prompt)
        question = self._apply_sns_prompt_placeholders(question)

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
            try:
                self.agent_replying_flag = False
            except Exception:
                pass
            return

        agent = self.agent
        # agent.give_it_plugin(pluginname)  # Use the first one in the config
        # agent.give_it_km(vector_path, embedding_model_name)
        self.messages_command = []
        self.messages_command.append({"role": "user", "content": question})

        if self.messages_command[0]["role"] != "system":
            self.messages_command.insert(0, {"role": "system", "content": f"{system_role_prompt}"})
        else:
            self.messages_command[0]["content"] = system_role_prompt

        messages = self.messages_command
        # Save original system prompt
        original_prompt = agent.role_config.get('system_prompt', '')

        modified_prompt = agent_adapter.build_system_prompt(
            system_role_prompt=system_role_prompt,
            original_prompt=original_prompt,
            aisns_cfg=getattr(self, "aisns_cfg", None),
            command_status=command_status,
            agent=agent,
        )

        # Temporarily override system prompt
        agent.role_config['system_prompt'] = modified_prompt

        restore_role = agent_adapter.apply_role_config_overrides(
            agent=agent,
            overrides=agent_adapter.get_role_config_overrides_for_command_status(
                command_status=command_status,
                aisns_cfg=getattr(self, "aisns_cfg", None),
                agent=agent,
            ),
        )

        try:
            # Call agent to chat
            use_tools = False
            tool_choice = "none" if not use_tools else None
            reply = await agent_adapter.chat(
                agent=agent,
                message=question,
                conversation_id=agent_adapter.build_conversation_id(prefix="sns", suffix="cjrtesting"),
                use_tools=use_tools,
                use_memory=False,
                use_knowledge_base=False,
                tool_choice=tool_choice,
            )

            if reply is None:
                reply = ""
            elif not isinstance(reply, str):
                try:
                    reply = str(reply)
                except Exception:
                    reply = ""

            try:
                sanitized = re.sub(r'^\s*```json\s*|\s*```\s*$', '', reply, flags=re.DOTALL)
            except Exception:
                sanitized = reply

            empty_reply = (not isinstance(sanitized, str)) or (not sanitized.strip())
            if empty_reply:
                retry_state = getattr(self, "_empty_agent_reply_retry", None)
                if not isinstance(retry_state, dict):
                    retry_state = {}
                    setattr(self, "_empty_agent_reply_retry", retry_state)

                retry_count = int(retry_state.get(command_status, 0) or 0)
                if retry_count < 1:
                    retry_state[command_status] = retry_count + 1
                    try:
                        self.show_alert_on_map("Agent returned empty output, retrying...", is_error=False)
                    except Exception:
                        pass

                    reply = await agent_adapter.chat(
                        agent=agent,
                        message=question,
                        conversation_id=agent_adapter.build_conversation_id(prefix="sns", suffix="cjrtesting"),
                        use_tools=use_tools,
                        use_memory=False,
                        use_knowledge_base=False,
                        tool_choice=tool_choice,
                    )

                    if reply is None:
                        reply = ""
                    elif not isinstance(reply, str):
                        try:
                            reply = str(reply)
                        except Exception:
                            reply = ""
                else:
                    try:
                        self.show_alert_on_map("Agent returned empty output.", is_error=False)
                    except Exception:
                        pass
        finally:
            # Restore original system prompt
            agent.role_config['system_prompt'] = original_prompt
            restore_role()

        self.on_agent_return_instruction(question, reply, command_status=command_status)

    # b. Agent returns instruction
    def on_agent_return_instruction(self, question, content, *, command_status: Optional[str] = None):
        try:
            self.agent_replying_flag = False
        except Exception:
            pass
        if self.stopping_ai_process_flag:
            self.stop_AI_process_finished()
            return
        if content is None:
            content = ""
        elif not isinstance(content, str):
            try:
                content = str(content)
            except Exception:
                content = ""

        content = re.sub(r'^\s*```json\s*|\s*```\s*$', '', content, flags=re.DOTALL)

        current_status = self.command_status
        # Conversation review statuses are self-contained async operations whose
        # results remain valid even if the game loop has advanced command_status
        # while the LLM was generating.  Do not drop them on mismatch.
        _REVIEW_STATUSES = frozenset({
            "ask_agent_to_review_conversation",
            "ask_agent_to_review_conversation_sell",
            "ask_agent_to_review_conversation_buy",
        })
        if command_status is not None and command_status != current_status:
            if command_status in _REVIEW_STATUSES:
                logger.info(
                    "command_status changed during conversation review (expected=%s current=%s); "
                    "proceeding with review result anyway",
                    command_status,
                    current_status,
                )
                # Keep original command_status for correct dispatch below
            else:
                logger.info(
                    "Dropping agent reply due to command_status mismatch. expected=%s current=%s",
                    command_status,
                    current_status,
                )
                return
        else:
            command_status = current_status
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


        elif command_status == "ask_agent_process_plan_summary":
            asyncio.create_task(self.taskmng.process_task(event="ask_agent_process_plan_summary_returned", result=content))


        elif command_status == "ask_agent_to_use_service":
            self.on_ask_agent_to_use_service_return(content)

        elif command_status == "run_tool_before_send_good":
            self.handle_send_goods(content)

        else:
            pass

        # self.loading_tab.stop_loading()

