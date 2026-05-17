# -*- coding: utf-8 -*-
"""
Agent Chat Router - Agent Q&A API
Supports streaming and non-streaming Q&A, calling agents by ID or name
"""
import logging
import json
import base64
import uuid
import time
from datetime import datetime
from typing import Optional
from typing import List
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agent_manager import agent_manager
from db.database import get_db_session as get_session
from db.models.agent import AgentCfg
from db.models.aisns import AIChatMessages
from runtime.shared.llm_log_writer import (
    new_request_id,
    log_llm_request,
    log_llm_response,
    log_llm_stream_chunk,
    log_llm_error,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_remote_agent_type(agent_type: str) -> bool:
    s = str(agent_type or '').strip().lower()
    return s in {'remote', 'remote agent', 'remote_agent', 'remoteagent'}


def _normalize_a2a_rpc_url(url: str) -> str:
    u = str(url or '').strip()
    if not u:
        return u
    if u.endswith('/rpc/'):
        return u[:-1]
    if u.endswith('/rpc'):
        return u
    return u.rstrip('/') + '/rpc'


def _extract_text_from_a2a_message(message_obj: dict) -> str:
    if not isinstance(message_obj, dict):
        return ''

    parts = message_obj.get('parts')
    if not isinstance(parts, list):
        return ''

    texts: List[str] = []
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


def _load_agent_cfg_by_name(agent_name: str) -> Optional[dict]:
    name = str(agent_name or '').strip()
    if not name:
        return None

    db = get_session()
    try:
        row = db.query(AgentCfg).filter(
            AgentCfg.name == name,
            AgentCfg.is_delete == False
        ).first()
        if not row:
            return None

        extra_data = {}
        try:
            if row.memo:
                extra_data = json.loads(row.memo)
        except Exception:
            extra_data = {}

        return {
            'id': row.id,
            'name': row.name,
            'agent_type': extra_data.get('agent_type', 'local'),
            'url': extra_data.get('url', '')
        }
    finally:
        try:
            db.close()
        except Exception:
            pass


def _save_chat_messages_to_db(
    *,
    conversation_id: str,
    agent_id: Optional[int],
    agent_name: str,
    user_message: str,
    assistant_reply: str,
) -> None:
    if not conversation_id:
        return

    session = get_session()
    try:
        is_new_conversation = not session.query(AIChatMessages).filter_by(
            conversation_id=conversation_id,
            is_first=True,
        ).first()

        now = datetime.now()
        messages_to_save = []

        friend_account = str(agent_id) if agent_id is not None else ''

        if is_new_conversation:
            messages_to_save.append(
                AIChatMessages(
                    conversation_id=conversation_id,
                    agent_id=agent_id,
                    flag=0,
                    title=user_message[:50] if len(user_message) > 50 else user_message,
                    content=user_message,
                    attachment_list=None,
                    owner_name="User",
                    owner_account="user",
                    friend_name=agent_name,
                    friend_account=friend_account,
                    is_first=True,
                    create_time=now,
                )
            )
        else:
            messages_to_save.append(
                AIChatMessages(
                    conversation_id=conversation_id,
                    agent_id=agent_id,
                    flag=0,
                    content=user_message,
                    attachment_list=None,
                    owner_name="User",
                    owner_account="user",
                    friend_name=agent_name,
                    friend_account=friend_account,
                    is_first=False,
                    create_time=now,
                )
            )

        messages_to_save.append(
            AIChatMessages(
                conversation_id=conversation_id,
                agent_id=agent_id,
                flag=1,
                content=assistant_reply,
                attachment_list=None,
                owner_name="User",
                owner_account="user",
                friend_name=agent_name,
                friend_account=friend_account,
                is_first=False,
                create_time=now,
            )
        )

        from db.write_queue import db_write
        _msgs = messages_to_save
        def _do(sess):
            sess.add_all(_msgs)
        db_write(_do, description="chat_router_save_messages")
    except Exception as e:
        logger.error(f"Failed to save chat messages: {e}", exc_info=True)
    finally:
        try:
            session.close()
        except Exception:
            pass


def _extract_delta_text_from_a2a_event(event_obj: dict) -> str:
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


def _extract_finish_reason_from_a2a_event(event_obj: dict) -> Optional[str]:
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


async def _remote_agent_collect_stream_text(*, rpc_url: str, text: str, context_id: str) -> str:
    rpc_url = _normalize_a2a_rpc_url(rpc_url)
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
    try:
        log_llm_request(
            request_id=req_id,
            source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
            request_json={"rpc_url": rpc_url, "payload": payload},
        )
    except Exception:
        pass

    timeout = httpx.Timeout(60.0, read=300.0)
    out_parts: List[str] = []
    seen_content = False
    last_content_ts = time.monotonic()
    idle_timeout_after_content_seconds = 120.0

    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        try:
            async with client.stream(
                'POST',
                rpc_url,
                json=payload,
                headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
            ) as resp:
                if resp.status_code >= 400:
                    try:
                        body = await resp.aread()
                        log_llm_error(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
                            error=f"HTTP {resp.status_code}: {body.decode(errors='ignore')}"
                        )
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
                    extracted = _extract_text_from_a2a_message(message_obj or {})
                    try:
                        log_llm_response(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
                            response_json={"content": extracted}
                        )
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
                            log_llm_error(
                                request_id=req_id,
                                source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
                                error=evt.get('error')
                            )
                        except Exception:
                            pass
                        return ''

                    delta = _extract_delta_text_from_a2a_event(evt)
                    if delta:
                        out_parts.append(delta)
                        try:
                            log_llm_stream_chunk(
                                request_id=req_id,
                                source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
                                stream_raw={"content": delta}
                            )
                        except Exception:
                            pass
                        seen_content = True
                        last_content_ts = time.monotonic()
                    else:
                        result = evt.get('result') if isinstance(evt, dict) else None
                        msg = (result or {}).get('message') if isinstance(result, dict) else None
                        parts = (msg or {}).get('parts') if isinstance(msg, dict) else None
                        if isinstance(parts, list):
                            for p in parts:
                                if isinstance(p, dict):
                                    t = p.get('text')
                                    if isinstance(t, str) and t:
                                        out_parts.append(t)
                                        try:
                                            log_llm_stream_chunk(
                                                request_id=req_id,
                                                source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
                                                stream_raw={"content": t}
                                            )
                                        except Exception:
                                            pass
                                        seen_content = True
                                        last_content_ts = time.monotonic()
                                        break

                        full_text = _extract_text_from_a2a_message(msg or {})
                        if isinstance(full_text, str) and full_text:
                            out_parts.append(full_text)
                            try:
                                log_llm_stream_chunk(
                                    request_id=req_id,
                                    source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
                                    stream_raw={"content": full_text}
                                )
                            except Exception:
                                pass
                            seen_content = True
                            last_content_ts = time.monotonic()

                    finish_reason = _extract_finish_reason_from_a2a_event(evt)
                    if finish_reason:
                        break
        except Exception as e:
            try:
                log_llm_error(
                    request_id=req_id,
                    source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
                    error=str(e)
                )
            except Exception:
                pass
            return ''

    full_text = ''.join(out_parts)
    try:
        log_llm_response(
            request_id=req_id,
            source="runtime.modules.agent.chat_router._remote_agent_collect_stream_text",
            response_json={"content": full_text}
        )
    except Exception:
        pass
    return full_text


async def _remote_agent_send_message(*, rpc_url: str, text: str, context_id: str, stream: bool) -> str:
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'SendMessage',
        'params': {
            'stream': bool(stream),
            'message': {
                'contextId': context_id,
                'parts': [{'text': text}]
            }
        }
    }
    rpc_url = _normalize_a2a_rpc_url(rpc_url)
    if not rpc_url:
        raise ValueError('A2A Endpoint URL is empty')

    timeout = httpx.Timeout(60.0, read=300.0)
    req_id = new_request_id()
    try:
        log_llm_request(
            request_id=req_id,
            source="runtime.modules.agent.chat_router._remote_agent_send_message",
            request_json={"rpc_url": rpc_url, "payload": payload},
        )
    except Exception:
        pass
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            resp = await client.post(rpc_url, json=payload, headers={'Content-Type': 'application/json'})
            if resp.status_code >= 400:
                try:
                    log_llm_error(
                        request_id=req_id,
                        source="runtime.modules.agent.chat_router._remote_agent_send_message",
                        error=f"HTTP {resp.status_code}: {resp.text[:500]}"
                    )
                except Exception:
                    pass
                raise HTTPException(status_code=502, detail=f'Remote agent error: HTTP {resp.status_code}: {resp.text[:500]}')

            content_type = str(resp.headers.get('content-type') or '').lower()
            if 'text/event-stream' in content_type:
                sse_text = resp.text or ''
                out_parts: List[str] = []
                for line in sse_text.splitlines():
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
                    delta = _extract_delta_text_from_a2a_event(evt)
                    if delta:
                        out_parts.append(delta)
                        try:
                            log_llm_stream_chunk(
                                request_id=req_id,
                                source="runtime.modules.agent.chat_router._remote_agent_send_message",
                                stream_raw={"content": delta}
                            )
                        except Exception:
                            pass
                        continue
                    result = evt.get('result') if isinstance(evt, dict) else None
                    msg = (result or {}).get('message') if isinstance(result, dict) else None
                    full_text = _extract_text_from_a2a_message(msg or {})
                    if isinstance(full_text, str) and full_text:
                        out_parts.append(full_text)
                    finish_reason = _extract_finish_reason_from_a2a_event(evt)
                    if finish_reason:
                        break

                joined = ''.join(out_parts)
                if joined:
                    try:
                        log_llm_response(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_send_message",
                            response_json={"content": joined}
                        )
                    except Exception:
                        pass
                    return joined
            try:
                data = resp.json()
            except Exception:
                try:
                    log_llm_error(
                        request_id=req_id,
                        source="runtime.modules.agent.chat_router._remote_agent_send_message",
                        error=f"Remote agent returned non-JSON response: {resp.text[:500]}"
                    )
                except Exception:
                    pass
                raise HTTPException(status_code=502, detail=f'Remote agent returned non-JSON response: {resp.text[:500]}')
    except httpx.TimeoutException:
        try:
            log_llm_error(
                request_id=req_id,
                source="runtime.modules.agent.chat_router._remote_agent_send_message",
                error='Remote agent timeout'
            )
        except Exception:
            pass
        raise HTTPException(status_code=504, detail='Remote agent timeout')
    except httpx.HTTPError as e:
        try:
            log_llm_error(
                request_id=req_id,
                source="runtime.modules.agent.chat_router._remote_agent_send_message",
                error=f'Remote agent network error: {str(e)}'
            )
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f'Remote agent network error: {str(e)}')

    if isinstance(data, dict) and data.get('error'):
        if not stream:
            fallback = await _remote_agent_collect_stream_text(
                rpc_url=rpc_url,
                text=text,
                context_id=context_id,
            )
            if fallback:
                try:
                    log_llm_response(
                        request_id=req_id,
                        source="runtime.modules.agent.chat_router._remote_agent_send_message",
                        response_json={"content": fallback}
                    )
                except Exception:
                    pass
                return fallback
        try:
            log_llm_error(
                request_id=req_id,
                source="runtime.modules.agent.chat_router._remote_agent_send_message",
                error=f"RPC error: {json.dumps(data.get('error'), ensure_ascii=False)}"
            )
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Remote agent RPC error: {json.dumps(data.get('error'), ensure_ascii=False)}")

    result = (data or {}).get('result') if isinstance(data, dict) else None
    message_obj = (result or {}).get('message') if isinstance(result, dict) else None
    reply = _extract_text_from_a2a_message(message_obj or {})
    try:
        log_llm_response(
            request_id=req_id,
            source="runtime.modules.agent.chat_router._remote_agent_send_message",
            response_json={"content": reply}
        )
    except Exception:
        pass
    return reply


