import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterable, Iterable, Optional

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
    from starlette.concurrency import run_in_threadpool
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing dependency 'fastapi'. Install it in the Python environment you're using:\n"
        "  python -m pip install fastapi uvicorn\n"
        "Note: this script uses uvicorn to serve the FastAPI app."
    ) from e

try:
    from langchain.chat_models import init_chat_model
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing dependency 'langchain'. Install it in the Python environment you're using:\n"
        "  python -m pip install langchain langchain-openai"
    ) from e

try:
    from deepagents import create_deep_agent
    from deepagents.backends.filesystem import FilesystemBackend

    _HAS_DEEPAGENTS = True
except ModuleNotFoundError:
    _HAS_DEEPAGENTS = False


# ---------------------------------------------------------------------------
# LangChain / DeepAgents execution helpers
# ---------------------------------------------------------------------------

def _invoke_langchain(
    *,
    base_url: str,
    api_key: str,
    model_name: str,
    message: str,
    backend_root_dir: Optional[str],
    virtual_mode: bool,
) -> str:
    """Run a single task through LangChain (+ optional DeepAgents backend)."""
    model = init_chat_model(
        model_name,
        base_url=base_url,
        api_key=api_key,
    )

    if _HAS_DEEPAGENTS and backend_root_dir:
        backend = FilesystemBackend(
            root_dir=backend_root_dir,
            virtual_mode=virtual_mode,
        )
        agent = create_deep_agent(model=model, backend=backend)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": message}]}
        )
        # result may be a dict, a LangChain message object, or a string
        if isinstance(result, dict):
            # Try to extract the last assistant message
            msgs = result.get("messages", [])
            if msgs:
                last = msgs[-1]
                # LangChain message objects have a .content attribute
                if hasattr(last, "content"):
                    return last.content
                if isinstance(last, dict):
                    return last.get("content", str(result))
                return str(last)
            return str(result)
        # LangChain message object returned directly
        if hasattr(result, "content"):
            return result.content
        return str(result)

    # Fallback: direct model invocation without DeepAgents
    from langchain_core.messages import HumanMessage

    resp = model.invoke([HumanMessage(content=message)])
    # resp is a LangChain AIMessage; extract only the text content
    if hasattr(resp, "content") and isinstance(resp.content, str):
        return resp.content
    return str(resp)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ServerConfig:
    bind_host: str
    port: int
    rpc_path: str
    public_url: Optional[str]


@dataclass(frozen=True)
class LangChainConfig:
    base_url: str
    api_key: Optional[str]
    api_key_env: list[str]
    model: str
    backend_root_dir: Optional[str]
    virtual_mode: bool
    timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    langchain: LangChainConfig


def _resolve_api_key(api_key: Optional[str], api_key_env: list[str]) -> str:
    if api_key:
        return api_key
    for env_key in api_key_env:
        v = os.environ.get(env_key)
        if v:
            return v
    raise SystemExit(
        "Missing API key. Set LANGCHAIN_API_KEY "
        "(or configure langchain.apiKey / langchain.apiKeyEnv)."
    )


def _get_config_path() -> str:
    path = os.environ.get("LANGCHAIN_ADAPTER_CONFIG")
    if path:
        return path
    return str(Path(__file__).with_name("config.json"))


