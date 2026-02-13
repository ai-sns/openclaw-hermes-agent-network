# -*- coding: utf-8 -*-
"""
Agent Chat Router - Agent问答API接口
支持流式和非流式问答，按ID或名称调用Agent
"""
import logging
import json
import base64
import uuid
import time
from typing import Optional
from typing import List
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agent_manager import agent_manager
from backend.database.base import get_session
from backend.database.models.agent import AgentCfg

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

    timeout = httpx.Timeout(60.0, read=60.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            resp = await client.post(rpc_url, json=payload, headers={'Content-Type': 'application/json'})
            if resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f'Remote agent error: HTTP {resp.status_code}: {resp.text[:500]}')
            try:
                data = resp.json()
            except Exception:
                raise HTTPException(status_code=502, detail=f'Remote agent returned non-JSON response: {resp.text[:500]}')
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail='Remote agent timeout')
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f'Remote agent network error: {str(e)}')

    if isinstance(data, dict) and data.get('error'):
        raise HTTPException(status_code=502, detail=f"Remote agent RPC error: {json.dumps(data.get('error'), ensure_ascii=False)}")

    result = (data or {}).get('result') if isinstance(data, dict) else None
    message_obj = (result or {}).get('message') if isinstance(result, dict) else None
    reply = _extract_text_from_a2a_message(message_obj or {})
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

    timeout = httpx.Timeout(60.0, read=30.0)
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        try:
            async with client.stream(
                'POST',
                rpc_url,
                json=payload,
                headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    text_body = ''
                    try:
                        text_body = body.decode('utf-8', errors='ignore')
                    except Exception:
                        text_body = str(body)
                    yield f"data: {json.dumps({'error': f'Remote agent error: HTTP {resp.status_code}: {text_body[:500]}'})}\n\n"
                    return

                # Some implementations keep the SSE connection open even after completion.
                # Break if no new *content* has arrived for a while (even if keep-alive blank lines arrive).
                idle_timeout_after_content_seconds = 5.0
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
                        if s.startswith('data:'):
                            s = s[5:].strip()
                        if s == '[DONE]':
                            break

                        try:
                            evt = json.loads(s)
                        except Exception:
                            continue

                        if isinstance(evt, dict) and evt.get('error'):
                            yield f"data: {json.dumps({'error': json.dumps(evt.get('error'), ensure_ascii=False)})}\n\n"
                            continue

                        delta = _extract_delta_text_from_a2a_event(evt)
                        if delta:
                            seen_content = True
                            last_content_ts = time.monotonic()
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
                                            yield f"data: {json.dumps({'content': t})}\n\n"
                                            break

                        finish_reason = _extract_finish_reason_from_a2a_event(evt)
                        if finish_reason:
                            break
                except httpx.ReadTimeout:
                    # Upstream keeps connection open forever; end the stream gracefully.
                    return
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    return
        except httpx.TimeoutException:
            yield f"data: {json.dumps({'error': 'Remote agent timeout'})}\n\n"
            return
        except httpx.HTTPError as e:
            yield f"data: {json.dumps({'error': f'Remote agent network error: {str(e)}'})}\n\n"
            return



# ==================== Request/Response Models ====================

class AgentChatRequest(BaseModel):
    """Agent问答请求"""
    message: str
    conversation_id: Optional[str] = None
    use_tools: bool = True
    use_memory: bool = True
    use_knowledge_base: bool = True


class AgentChatResponse(BaseModel):
    """Agent问答响应"""
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
    Agent非流式问答（按ID）

    Args:
        agent_id: Agent ID
        request: 问答请求

    Returns:
        问答响应
    """
    try:
        try:
            from backend.modules.agent.service import AgentService
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
            return {
                'success': True,
                'data': {
                    'reply': reply,
                    'conversation_id': context_id,
                    'agent_id': agent_id,
                    'agent_name': (cfg or {}).get('name') or str(agent_id)
                }
            }

        # 获取Agent实例
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # 调用agent问答
        reply = await agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            use_tools=request.use_tools,
            use_memory=request.use_memory,
            use_knowledge_base=request.use_knowledge_base
        )

        return {
            "success": True,
            "data": {
                "reply": reply,
                "conversation_id": request.conversation_id or "default",
                "agent_id": agent_id,
                "agent_name": agent.name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/chat/stream-with-files")
async def agent_chat_stream_with_files(
    agent_id: int,
    message: str = Form(...),
    conversation_id: Optional[str] = Form(None),
    use_tools: bool = Form(True),
    use_memory: bool = Form(True),
    use_knowledge_base: bool = Form(True),
    files: List[UploadFile] = File(default=[])
):
    try:
        try:
            from backend.modules.agent.service import AgentService
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
        from backend.modules.km.document_loader import DocumentLoader

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
                    attachments_text_parts.append(f"[文件: {filename}]\n{text}")
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
                attachments_text_parts.append(f"[文件: {filename}]\n{extracted}")
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
                    attachments_meta=attachments_meta_full
                ):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True, 'attachments': attachments_public})}\n\n"
            except Exception as e:
                logger.error(f"流式生成失败: {e}", exc_info=True)
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
        logger.error(f"Agent流式问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/chat/stream")
async def agent_chat_stream_by_id(
    agent_id: int,
    request: AgentChatRequest
):
    """
    Agent流式问答（按ID）- 使用SSE

    Args:
        agent_id: Agent ID
        request: 问答请求

    Returns:
        SSE流式响应
    """
    try:
        try:
            from backend.modules.agent.service import AgentService
            cfg = AgentService.get_agent(agent_id)
        except Exception:
            cfg = None

        agent_type = str((cfg or {}).get('agent_type') or 'local')
        if _is_remote_agent_type(agent_type):
            rpc_url = str((cfg or {}).get('url') or '').strip()
            context_id = request.conversation_id or 'default'

            async def generate_remote():
                async for sse in _remote_agent_stream(
                    rpc_url=rpc_url,
                    text=request.message,
                    context_id=context_id,
                ):
                    yield sse
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

        # 获取Agent实例
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        async def generate():
            """SSE生成器"""
            try:
                async for chunk in agent.chat_stream(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    use_tools=request.use_tools,
                    use_memory=request.use_memory,
                    use_knowledge_base=request.use_knowledge_base
                ):
                    # SSE格式
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                # 发送完成信号
                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {e}", exc_info=True)
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
        logger.error(f"Agent流式问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/name/{agent_name}/chat", response_model=dict)
async def agent_chat_by_name(
    agent_name: str,
    request: AgentChatRequest
):
    """
    Agent非流式问答（按名称）

    Args:
        agent_name: Agent名称
        request: 问答请求

    Returns:
        问答响应
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
            return {
                'success': True,
                'data': {
                    'reply': reply,
                    'conversation_id': context_id,
                    'agent_id': (cfg or {}).get('id'),
                    'agent_name': (cfg or {}).get('name') or agent_name
                }
            }

        # 获取Agent实例
        agent = agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # 调用agent问答
        reply = await agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            use_tools=request.use_tools,
            use_memory=request.use_memory,
            use_knowledge_base=request.use_knowledge_base
        )

        return {
            "success": True,
            "data": {
                "reply": reply,
                "conversation_id": request.conversation_id or "default",
                "agent_id": agent.agent_id,
                "agent_name": agent.name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/name/{agent_name}/chat/stream")
async def agent_chat_stream_by_name(
    agent_name: str,
    request: AgentChatRequest
):
    """
    Agent流式问答（按名称）- 使用SSE

    Args:
        agent_name: Agent名称
        request: 问答请求

    Returns:
        SSE流式响应
    """
    try:
        cfg = _load_agent_cfg_by_name(agent_name)
        agent_type = str((cfg or {}).get('agent_type') or 'local')
        if _is_remote_agent_type(agent_type):
            rpc_url = str((cfg or {}).get('url') or '').strip()
            context_id = request.conversation_id or 'default'

            async def generate_remote():
                async for sse in _remote_agent_stream(
                    rpc_url=rpc_url,
                    text=request.message,
                    context_id=context_id,
                ):
                    yield sse
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

        # 获取Agent实例
        agent = agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        async def generate():
            """SSE生成器"""
            try:
                async for chunk in agent.chat_stream(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    use_tools=request.use_tools,
                    use_memory=request.use_memory,
                    use_knowledge_base=request.use_knowledge_base
                ):
                    # SSE格式
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                # 发送完成信号
                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {e}", exc_info=True)
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
        logger.error(f"Agent流式问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Memory Management ====================

@router.delete("/{agent_id}/memory")
async def clear_agent_memory(
    agent_id: int,
    conversation_id: Optional[str] = None
):
    """
    清除Agent的对话记忆

    Args:
        agent_id: Agent ID
        conversation_id: 对话ID，如果为None则清除所有

    Returns:
        成功状态
    """
    try:
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        agent.clear_memory(conversation_id)

        return {
            "success": True,
            "message": f"Memory cleared for agent {agent_id}" + (f" conversation {conversation_id}" if conversation_id else " (all conversations)")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/memory")
async def get_agent_memory(
    agent_id: int,
    conversation_id: Optional[str] = None
):
    """
    获取Agent的对话记忆

    Args:
        agent_id: Agent ID
        conversation_id: 对话ID

    Returns:
        对话历史
    """
    try:
        agent = agent_manager.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        memory = agent._get_conversation_memory(conversation_id)

        return {
            "success": True,
            "data": {
                "conversation_id": conversation_id or "default",
                "messages": memory
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Instance Management ====================

@router.get("/{agent_id}/info")
async def get_agent_info(agent_id: int):
    """
    获取Agent实例信息

    Args:
        agent_id: Agent ID

    Returns:
        Agent信息
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
        logger.error(f"获取Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/reload")
async def reload_agent(agent_id: int):
    """
    重新加载Agent（刷新配置）

    Args:
        agent_id: Agent ID

    Returns:
        成功状态
    """
    try:
        agent = agent_manager.reload_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {
            "success": True,
            "message": f"Agent {agent_id} reloaded",
            "data": agent.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新加载Agent失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cached")
async def get_cached_agents():
    """
    获取所有已缓存的Agent

    Returns:
        缓存的Agent列表
    """
    try:
        agents = agent_manager.get_all_cached_agents()

        return {
            "success": True,
            "data": [agent.to_dict() for agent in agents]
        }

    except Exception as e:
        logger.error(f"获取缓存Agent失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