async def _remote_agent_stream(*, rpc_url: str, text: str, context_id: str):
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
    rpc_url = _normalize_a2a_rpc_url(rpc_url)
    if not rpc_url:
        yield f"data: {json.dumps({'error': 'A2A Endpoint URL is empty'})}\n\n"
        return

    timeout = httpx.Timeout(60.0, read=300.0)
    req_id = new_request_id()
    try:
        log_llm_request(
            request_id=req_id,
            source="runtime.modules.agent.chat_router._remote_agent_stream",
            request_json={"rpc_url": rpc_url, "payload": payload},
        )
    except Exception:
        pass
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        try:
            async with client.stream(
                'POST',
                rpc_url,
                json=payload,
                headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
            ) as resp:
                content_type = str(resp.headers.get('content-type') or '').lower()
                if resp.status_code >= 400:
                    body = await resp.aread()
                    text_body = ''
                    try:
                        text_body = body.decode('utf-8', errors='ignore')
                    except Exception:
                        text_body = str(body)
                    try:
                        log_llm_error(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_stream",
                            error=f"HTTP {resp.status_code}: {text_body[:500]}"
                        )
                    except Exception:
                        pass
                    yield f"data: {json.dumps({'error': f'Remote agent error: HTTP {resp.status_code}: {text_body[:500]}'})}\n\n"
                    return

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

                    if isinstance(data, dict) and data.get('error'):
                        try:
                            reply = await _remote_agent_send_message(
                                rpc_url=rpc_url,
                                text=text,
                                context_id=context_id,
                                stream=False,
                            )
                            if reply:
                                try:
                                    log_llm_response(
                                        request_id=req_id,
                                        source="runtime.modules.agent.chat_router._remote_agent_stream",
                                        response_json={"content": reply}
                                    )
                                except Exception:
                                    pass
                                yield f"data: {json.dumps({'content': reply})}\n\n"
                                return
                        except Exception:
                            pass
                        try:
                            log_llm_error(
                                request_id=req_id,
                                source="runtime.modules.agent.chat_router._remote_agent_stream",
                                error=json.dumps(data.get('error'), ensure_ascii=False)
                            )
                        except Exception:
                            pass
                        yield f"data: {json.dumps({'error': json.dumps(data.get('error'), ensure_ascii=False)})}\n\n"
                        return

                    result = data.get('result') if isinstance(data, dict) else None
                    message_obj = (result or {}).get('message') if isinstance(result, dict) else None
                    reply = _extract_text_from_a2a_message(message_obj or {})
                    if reply:
                        try:
                            log_llm_response(
                                request_id=req_id,
                                source="runtime.modules.agent.chat_router._remote_agent_stream",
                                response_json={"content": reply}
                            )
                        except Exception:
                            pass
                        yield f"data: {json.dumps({'content': reply})}\n\n"
                        return

                    try:
                        reply = await _remote_agent_send_message(
                            rpc_url=rpc_url,
                            text=text,
                            context_id=context_id,
                            stream=False,
                        )
                        if reply:
                            try:
                                log_llm_response(
                                    request_id=req_id,
                                    source="runtime.modules.agent.chat_router._remote_agent_stream",
                                    response_json={"content": reply}
                                )
                            except Exception:
                                pass
                            yield f"data: {json.dumps({'content': reply})}\n\n"
                            return
                    except Exception:
                        pass
                    try:
                        log_llm_error(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_stream",
                            error=f"Remote agent returned non-SSE response: {text_body[:500]}"
                        )
                    except Exception:
                        pass
                    yield f"data: {json.dumps({'error': f'Remote agent returned non-SSE response: {text_body[:500]}'})}\n\n"
                    return

                # Some implementations keep the SSE connection open even after completion.
                # Break if no new *content* has arrived for a while (even if keep-alive blank lines arrive).
                idle_timeout_after_content_seconds = 120.0
                last_content_ts = time.monotonic()
                seen_content = False

                try:
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
                            if not seen_content:
                                try:
                                    reply = await _remote_agent_send_message(
                                        rpc_url=rpc_url,
                                        text=text,
                                        context_id=context_id,
                                        stream=False,
                                    )
                                    if reply:
                                        seen_content = True
                                        last_content_ts = time.monotonic()
                                        try:
                                            log_llm_response(
                                                request_id=req_id,
                                                source="runtime.modules.agent.chat_router._remote_agent_stream",
                                                response_json={"content": reply}
                                            )
                                        except Exception:
                                            pass
                                        yield f"data: {json.dumps({'content': reply})}\n\n"
                                        break
                                except Exception:
                                    pass
                            try:
                                log_llm_error(
                                    request_id=req_id,
                                    source="runtime.modules.agent.chat_router._remote_agent_stream",
                                    error=json.dumps(evt.get('error'), ensure_ascii=False)
                                )
                            except Exception:
                                pass
                            yield f"data: {json.dumps({'error': json.dumps(evt.get('error'), ensure_ascii=False)})}\n\n"
                            continue

                        delta = _extract_delta_text_from_a2a_event(evt)
                        if delta:
                            seen_content = True
                            last_content_ts = time.monotonic()
                            try:
                                log_llm_stream_chunk(
                                    request_id=req_id,
                                    source="runtime.modules.agent.chat_router._remote_agent_stream",
                                    stream_raw={"content": delta}
                                )
                            except Exception:
                                pass
                            yield f"data: {json.dumps({'content': delta})}\n\n"
                        else:
                            # Some A2A implementations stream text directly via part.text
                            result = evt.get('result') if isinstance(evt, dict) else None
                            msg = (result or {}).get('message') if isinstance(result, dict) else None
                            parts = (msg or {}).get('parts') if isinstance(msg, dict) else None
                            if isinstance(parts, list):
                                for p in parts:
                                    if isinstance(p, dict):
                                        t = p.get('text')
                                        if isinstance(t, str) and t:
                                            seen_content = True
                                            last_content_ts = time.monotonic()
                                            try:
                                                log_llm_stream_chunk(
                                                    request_id=req_id,
                                                    source="runtime.modules.agent.chat_router._remote_agent_stream",
                                                    stream_raw={"content": t}
                                                )
                                            except Exception:
                                                pass
                                            yield f"data: {json.dumps({'content': t})}\n\n"
                                            break

                        if not delta:
                            result = evt.get('result') if isinstance(evt, dict) else None
                            msg = (result or {}).get('message') if isinstance(result, dict) else None
                            full_text = _extract_text_from_a2a_message(msg or {})
                            if isinstance(full_text, str) and full_text:
                                seen_content = True
                                last_content_ts = time.monotonic()
                                try:
                                    log_llm_stream_chunk(
                                        request_id=req_id,
                                        source="runtime.modules.agent.chat_router._remote_agent_stream",
                                        stream_raw={"content": full_text}
                                    )
                                except Exception:
                                    pass
                                yield f"data: {json.dumps({'content': full_text})}\n\n"

                        finish_reason = _extract_finish_reason_from_a2a_event(evt)
                        if finish_reason:
                            break
                    # Normal SSE loop completion (finish_reason / [DONE] / idle timeout)
                    try:
                        log_llm_response(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_stream",
                            response_json={"status": "completed"}
                        )
                    except Exception:
                        pass
                except httpx.ReadTimeout:
                    # Upstream keeps connection open forever; end the stream gracefully.
                    try:
                        log_llm_response(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_stream",
                            response_json={"status": "completed"}
                        )
                    except Exception:
                        pass
                    return
                except Exception as e:
                    try:
                        log_llm_error(
                            request_id=req_id,
                            source="runtime.modules.agent.chat_router._remote_agent_stream",
                            error=str(e)
                        )
                    except Exception:
                        pass
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    return
        except httpx.TimeoutException:
            try:
                log_llm_error(
                    request_id=req_id,
                    source="runtime.modules.agent.chat_router._remote_agent_stream",
                    error='Remote agent timeout'
                )
            except Exception:
                pass
            yield f"data: {json.dumps({'error': 'Remote agent timeout'})}\n\n"
            return
        except httpx.HTTPError as e:
            try:
                log_llm_error(
                    request_id=req_id,
                    source="runtime.modules.agent.chat_router._remote_agent_stream",
                    error=f'Remote agent network error: {str(e)}'
                )
            except Exception:
                pass
            yield f"data: {json.dumps({'error': f'Remote agent network error: {str(e)}'})}\n\n"
            return