def _load_app_config() -> AppConfig:
    path = _get_config_path()
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise SystemExit(f"Missing config file: {path}") from e

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in config file: {path}: {e}") from e

    if not isinstance(obj, dict):
        raise SystemExit(f"Invalid config file: {path}: must be a JSON object")

    # -- server --
    server_obj = obj.get("server")
    if not isinstance(server_obj, dict):
        raise SystemExit("Invalid config: server must be an object")

    bind_host = server_obj.get("bindHost", "127.0.0.1")
    port = server_obj.get("port", 19199)
    rpc_path = server_obj.get("rpcPath", "/rpc")
    public_url = server_obj.get("publicUrl")

    if not isinstance(bind_host, str) or not bind_host:
        raise SystemExit("Invalid config: server.bindHost must be a non-empty string")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise SystemExit("Invalid config: server.port must be an integer in range 1..65535")
    if not isinstance(rpc_path, str) or not rpc_path.startswith("/"):
        raise SystemExit("Invalid config: server.rpcPath must be a string starting with '/'")
    if public_url is not None and not isinstance(public_url, str):
        raise SystemExit("Invalid config: server.publicUrl must be a string or null")

    # -- langchain --
    lc_obj = obj.get("langchain")
    if not isinstance(lc_obj, dict):
        raise SystemExit("Invalid config: langchain must be an object")

    base_url = lc_obj.get("baseUrl", "https://api.chatanywhere.tech/v1")
    api_key = lc_obj.get("apiKey")
    api_key_env = lc_obj.get("apiKeyEnv", ["LANGCHAIN_API_KEY"])
    model = lc_obj.get("model", "openai:gpt-4o")
    backend_root_dir = lc_obj.get("backendRootDir")
    virtual_mode = lc_obj.get("virtualMode", True)
    timeout_seconds = lc_obj.get("timeoutSeconds", 600)

    if not isinstance(base_url, str) or not base_url:
        raise SystemExit("Invalid config: langchain.baseUrl must be a non-empty string")
    if api_key is not None and not isinstance(api_key, str):
        raise SystemExit("Invalid config: langchain.apiKey must be a string or null")
    if isinstance(api_key_env, str):
        api_key_env = [api_key_env]
    if not isinstance(api_key_env, list) or not all(isinstance(x, str) and x for x in api_key_env):
        raise SystemExit("Invalid config: langchain.apiKeyEnv must be a string or array of strings")
    if not isinstance(model, str) or not model:
        raise SystemExit("Invalid config: langchain.model must be a non-empty string")
    if backend_root_dir is not None and not isinstance(backend_root_dir, str):
        raise SystemExit("Invalid config: langchain.backendRootDir must be a string or null")
    if not isinstance(virtual_mode, bool):
        raise SystemExit("Invalid config: langchain.virtualMode must be a boolean")
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise SystemExit("Invalid config: langchain.timeoutSeconds must be a positive integer")

    return AppConfig(
        server=ServerConfig(bind_host=bind_host, port=port, rpc_path=rpc_path, public_url=public_url),
        langchain=LangChainConfig(
            base_url=base_url,
            api_key=api_key,
            api_key_env=api_key_env,
            model=model,
            backend_root_dir=backend_root_dir,
            virtual_mode=virtual_mode,
            timeout_seconds=timeout_seconds,
        ),
    )


# ---------------------------------------------------------------------------
# A2A helpers
# ---------------------------------------------------------------------------

def _extract_text_from_a2a_send_message_params(params: Any) -> str:
    if isinstance(params, str):
        return params
    if not isinstance(params, dict):
        return ""

    msg = params.get("message")
    if isinstance(msg, str):
        return msg
    if not isinstance(msg, dict):
        return ""

    parts = msg.get("parts")
    if not isinstance(parts, list):
        return ""

    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text:
            return text
        data = part.get("data")
        if isinstance(data, dict):
            maybe_messages = data.get("messages")
            if isinstance(maybe_messages, list):
                for m in reversed(maybe_messages):
                    if not isinstance(m, dict):
                        continue
                    if m.get("role") != "user":
                        continue
                    content = m.get("content")
                    if isinstance(content, str) and content:
                        return content
    return ""


def _openai_chat_completion_response(*, model: str, content: str) -> dict[str, Any]:
    now = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": now,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def _openai_chat_completion_chunk(
    *,
    stream_id: str,
    created: int,
    model: str,
    delta: dict[str, Any],
    finish_reason: Optional[str],
) -> dict[str, Any]:
    choice: dict[str, Any] = {"index": 0, "delta": delta}
    if finish_reason is not None:
        choice["finish_reason"] = finish_reason
    return {
        "id": stream_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [choice],
    }


