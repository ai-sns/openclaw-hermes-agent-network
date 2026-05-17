"""Agent adapter for SNS module.

This file is intended as the customization point for how SNS talks to the Agent module.
"""

import logging
import json
import os
import time
from typing import Optional, Callable, Dict, Any, Tuple

import httpx

from runtime.modules.agent.agent_manager import agent_manager
from db.database import get_db_session as get_session
from db.models.agent import AgentCfg
from runtime.shared.llm_log_writer import (
    new_request_id,
    log_llm_request,
    log_llm_response,
    log_llm_stream_chunk,
    log_llm_error,
)

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

    def _moderation_agent_resolver(self, *, command_status, aisns_cfg):
        return "moderation_agent"

    def _moderation_role_overrides(self, *, command_status, aisns_cfg, agent):
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
            aisns_cfg,
            agent,
    ):
        return f"MODERATION MODE:\n{original_prompt}"



    def get_agent_by_identifier(self, agent_identifier: str):
        if not agent_identifier:
            return None

        identifier = str(agent_identifier)
        if self._use_isolated_agent_instance():
            agent_id = self._resolve_agent_id(identifier)
            if not agent_id:
                return None
            return agent_manager.build_agent_instance(int(agent_id))

        if identifier.isdigit():
            return agent_manager.get_agent_by_id(int(identifier))
        return agent_manager.get_agent_by_name(identifier)

    def _use_isolated_agent_instance(self) -> bool:
        v = str(os.environ.get('SNS_USE_ISOLATED_AGENT_INSTANCE', '')).strip().lower()
        return v in {'1', 'true', 'yes', 'y', 'on'}

    def _resolve_agent_id(self, agent_identifier: str) -> Optional[int]:
        identifier = str(agent_identifier or '').strip()
        if not identifier:
            return None
        if identifier.isdigit():
            try:
                return int(identifier)
            except Exception:
                return None

        db = get_session()
        try:
            row = db.query(AgentCfg).filter(
                AgentCfg.name == identifier,
                AgentCfg.is_delete == False,
            ).first()
            if not row:
                return None
            return int(row.id)
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _extract_delta_text_from_a2a_event(self, event_obj: dict) -> str:
        if not isinstance(event_obj, dict):
            return ''
        result = event_obj.get('result')
        if not isinstance(result, dict):
            return ''
        message_obj = result.get('message')
        if not isinstance(message_obj, dict):
            return ''
        parts = message_obj.get('parts')
        if not isinstance(parts, list):
            return ''

        for part in parts:
            if not isinstance(part, dict):
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
            delta = choice0.get('delta')
            if not isinstance(delta, dict):
                continue
            c = delta.get('content')
            if isinstance(c, str) and c:
                return c
        return ''

    def _is_remote_agent_type(self, agent_type: str) -> bool:
        t = str(agent_type or '').strip().lower()
        return t in {'remote', 'remoteagent', 'remote_agent', 'remote agent', 'remote-agent'}

    def is_agent_remote(self, agent_identifier) -> bool:
        """Return True if the agent identified by *agent_identifier* is a remote agent."""
        identifier = str(agent_identifier or '').strip()
        if not identifier:
            return False
        agent_type, _url = self._load_agent_type_and_url(identifier)
        return self._is_remote_agent_type(agent_type)

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

    def _extract_finish_reason_from_a2a_event(self, event_obj: dict) -> Optional[str]:
        if not isinstance(event_obj, dict):
            return None
        result = event_obj.get('result')
        if not isinstance(result, dict):
            return None
        message_obj = result.get('message')
        if not isinstance(message_obj, dict):
            return None
        parts = message_obj.get('parts')
        if not isinstance(parts, list):
            return None

        for part in parts:
            if not isinstance(part, dict):
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
            fr = choice0.get('finish_reason')
            if fr is None:
                continue
            return str(fr)
        return None

    async def _remote_collect_stream_text(self, *, rpc_url: str, text: str, context_id: str) -> str:
        rpc_url = self._normalize_a2a_rpc_url(rpc_url)
        if not rpc_url:
            return ''

        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'SendMessage',
            'params': {
                'stream': True,
                'message': {
                    'contextId': context_id,
                    'parts': [{'text': text}]
                }
            }
        }

        req_id = new_request_id()
        _log_source = "runtime.apps.sns.adapter.agent_adapter.AgentAdapter._remote_collect_stream_text"
        try:
            log_llm_request(
                request_id=req_id, source=_log_source,
                request_json={"rpc_url": rpc_url, "payload": payload},
            )
        except Exception:
            pass

        timeout = httpx.Timeout(60.0, read=300.0)
        out_parts = []
        seen_content = False
        last_content_ts = time.monotonic()
        idle_timeout_after_content_seconds = 120.0

        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                async with client.stream(
                    'POST',
                    rpc_url,
                    json=payload,
                    headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
                ) as resp:
                    if resp.status_code >= 400:
                        try:
                            log_llm_error(request_id=req_id, source=_log_source, error=f"HTTP {resp.status_code}")
                        except Exception:
                            pass
                        return ''

                    content_type = str(resp.headers.get('content-type') or '').lower()
                    if 'text/event-stream' not in content_type:
                        body = await resp.aread()
                        text_body = ''
                        try:
                            text_body = body.decode('utf-8', errors='ignore')
                        except Exception:
                            text_body = str(body)

                        try:
                            data = json.loads(text_body) if text_body else {}
                        except Exception:
                            data = {}
                        result = data.get('result') if isinstance(data, dict) else None
                        message_obj = (result or {}).get('message') if isinstance(result, dict) else None
                        extracted = self._extract_text_from_a2a_message(message_obj or {})
                        try:
                            log_llm_response(request_id=req_id, source=_log_source, response_json={"content": extracted})
                        except Exception:
                            pass
                        return extracted

                    async for line in resp.aiter_lines():
                        now = time.monotonic()
                        if seen_content and (now - last_content_ts) > idle_timeout_after_content_seconds:
                            break
                        if not line:
                            continue
                        s = line.strip()
                        if not s:
                            continue
                        # SSE comment lines (e.g. ': heartbeat') are keep-alive
                        # signals from the adapter; reset the idle timer but skip.
                        if s.startswith(':'):
                            last_content_ts = now
                            continue
                        if s.startswith('data:'):
                            s = s[5:].strip()
                        if s == '[DONE]':
                            break
                        try:
                            evt = json.loads(s)
                        except Exception:
                            continue

                        if isinstance(evt, dict) and evt.get('error'):
                            try:
                                log_llm_error(request_id=req_id, source=_log_source, error=evt.get('error'))
                            except Exception:
                                pass
                            return ''

                        delta = self._extract_delta_text_from_a2a_event(evt)
                        if delta:
                            out_parts.append(delta)
                            seen_content = True
                            last_content_ts = time.monotonic()
                            try:
                                log_llm_stream_chunk(request_id=req_id, source=_log_source, stream_raw={"content": delta})
                            except Exception:
                                pass
                        else:
                            result = evt.get('result') if isinstance(evt, dict) else None
                            message_obj = (result or {}).get('message') if isinstance(result, dict) else None
                            chunk_text = self._extract_text_from_a2a_message(message_obj or {})
                            if chunk_text:
                                out_parts.append(chunk_text)
                                seen_content = True
                                last_content_ts = time.monotonic()
                                try:
                                    log_llm_stream_chunk(request_id=req_id, source=_log_source, stream_raw={"content": chunk_text})
                                except Exception:
                                    pass

                        fr = self._extract_finish_reason_from_a2a_event(evt)
                        if fr:
                            break
        except Exception:
            try:
                log_llm_error(request_id=req_id, source=_log_source, error="stream collection exception")
            except Exception:
                pass
            return ''

        joined = ''.join(out_parts)
        try:
            log_llm_response(request_id=req_id, source=_log_source, response_json={"content": joined})
        except Exception:
            pass
        return joined

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

        req_id = new_request_id()
        _log_source = "runtime.apps.sns.adapter.agent_adapter.AgentAdapter._remote_send_message"
        try:
            log_llm_request(
                request_id=req_id, source=_log_source,
                request_json={"rpc_url": rpc_url, "payload": payload},
            )
        except Exception:
            pass

        timeout = httpx.Timeout(60.0, read=300.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                resp = await client.post(
                    rpc_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                )
        except httpx.TimeoutException:
            try:
                log_llm_error(request_id=req_id, source=_log_source, error="Remote agent timeout")
            except Exception:
                pass
            return 'Error: Remote agent timeout'
        except httpx.HTTPError as e:
            try:
                log_llm_error(request_id=req_id, source=_log_source, error=f"Remote agent network error: {str(e)}")
            except Exception:
                pass
            return f'Error: Remote agent network error: {str(e)}'

        if resp.status_code >= 400:
            try:
                log_llm_error(request_id=req_id, source=_log_source, error=f"HTTP {resp.status_code}: {resp.text[:500]}")
            except Exception:
                pass
            return f'Error: Remote agent error: HTTP {resp.status_code}: {resp.text[:500]}'

        content_type = str(resp.headers.get('content-type') or '').lower()
        if 'text/event-stream' in content_type:
            out_parts = []
            for line in (resp.text or '').splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith('data:'):
                    s = s[5:].strip()
                if s == '[DONE]':
                    break
                try:
                    evt = json.loads(s)
                except Exception:
                    continue

                delta = self._extract_delta_text_from_a2a_event(evt)
                if delta:
                    out_parts.append(delta)
                    try:
                        log_llm_stream_chunk(request_id=req_id, source=_log_source, stream_raw={"content": delta})
                    except Exception:
                        pass
                else:
                    result = evt.get('result') if isinstance(evt, dict) else None
                    message_obj = (result or {}).get('message') if isinstance(result, dict) else None
                    chunk_text = self._extract_text_from_a2a_message(message_obj or {})
                    if chunk_text:
                        out_parts.append(chunk_text)
                        try:
                            log_llm_stream_chunk(request_id=req_id, source=_log_source, stream_raw={"content": chunk_text})
                        except Exception:
                            pass
                fr = self._extract_finish_reason_from_a2a_event(evt)
                if fr:
                    break
            joined = ''.join(out_parts)
            if joined:
                try:
                    log_llm_response(request_id=req_id, source=_log_source, response_json={"content": joined})
                except Exception:
                    pass
                return joined

        try:
            data = resp.json()
        except Exception:
            try:
                log_llm_error(request_id=req_id, source=_log_source, error=f"Non-JSON response: {resp.text[:500]}")
            except Exception:
                pass
            return f'Error: Remote agent returned non-JSON response: {resp.text[:500]}'

        if isinstance(data, dict) and data.get('error'):
            fallback = await self._remote_collect_stream_text(
                rpc_url=rpc_url,
                text=text,
                context_id=context_id,
            )
            if fallback:
                try:
                    log_llm_response(request_id=req_id, source=_log_source, response_json={"content": fallback})
                except Exception:
                    pass
                return fallback
            try:
                log_llm_error(request_id=req_id, source=_log_source, error=json.dumps(data.get('error'), ensure_ascii=False))
            except Exception:
                pass
            return f"Error: Remote agent RPC error: {json.dumps(data.get('error'), ensure_ascii=False)}"

        result = data.get('result') if isinstance(data, dict) else None
        message_obj = (result or {}).get('message') if isinstance(result, dict) else None
        reply = self._extract_text_from_a2a_message(message_obj or {})
        try:
            log_llm_response(request_id=req_id, source=_log_source, response_json={"content": reply})
        except Exception:
            pass
        return reply

    def get_agent_identifier_for_command_status(self, *, command_status: str, aisns_cfg=None) -> Optional[str]:
        resolver = self._command_status_agent_resolvers.get(command_status)
        if resolver is None:
            return None
        try:
            return resolver(command_status=command_status, aisns_cfg=aisns_cfg)
        except Exception as e:
            logger.error(f"command_status resolver failed: {e}", exc_info=True)
            return None

    def get_role_config_overrides_for_command_status(
        self,
        *,
        command_status: str,
        aisns_cfg=None,
        agent=None,
    ) -> Dict[str, Any]:
        provider = self._command_status_role_overrides.get(command_status)
        if provider is None:
            return {}
        try:
            overrides = provider(command_status=command_status, aisns_cfg=aisns_cfg, agent=agent)
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

    def get_agent_for_aisns_cfg(self, aisns_cfg, *, command_status: Optional[str] = None):
        if command_status:
            agent_identifier = self.get_agent_identifier_for_command_status(
                command_status=command_status,
                aisns_cfg=aisns_cfg,
            )
            if agent_identifier:
                agent = self.get_agent_by_identifier(agent_identifier)
                if agent is not None:
                    return agent
        agent_id = getattr(aisns_cfg, "agent_id", None)
        if not agent_id:
            return None

        if self._use_isolated_agent_instance():
            try:
                return agent_manager.build_agent_instance(int(agent_id))
            except Exception:
                return None

        return agent_manager.get_agent_by_id(agent_id)

    def build_conversation_id(self, *, prefix: str = "sns", suffix: str = "agent_conversation") -> str:
        return f"{prefix}_{suffix}"

    def build_system_prompt(
        self,
        *,
        system_role_prompt: str,
        original_prompt: str,
        aisns_cfg=None,
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
                        aisns_cfg=aisns_cfg,
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
        tool_choice: Optional[dict] = None,
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
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        return await agent.chat(**kwargs)