# ==================== Request/Response Models ====================

class AgentChatRequest(BaseModel):
    """Agent chat request."""
    message: str
    conversation_id: Optional[str] = None
    use_tools: bool = True
    use_memory: bool = True
    use_knowledge_base: bool = True
    show_token_usage: bool = False


class AgentChatResponse(BaseModel):
    """Agent chat response."""
    success: bool
    reply: Optional[str] = None
    conversation_id: Optional[str] = None
    error: Optional[str] = None


# ==================== Agent Chat Endpoints ====================

@router.post("/{agent_id}/chat", response_model=dict)
async def agent_chat_by_id(
    agent_id: int,
    request: AgentChatRequest
):
    """
    Agent non-streaming chat (by ID).

    Args:
        agent_id: Agent ID
        request: Chat request

    Returns:
        Chat response
    """
    try:
        try:
            from runtime.modules.agent.service import AgentService
            cfg = AgentService.get_agent(agent_id)
        except Exception:
            cfg = None

        agent_type = str((cfg or {}).get('agent_type') or 'local')
        if _is_remote_agent_type(agent_type):
            rpc_url = str((cfg or {}).get('url') or '').strip()
            context_id = request.conversation_id or 'default'
            reply = await _remote_agent_send_message(
                rpc_url=rpc_url,
                text=request.message,
                context_id=context_id,
                stream=False
            )

            try:
                _save_chat_messages_to_db(
                    conversation_id=context_id,
                    agent_id=agent_id,
                    agent_name=(cfg or {}).get('name') or str(agent_id),
                    user_message=request.message,
                    assistant_reply=reply,
                )
            except Exception:
                pass

            return {
                'success': True,
                'data': {
                    'reply': reply,
                    'conversation_id': context_id,
                    'agent_id': agent_id,
                    'agent_name': (cfg or {}).get('name') or str(agent_id)
                }
            }

        # Get agent instance
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Call agent chat
        reply = await agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            use_tools=request.use_tools,
            use_memory=request.use_memory,
            use_knowledge_base=request.use_knowledge_base,
            show_token_usage=request.show_token_usage,
        )

        # Persist messages for local (non-streaming) chat
        conv_id = request.conversation_id or "default"
        try:
            _save_chat_messages_to_db(
                conversation_id=conv_id,
                agent_id=agent_id,
                agent_name=agent.name,
                user_message=request.message,
                assistant_reply=reply,
            )
        except Exception:
            logger.warning("Failed to persist non-streaming chat messages", exc_info=True)

        usage = agent.get_last_usage(request.conversation_id) if request.show_token_usage else None

        return {
            "success": True,
            "data": {
                "reply": reply,
                "conversation_id": conv_id,
                "agent_id": agent_id,
                "agent_name": agent.name,
                "usage": usage,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/chat/stream-with-files")
async def agent_chat_stream_with_files(
    agent_id: int,
    message: str = Form(...),
    conversation_id: Optional[str] = Form(None),
    use_tools: bool = Form(True),
    use_memory: bool = Form(True),
    use_knowledge_base: bool = Form(True),
    show_token_usage: bool = Form(False),
    files: List[UploadFile] = File(default=[])
):
    try:
        try:
            from runtime.modules.agent.service import AgentService
            cfg = AgentService.get_agent(agent_id)
        except Exception:
            cfg = None

        agent_type = str((cfg or {}).get('agent_type') or 'local')

        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        attachments_text_parts = []
        image_data_urls: List[str] = []
        attachments_meta_full: List[dict] = []
        attachments_public: List[dict] = []

        from pathlib import Path
        from runtime.modules.km.document_loader import DocumentLoader

        upload_dir = Path(f"uploads/agent_attachments/{agent_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        for f in files or []:
            filename = f.filename or 'unknown'
            content = await f.read()

            safe_name = Path(filename).name
            attachment_id = uuid.uuid4().hex
            unique_name = f"{uuid.uuid4().hex}_{safe_name}"
            file_path = upload_dir / unique_name

            try:
                file_path.write_bytes(content)
            except Exception:
                continue

            content_type = f.content_type or ''
            if content_type.startswith('image/'):
                b64 = base64.b64encode(content).decode('utf-8')
                image_data_urls.append(f"data:{content_type};base64,{b64}")
                meta = {
                    'id': attachment_id,
                    'name': safe_name,
                    'size': len(content),
                    'type': content_type,
                    'saved_path': str(file_path.resolve())
                }
                attachments_meta_full.append(meta)
                attachments_public.append({
                    'id': attachment_id,
                    'name': safe_name,
                    'size': len(content),
                    'type': content_type
                })
                continue

            suffix = Path(filename).suffix.lower()
            if suffix in {'.txt', '.md', '.markdown'}:
                try:
                    text = content.decode('utf-8')
                except Exception:
                    try:
                        text = content.decode('gbk')
                    except Exception:
                        text = ''
                if text:
                    attachments_text_parts.append(f"[File: {filename}]\n{text}")
                meta = {
                    'id': attachment_id,
                    'name': safe_name,
                    'size': len(content),
                    'type': content_type or 'text/plain',
                    'saved_path': str(file_path.resolve())
                }
                attachments_meta_full.append(meta)
                attachments_public.append({
                    'id': attachment_id,
                    'name': safe_name,
                    'size': len(content),
                    'type': content_type or 'text/plain'
                })
                continue

            extracted = DocumentLoader.load_document(file_path)
            if extracted:
                attachments_text_parts.append(f"[File: {filename}]\n{extracted}")
            meta = {
                'id': attachment_id,
                'name': safe_name,
                'size': len(content),
                'type': content_type,
                'saved_path': str(file_path.resolve())
            }
            attachments_meta_full.append(meta)
            attachments_public.append({
                'id': attachment_id,
                'name': safe_name,
                'size': len(content),
                'type': content_type
            })

        attachments_text = "\n\n".join(attachments_text_parts)

        if _is_remote_agent_type(agent_type):
            rpc_url = str((cfg or {}).get('url') or '').strip()
            context_id = conversation_id or 'default'
            send_text = message
            if attachments_text:
                send_text = send_text + "\n\n" + attachments_text

            async def generate_remote():
                async for sse in _remote_agent_stream(
                    rpc_url=rpc_url,
                    text=send_text,
                    context_id=context_id,
                ):
                    yield sse
                yield f"data: {json.dumps({'done': True, 'attachments': attachments_public})}\n\n"

            return StreamingResponse(
                generate_remote(),
                media_type='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )

        async def generate():
            try:
                async for chunk in agent.chat_stream(
                    message=message,
                    conversation_id=conversation_id,
                    use_tools=use_tools,
                    use_memory=use_memory,
                    use_knowledge_base=use_knowledge_base,
                    attachments_text=attachments_text,
                    image_data_urls=image_data_urls,
                    attachments_meta=attachments_meta_full,
                    show_token_usage=show_token_usage,
                ):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                if show_token_usage:
                    usage = agent.get_last_usage(conversation_id)
                    if usage:
                        yield f"data: {json.dumps({'usage': usage})}\n\n"
                yield f"data: {json.dumps({'done': True, 'attachments': attachments_public})}\n\n"
            except Exception as e:
                logger.error(f"Streaming generation failed: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent streaming chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/chat/stream")
async def agent_chat_stream_by_id(
    agent_id: int,
    request: AgentChatRequest
):
    """
    Agent streaming chat (by ID) - uses SSE.

    Args:
        agent_id: Agent ID
        request: Chat request

    Returns:
        SSE streaming response
    """
    try:
        try:
            from runtime.modules.agent.service import AgentService
            cfg = AgentService.get_agent(agent_id)
        except Exception:
            cfg = None

        agent_type = str((cfg or {}).get('agent_type') or 'local')
        if _is_remote_agent_type(agent_type):
            rpc_url = str((cfg or {}).get('url') or '').strip()
            context_id = request.conversation_id or 'default'

            async def generate_remote():
                parts: List[str] = []
                async for sse in _remote_agent_stream(
                    rpc_url=rpc_url,
                    text=request.message,
                    context_id=context_id,
                ):
                    try:
                        line = str(sse or '')
                        if line.startswith('data:'):
                            payload = line[len('data:'):].strip()
                            obj = json.loads(payload)
                            c = obj.get('content') if isinstance(obj, dict) else None
                            if isinstance(c, str) and c:
                                parts.append(c)
                    except Exception:
                        pass
                    yield sse

                try:
                    _save_chat_messages_to_db(
                        conversation_id=context_id,
                        agent_id=agent_id,
                        agent_name=(cfg or {}).get('name') or str(agent_id),
                        user_message=request.message,
                        assistant_reply=''.join(parts),
                    )
                except Exception:
                    pass

                yield f"data: {json.dumps({'done': True})}\n\n"

            return StreamingResponse(
                generate_remote(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        # Get agent instance
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        async def generate():
            """SSE generator."""
            try:
                async for chunk in agent.chat_stream(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    use_tools=request.use_tools,
                    use_memory=request.use_memory,
                    use_knowledge_base=request.use_knowledge_base,
                    show_token_usage=request.show_token_usage,
                ):
                    # SSE format
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                if request.show_token_usage:
                    usage = agent.get_last_usage(request.conversation_id)
                    if usage:
                        yield f"data: {json.dumps({'usage': usage})}\n\n"

                # Send completion signal
                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                logger.error(f"Streaming generation failed: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent streaming chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/name/{agent_name}/chat", response_model=dict)
async def agent_chat_by_name(
    agent_name: str,
    request: AgentChatRequest
):
    """
    Agent non-streaming chat (by name).

    Args:
        agent_name: Agent name
        request: Chat request

    Returns:
        Chat response
    """
    try:
        cfg = _load_agent_cfg_by_name(agent_name)
        agent_type = str((cfg or {}).get('agent_type') or 'local')
        if _is_remote_agent_type(agent_type):
            rpc_url = str((cfg or {}).get('url') or '').strip()
            context_id = request.conversation_id or 'default'
            reply = await _remote_agent_send_message(
                rpc_url=rpc_url,
                text=request.message,
                context_id=context_id,
                stream=False
            )

            try:
                _save_chat_messages_to_db(
                    conversation_id=context_id,
                    agent_id=(cfg or {}).get('id'),
                    agent_name=(cfg or {}).get('name') or agent_name,
                    user_message=request.message,
                    assistant_reply=reply,
                )
            except Exception:
                pass

            return {
                'success': True,
                'data': {
                    'reply': reply,
                    'conversation_id': context_id,
                    'agent_id': (cfg or {}).get('id'),
                    'agent_name': (cfg or {}).get('name') or agent_name
                }
            }

        # Get agent instance
        agent = agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Call agent chat
        reply = await agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            use_tools=request.use_tools,
            use_memory=request.use_memory,
            use_knowledge_base=request.use_knowledge_base,
            show_token_usage=request.show_token_usage,
        )

        # Persist messages for local (non-streaming) chat
        conv_id = request.conversation_id or "default"
        try:
            _save_chat_messages_to_db(
                conversation_id=conv_id,
                agent_id=agent.agent_id,
                agent_name=agent.name,
                user_message=request.message,
                assistant_reply=reply,
            )
        except Exception:
            logger.warning("Failed to persist non-streaming chat messages", exc_info=True)

        usage = agent.get_last_usage(request.conversation_id) if request.show_token_usage else None

        return {
            "success": True,
            "data": {
                "reply": reply,
                "conversation_id": conv_id,
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "usage": usage,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/name/{agent_name}/chat/stream")
async def agent_chat_stream_by_name(
    agent_name: str,
    request: AgentChatRequest
):
    """
    Agent streaming chat (by name) - uses SSE.

    Args:
        agent_name: Agent name
        request: Chat request

    Returns:
        SSE streaming response
    """
    try:
        cfg = _load_agent_cfg_by_name(agent_name)
        agent_type = str((cfg or {}).get('agent_type') or 'local')
        if _is_remote_agent_type(agent_type):
            rpc_url = str((cfg or {}).get('url') or '').strip()
            context_id = request.conversation_id or 'default'

            async def generate_remote():
                parts: List[str] = []
                async for sse in _remote_agent_stream(
                    rpc_url=rpc_url,
                    text=request.message,
                    context_id=context_id,
                ):
                    try:
                        line = str(sse or '')
                        if line.startswith('data:'):
                            payload = line[len('data:'):].strip()
                            obj = json.loads(payload)
                            c = obj.get('content') if isinstance(obj, dict) else None
                            if isinstance(c, str) and c:
                                parts.append(c)
                    except Exception:
                        pass
                    yield sse

                try:
                    _save_chat_messages_to_db(
                        conversation_id=context_id,
                        agent_id=(cfg or {}).get('id'),
                        agent_name=(cfg or {}).get('name') or agent_name,
                        user_message=request.message,
                        assistant_reply=''.join(parts),
                    )
                except Exception:
                    pass
                yield f"data: {json.dumps({'done': True})}\n\n"

            return StreamingResponse(
                generate_remote(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        # Get agent instance
        agent = agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        async def generate():
            """SSE generator."""
            try:
                async for chunk in agent.chat_stream(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    use_tools=request.use_tools,
                    use_memory=request.use_memory,
                    use_knowledge_base=request.use_knowledge_base,
                    show_token_usage=request.show_token_usage,
                ):
                    # SSE format
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                if request.show_token_usage:
                    usage = agent.get_last_usage(request.conversation_id)
                    if usage:
                        yield f"data: {json.dumps({'usage': usage})}\n\n"

                # Send completion signal
                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                logger.error(f"Streaming generation failed: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent streaming chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Memory Management ====================

@router.delete("/{agent_id}/memory")
async def clear_agent_memory(
    agent_id: int,
    conversation_id: Optional[str] = None
):
    """
    Clear agent conversation memory.

    Args:
        agent_id: Agent ID
        conversation_id: Conversation ID; if None, clears all

    Returns:
        Success status
    """
    raise HTTPException(status_code=410, detail="Deprecated: agent conversation memory endpoints are disabled")


@router.get("/{agent_id}/memory")
async def get_agent_memory(
    agent_id: int,
    conversation_id: Optional[str] = None
):
    """
    Get agent conversation memory.

    Args:
        agent_id: Agent ID
        conversation_id: Conversation ID

    Returns:
        Conversation history
    """
    raise HTTPException(status_code=410, detail="Deprecated: agent conversation memory endpoints are disabled")


# ==================== Agent Instance Management ====================

@router.get("/{agent_id}/info")
async def get_agent_info(agent_id: int):
    """
    Get agent instance info.

    Args:
        agent_id: Agent ID

    Returns:
        Agent info
    """
    try:
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {
            "success": True,
            "data": agent.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/reload")
async def reload_agent(agent_id: int):
    """
    Reload agent (refresh config).

    Args:
        agent_id: Agent ID

    Returns:
        Success status
    """
    try:
        agent = agent_manager.reload_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Clear SNS engine's cached agent if it uses this agent
        try:
            from runtime.apps.sns.service_async import _social_engine_instance
            if _social_engine_instance is not None:
                eng_agent_id = getattr(
                    getattr(_social_engine_instance, "aisns_cfg", None),
                    "agent_id", None,
                )
                if eng_agent_id is not None and int(eng_agent_id) == agent_id:
                    _social_engine_instance.agent = None
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Agent {agent_id} reloaded",
            "data": agent.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reload agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cached")
async def get_cached_agents():
    """
    Get all cached agents.

    Returns:
        Cached agent list
    """
    try:
        agents = agent_manager.get_all_cached_agents()

        return {
            "success": True,
            "data": [agent.to_dict() for agent in agents]
        }

    except Exception as e:
        logger.error(f"Failed to get cached agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