def _jsonrpc_error(
    *,
    req_id: Any,
    code: int,
    message: str,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _extended_agent_card(cfg: AppConfig) -> dict[str, Any]:
    url = cfg.server.public_url
    if not url:
        url = f"http://{cfg.server.bind_host}:{cfg.server.port}{cfg.server.rpc_path}"
    return {
        "name": "LangChain A2A Chat",
        "description": "A2A JSON-RPC wrapper for LangChain + DeepAgents",
        "supportedInterfaces": [
            {"url": url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        ],
        "capabilities": {"streaming": True, "pushNotifications": False},
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json"],
    }


# ---------------------------------------------------------------------------
# A2A request handlers
# ---------------------------------------------------------------------------

async def _handle_send_message(*, params: Any, cfg: AppConfig) -> dict[str, Any]:
    text = _extract_text_from_a2a_send_message_params(params)
    if not text:
        raise ValueError("missing message text")

    api_key = _resolve_api_key(cfg.langchain.api_key, cfg.langchain.api_key_env)

    assistant_content = await run_in_threadpool(
        _invoke_langchain,
        base_url=cfg.langchain.base_url,
        api_key=api_key,
        model_name=cfg.langchain.model,
        message=text,
        backend_root_dir=cfg.langchain.backend_root_dir,
        virtual_mode=cfg.langchain.virtual_mode,
    )

    openai_resp = _openai_chat_completion_response(
        model=cfg.langchain.model, content=assistant_content
    )

    context_id = None
    task_id = None
    if isinstance(params, dict) and isinstance(params.get("message"), dict):
        msg = params["message"]
        if isinstance(msg.get("contextId"), str):
            context_id = msg["contextId"]
        if isinstance(msg.get("taskId"), str):
            task_id = msg["taskId"]
    if context_id is None:
        context_id = str(uuid.uuid4())

    message_obj: dict[str, Any] = {
        "messageId": str(uuid.uuid4()),
        "contextId": context_id,
        "role": "ROLE_AGENT",
        "parts": [{"data": openai_resp}],
    }
    if task_id is not None:
        message_obj["taskId"] = task_id

    return {"message": message_obj}


_SENTINEL = object()
_HEARTBEAT_INTERVAL = 15  # seconds between SSE keep-alive comments


async def _send_message_sse(*, req_id: Any, params: Any, cfg: AppConfig) -> AsyncIterable[str]:
    """Async SSE generator with heartbeat keep-alive.

    LangChain / DeepAgents execution runs in a background thread.  While it
    blocks, this generator sends SSE comment lines (``: heartbeat``) every
    ``_HEARTBEAT_INTERVAL`` seconds so the downstream caller's read-timeout
    does not fire.
    """
    if req_id is None:
        return

    try:
        text = _extract_text_from_a2a_send_message_params(params)
        if not text:
            raise ValueError("missing message text")

        api_key = _resolve_api_key(cfg.langchain.api_key, cfg.langchain.api_key_env)

        # Run blocking LangChain execution in a thread; bridge via queue.
        q: queue.Queue = queue.Queue()

        def _worker() -> None:
            try:
                result = _invoke_langchain(
                    base_url=cfg.langchain.base_url,
                    api_key=api_key,
                    model_name=cfg.langchain.model,
                    message=text,
                    backend_root_dir=cfg.langchain.backend_root_dir,
                    virtual_mode=cfg.langchain.virtual_mode,
                )
                q.put(result)
            except Exception as exc:
                q.put(exc)
            finally:
                q.put(_SENTINEL)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        assistant_content = None
        while True:
            try:
                item = q.get(timeout=_HEARTBEAT_INTERVAL)
            except queue.Empty:
                yield ": heartbeat\n\n"
                continue

            if item is _SENTINEL:
                break
            if isinstance(item, Exception):
                raise item
            assistant_content = item

        if assistant_content is None:
            raise RuntimeError("LangChain returned no result")

        context_id = None
        task_id = None
        if isinstance(params, dict) and isinstance(params.get("message"), dict):
            msg = params["message"]
            if isinstance(msg.get("contextId"), str):
                context_id = msg["contextId"]
            if isinstance(msg.get("taskId"), str):
                task_id = msg["taskId"]
        if context_id is None:
            context_id = str(uuid.uuid4())

        created = int(time.time())
        stream_id = f"chatcmpl-{uuid.uuid4().hex}"

        # LangChain invoke is non-streaming; emit a single content chunk + stop chunk
        content_chunk = _openai_chat_completion_chunk(
            stream_id=stream_id,
            created=created,
            model=cfg.langchain.model,
            delta={"role": "assistant", "content": assistant_content},
            finish_reason=None,
        )

        message_obj: dict[str, Any] = {
            "messageId": str(uuid.uuid4()),
            "contextId": context_id,
            "role": "ROLE_AGENT",
            "parts": [{"data": content_chunk}],
        }
        if task_id is not None:
            message_obj["taskId"] = task_id

        frame = {"jsonrpc": "2.0", "id": req_id, "result": {"message": message_obj}}
        yield f"data: {json.dumps(frame)}\n\n"

        # Final stop chunk
        stop_chunk = _openai_chat_completion_chunk(
            stream_id=stream_id,
            created=created,
            model=cfg.langchain.model,
            delta={},
            finish_reason="stop",
        )

        stop_msg: dict[str, Any] = {
            "messageId": str(uuid.uuid4()),
            "contextId": context_id,
            "role": "ROLE_AGENT",
            "parts": [{"data": stop_chunk}],
        }
        if task_id is not None:
            stop_msg["taskId"] = task_id

        stop_frame = {"jsonrpc": "2.0", "id": req_id, "result": {"message": stop_msg}}
        yield f"data: {json.dumps(stop_frame)}\n\n"

    except ValueError as e:
        yield f"data: {json.dumps(_jsonrpc_error(req_id=req_id, code=-32602, message='Invalid params', data={'error': str(e)}))}\n\n"
    except Exception as e:
        yield f"data: {json.dumps(_jsonrpc_error(req_id=req_id, code=-32603, message='Internal error', data={'error': str(e)}))}\n\n"


async def _handle_one(*, req: Any, cfg: AppConfig) -> Optional[dict[str, Any]]:
    if not isinstance(req, dict):
        return _jsonrpc_error(req_id=None, code=-32600, message="Invalid Request")

    if req.get("jsonrpc") != "2.0":
        return _jsonrpc_error(req_id=req.get("id"), code=-32600, message="Invalid Request")

    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params")

    if req_id is None:
        return None

    if not isinstance(method, str) or not method:
        return _jsonrpc_error(req_id=req_id, code=-32600, message="Invalid Request")

    if method == "SendMessage":
        try:
            result = await _handle_send_message(params=params, cfg=cfg)
        except ValueError as e:
            return _jsonrpc_error(req_id=req_id, code=-32602, message="Invalid params", data={"error": str(e)})
        except Exception as e:
            return _jsonrpc_error(req_id=req_id, code=-32603, message="Internal error", data={"error": str(e)})
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    if method == "GetExtendedAgentCard":
        return {"jsonrpc": "2.0", "id": req_id, "result": _extended_agent_card(cfg)}

    return _jsonrpc_error(req_id=req_id, code=-32601, message="Method not found", data={"method": method})


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

def create_app(cfg: AppConfig) -> FastAPI:
    app = FastAPI()

    @app.get("/.well-known/agent-card.json")
    async def agent_card() -> JSONResponse:
        return JSONResponse(_extended_agent_card(cfg))

    async def rpc(request: Request):
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(_jsonrpc_error(req_id=None, code=-32700, message="Parse error"))

        if isinstance(payload, dict) and payload.get("method") == "SendMessage":
            params = payload.get("params")
            is_stream = False
            if isinstance(params, dict) and isinstance(params.get("stream"), bool):
                is_stream = params["stream"]

            if is_stream:
                req_id = payload.get("id")
                if payload.get("jsonrpc") != "2.0" or req_id is None:
                    return JSONResponse(
                        _jsonrpc_error(req_id=req_id, code=-32600, message="Invalid Request")
                    )

                return StreamingResponse(
                    _send_message_sse(req_id=req_id, params=params, cfg=cfg),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache"},
                )

        if isinstance(payload, list):
            res_list: list[dict[str, Any]] = []
            for item in payload:
                r = await _handle_one(req=item, cfg=cfg)
                if r is not None:
                    res_list.append(r)
            if not res_list:
                return PlainTextResponse("", status_code=204)
            return JSONResponse(res_list)

        res = await _handle_one(req=payload, cfg=cfg)
        if res is None:
            return PlainTextResponse("", status_code=204)
        return JSONResponse(res)

    app.add_api_route(cfg.server.rpc_path, rpc, methods=["POST"])

    return app


def main() -> None:
    cfg = _load_app_config()
    app = create_app(cfg)

    try:
        import uvicorn
    except ModuleNotFoundError as e:
        raise SystemExit(
            "Missing dependency 'uvicorn'. Install it in the Python environment you're using:\n"
            "  python -m pip install uvicorn"
        ) from e

    uvicorn.run(app, host=cfg.server.bind_host, port=cfg.server.port)


if __name__ == "__main__":
    main()
