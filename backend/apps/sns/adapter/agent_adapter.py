"""Agent adapter for SNS module.

This file is intended as the customization point for how SNS talks to the Agent module.
"""

import logging
import json
from typing import Optional, Callable, Dict, Any, Tuple

import httpx

from backend.modules.agent.agent_manager import agent_manager
from backend.database.base import get_session
from backend.database.models.agent import AgentCfg

logger = logging.getLogger(__name__)


class AgentAdapter:
    def __init__(self):
        self._command_status_agent_resolvers: Dict[str, Callable[..., Optional[str]]] = {}
        self._command_status_role_overrides: Dict[str, Callable[..., Dict[str, Any]]] = {}
        self._command_status_prompt_builders: Dict[str, Callable[..., str]] = {}
        self._register_builtin_handlers()

    def register_command_status_agent_resolver(self, command_status: str, resolver: Callable[..., Optional[str]]):
        self._command_status_agent_resolvers[command_status] = resolver

    def register_command_status_role_overrides(self, command_status: str, provider: Callable[..., Dict[str, Any]]):
        self._command_status_role_overrides[command_status] = provider

    def register_command_status_prompt_builder(self, command_status: str, builder: Callable[..., str]):
        self._command_status_prompt_builders[command_status] = builder

    def _register_builtin_handlers(self):
        self.register_command_status_agent_resolver(
            "moderation",
            self._moderation_agent_resolver,
        )
        self.register_command_status_role_overrides(
            "moderation",
            self._moderation_role_overrides,
        )
        self.register_command_status_prompt_builder(
            "moderation",
            self._moderation_prompt_builder,
        )

    # ===== moderation handlers =====

    def _moderation_agent_resolver(self, *, command_status, ai_chat_cfg):
        return "moderation_agent"

    def _moderation_role_overrides(self, *, command_status, ai_chat_cfg, agent):
        return {
            "temperature": 0.0,
            "style": "strict",
        }

    def _moderation_prompt_builder(
            self,
            *,
            command_status,
            system_role_prompt,
            original_prompt,
            ai_chat_cfg,
            agent,
    ):
        return f"MODERATION MODE:\n{original_prompt}"



    def get_agent_by_identifier(self, agent_identifier: str):
        if not agent_identifier:
            return None
        if str(agent_identifier).isdigit():
            return agent_manager.get_agent_by_id(int(agent_identifier))
        return agent_manager.get_agent_by_name(str(agent_identifier))

    def _is_remote_agent_type(self, agent_type: str) -> bool:
        t = str(agent_type or '').strip().lower()
        return t in {'remote', 'remoteagent', 'remote_agent', 'remote agent', 'remote-agent'}

    def _normalize_a2a_rpc_url(self, url: str) -> str:
        u = str(url or '').strip()
        if not u:
            return ''
        if u.endswith('/rpc'):
            return u
        if u.endswith('/'):
            return u + 'rpc'
        return u + '/rpc'

    def _load_agent_type_and_url(self, agent_identifier: str) -> Tuple[str, str]:
        identifier = str(agent_identifier or '').strip()
        if not identifier:
            return 'local', ''

        db = get_session()
        try:
            row = None
            if identifier.isdigit():
                row = db.query(AgentCfg).filter(
                    AgentCfg.id == int(identifier),
                    AgentCfg.is_delete == False,
                ).first()
            else:
                row = db.query(AgentCfg).filter(
                    AgentCfg.name == identifier,
                    AgentCfg.is_delete == False,
                ).first()

            if not row:
                return 'local', ''

            extra_data = {}
            try:
                if row.memo:
                    extra_data = json.loads(row.memo)
            except Exception:
                extra_data = {}

            return str(extra_data.get('agent_type') or 'local'), str(extra_data.get('url') or '')
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _extract_text_from_a2a_message(self, message_obj: dict) -> str:
        if not isinstance(message_obj, dict):
            return ''
        parts = message_obj.get('parts')
        if not isinstance(parts, list):
            return ''
        texts = []
        for part in parts:
            if not isinstance(part, dict):
                continue

            t = part.get('text')
            if isinstance(t, str) and t:
                texts.append(t)
                continue

            data = part.get('data')
            if not isinstance(data, dict):
                continue
            choices = data.get('choices')
            if not isinstance(choices, list) or not choices:
                continue
            choice0 = choices[0]
            if not isinstance(choice0, dict):
                continue

            msg = choice0.get('message')
            if isinstance(msg, dict):
                c = msg.get('content')
                if isinstance(c, str) and c:
                    texts.append(c)
                    continue

            delta = choice0.get('delta')
            if isinstance(delta, dict):
                c = delta.get('content')
                if isinstance(c, str) and c:
                    texts.append(c)
                    continue

        return ''.join(texts)

    async def _remote_send_message(self, *, rpc_url: str, text: str, context_id: str) -> str:
        rpc_url = self._normalize_a2a_rpc_url(rpc_url)
        if not rpc_url:
            return 'Error: A2A Endpoint URL is empty'

        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'SendMessage',
            'params': {
                'stream': False,
                'message': {
                    'contextId': context_id,
                    'parts': [{'text': text}]
                }
            }
        }

        timeout = httpx.Timeout(60.0, read=60.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                resp = await client.post(
                    rpc_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                )
        except httpx.TimeoutException:
            return 'Error: Remote agent timeout'
        except httpx.HTTPError as e:
            return f'Error: Remote agent network error: {str(e)}'

        if resp.status_code >= 400:
            return f'Error: Remote agent error: HTTP {resp.status_code}: {resp.text[:500]}'

        try:
            data = resp.json()
        except Exception:
            return f'Error: Remote agent returned non-JSON response: {resp.text[:500]}'

        if isinstance(data, dict) and data.get('error'):
            return f"Error: Remote agent RPC error: {json.dumps(data.get('error'), ensure_ascii=False)}"

        result = data.get('result') if isinstance(data, dict) else None
        message_obj = (result or {}).get('message') if isinstance(result, dict) else None
        return self._extract_text_from_a2a_message(message_obj or {})

    def get_agent_identifier_for_command_status(self, *, command_status: str, ai_chat_cfg=None) -> Optional[str]:
        resolver = self._command_status_agent_resolvers.get(command_status)
        if resolver is None:
            return None
        try:
            return resolver(command_status=command_status, ai_chat_cfg=ai_chat_cfg)
        except Exception as e:
            logger.error(f"command_status resolver failed: {e}", exc_info=True)
            return None

    def get_role_config_overrides_for_command_status(
        self,
        *,
        command_status: str,
        ai_chat_cfg=None,
        agent=None,
    ) -> Dict[str, Any]:
        provider = self._command_status_role_overrides.get(command_status)
        if provider is None:
            return {}
        try:
            overrides = provider(command_status=command_status, ai_chat_cfg=ai_chat_cfg, agent=agent)
            return overrides if isinstance(overrides, dict) else {}
        except Exception as e:
            logger.error(f"command_status role overrides failed: {e}", exc_info=True)
            return {}

    def apply_role_config_overrides(self, *, agent, overrides: Dict[str, Any]):
        original = {}
        if not overrides:
            return lambda: None
        for key, value in overrides.items():
            original[key] = agent.role_config.get(key)
            agent.role_config[key] = value

        def _restore():
            for key, value in original.items():
                if value is None:
                    agent.role_config.pop(key, None)
                else:
                    agent.role_config[key] = value

        return _restore

    def get_agent_for_ai_chat_cfg(self, ai_chat_cfg, *, command_status: Optional[str] = None):
        if command_status:
            agent_identifier = self.get_agent_identifier_for_command_status(
                command_status=command_status,
                ai_chat_cfg=ai_chat_cfg,
            )
            if agent_identifier:
                agent = self.get_agent_by_identifier(agent_identifier)
                if agent is not None:
                    return agent
        agent_id = getattr(ai_chat_cfg, "agent_id", None)
        if not agent_id:
            return None
        return agent_manager.get_agent_by_id(agent_id)

    def build_conversation_id(self, *, prefix: str = "sns", suffix: str = "agent_conversation") -> str:
        return f"{prefix}_{suffix}"

    def build_system_prompt(
        self,
        *,
        system_role_prompt: str,
        original_prompt: str,
        ai_chat_cfg=None,
        command_status: Optional[str] = None,
        agent=None,
    ) -> str:
        if command_status:
            builder = self._command_status_prompt_builders.get(command_status)
            if builder is not None:
                try:
                    return builder(
                        command_status=command_status,
                        system_role_prompt=system_role_prompt,
                        original_prompt=original_prompt,
                        ai_chat_cfg=ai_chat_cfg,
                        agent=agent,
                    )
                except Exception as e:
                    logger.error(f"command_status prompt builder failed: {e}", exc_info=True)
        return system_role_prompt

    async def chat(
        self,
        *,
        agent,
        message: str,
        conversation_id: str,
        use_tools: Optional[bool] = None,
        use_memory: bool = False,
        use_knowledge_base: bool = False,
    ):
        agent_type, rpc_url = self._load_agent_type_and_url(str(getattr(agent, 'agent_id', '') or ''))
        if self._is_remote_agent_type(agent_type):
            system_prompt = ''
            try:
                rc = getattr(agent, 'role_config', None)
                if isinstance(rc, dict):
                    system_prompt = str(rc.get('system_prompt') or '').strip()
            except Exception:
                system_prompt = ''

            send_text = message
            if system_prompt:
                send_text = system_prompt + "\n\n" + message
            return await self._remote_send_message(
                rpc_url=rpc_url,
                text=send_text,
                context_id=conversation_id or 'sns',
            )
        kwargs = {
            "message": message,
            "conversation_id": conversation_id,
            "use_memory": use_memory,
            "use_knowledge_base": use_knowledge_base,
        }
        if use_tools is not None:
            kwargs["use_tools"] = use_tools
        return await agent.chat(**kwargs)
