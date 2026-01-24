# -*- coding: utf-8 -*-
"""
SNS AI Service - 为SNS模块提供AI对话服务
"""
import logging
from typing import Optional
from backend.modules.agent.agent_manager import agent_manager

logger = logging.getLogger(__name__)


class SNSAIService:
    """SNS AI服务类"""

    @staticmethod
    async def chat_with_agent(
        agent_identifier: str,
        message: str,
        mode: str = "ai"
    ) -> str:
        """
        与Agent对话

        Args:
            agent_identifier: Agent ID或名称
            message: 用户消息
            mode: 对话模式 ("ai" 或 "friends")

        Returns:
            Agent回复
        """
        try:
            # 获取Agent实例
            agent = None
            if agent_identifier.isdigit():
                agent = agent_manager.get_agent_by_id(int(agent_identifier))
            else:
                agent = agent_manager.get_agent_by_name(agent_identifier)

            if not agent:
                return f"Error: Agent '{agent_identifier}' not found"

            # 保存原始system prompt
            original_prompt = agent.role_config.get('system_prompt', '')

            # 根据mode修改system prompt
            if mode == "ai":
                modified_prompt = "我是你的AI助手。" + original_prompt
            else:  # friends
                modified_prompt = "我是你的朋友。" + original_prompt

            # 临时修改system prompt
            agent.role_config['system_prompt'] = modified_prompt

            try:
                # 调用Agent进行对话
                reply = await agent.chat(
                    message=message,
                    conversation_id=f"sns_{mode}",
                    use_memory=False,
                    use_knowledge_base=False
                )
                return reply
            finally:
                # 恢复原始system prompt
                agent.role_config['system_prompt'] = original_prompt

        except Exception as e:
            logger.error(f"SNS AI chat failed: {e}", exc_info=True)
            return f"Error: {str(e)}"
