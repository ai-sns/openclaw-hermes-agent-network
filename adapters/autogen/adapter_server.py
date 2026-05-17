import asyncio
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
    from autogenstudio.teammanager import TeamManager
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing dependency 'autogenstudio'. Install it in the Python environment you're using:\n"
        "  python -m pip install autogenstudio"
    ) from e


# ---------------------------------------------------------------------------
# AutoGen team execution helpers
# ---------------------------------------------------------------------------

def _convert_to_openai_format(result_message: Any, model: str) -> dict[str, Any]:
    """Convert AutoGen TeamManager result to OpenAI chat completion format."""
    messages = result_message.task_result.messages

    assistant_msg = None
    for msg in reversed(messages):
        if msg.source != "user":
            content = getattr(msg, "content", None)
            if content and content != "TERMINATE":
                assistant_msg = content
                break

    prompt_tokens = 0
    completion_tokens = 0
    for msg in messages:
        usage = getattr(msg, "models_usage", None)
        if usage:
            prompt_tokens += usage.prompt_tokens or 0
            completion_tokens += usage.completion_tokens or 0

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": assistant_msg or "",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


async def _run_autogen_team(
    *,
    team_file: str,
    message: str,
    model: str,
) -> dict[str, Any]:
    """Run a task through the AutoGen TeamManager and return OpenAI-format response."""
    team_manager = TeamManager()
    result_message = await team_manager.run(
        task=message,
        team_config=team_file,
    )
    return _convert_to_openai_format(result_message, model)


def _run_autogen_team_sync(
    *,
    team_file: str,
    message: str,
    model: str,
) -> dict[str, Any]:
    """Synchronous wrapper for _run_autogen_team."""
    return asyncio.run(
        _run_autogen_team(team_file=team_file, message=message, model=model)
    )


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
class AutoGenConfig:
    team_file: Optional[str]
    team_file_env: list[str]
    model: str
    timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    autogen: AutoGenConfig


def _resolve_team_file(team_file: Optional[str], team_file_env: list[str]) -> str:
    if team_file:
        return team_file
    for env_key in team_file_env:
        v = os.environ.get(env_key)
        if v:
            return v
    # Fallback: look for team.json next to this script
    default = str(Path(__file__).with_name("team.json"))
    if Path(default).exists():
        return default
    raise SystemExit(
        "Missing team config file. Set AUTOGENSTUDIO_TEAM_FILE "
        "(or configure autogen.teamFile / autogen.teamFileEnv)."
    )


def _get_config_path() -> str:
    path = os.environ.get("AUTOGEN_ADAPTER_CONFIG")
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

    bind_host = server_obj.get("bindHost", "0.0.0.0")
    port = server_obj.get("port", 8080)
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

    # -- autogen --
    ag_obj = obj.get("autogen")
    if not isinstance(ag_obj, dict):
        raise SystemExit("Invalid config: autogen must be an object")

    team_file = ag_obj.get("teamFile")
    team_file_env = ag_obj.get("teamFileEnv", ["AUTOGENSTUDIO_TEAM_FILE"])
    model = ag_obj.get("model", "autogen-team")
    timeout_seconds = ag_obj.get("timeoutSeconds", 600)

    if team_file is not None and not isinstance(team_file, str):
        raise SystemExit("Invalid config: autogen.teamFile must be a string or null")
    if isinstance(team_file_env, str):
        team_file_env = [team_file_env]
    if not isinstance(team_file_env, list) or not all(isinstance(x, str) and x for x in team_file_env):
        raise SystemExit("Invalid config: autogen.teamFileEnv must be a string or array of strings")
    if not isinstance(model, str) or not model:
        raise SystemExit("Invalid config: autogen.model must be a non-empty string")
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise SystemExit("Invalid config: autogen.timeoutSeconds must be a positive integer")

    return AppConfig(
        server=ServerConfig(bind_host=bind_host, port=port, rpc_path=rpc_path, public_url=public_url),
        autogen=AutoGenConfig(
            team_file=team_file,
            team_file_env=team_file_env,
            model=model,
            timeout_seconds=timeout_seconds,
        ),
    )


# ---------------------------------------------------------------------------
# A2A helpers (same as openclaw adapter_server)
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
        "name": "AutoGen A2A Chat",
        "description": "A2A JSON-RPC wrapper for AutoGen Studio TeamManager",
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

    team_file = _resolve_team_file(cfg.autogen.team_file, cfg.autogen.team_file_env)

    openai_resp = await run_in_threadpool(
        _run_autogen_team_sync,
        team_file=team_file,
        message=text,
        model=cfg.autogen.model,
    )

    # Extract assistant content from the OpenAI-format response
    assistant_content = openai_resp.get("choices", [{}])[0].get("message", {}).get("content", "")

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

    AutoGen team execution runs in a background thread.  While it blocks,
    this generator sends SSE comment lines (``: heartbeat``) every
    ``_HEARTBEAT_INTERVAL`` seconds so the downstream caller's read-timeout
    does not fire.
    """
    if req_id is None:
        return

    try:
        text = _extract_text_from_a2a_send_message_params(params)
        if not text:
            raise ValueError("missing message text")

        team_file = _resolve_team_file(cfg.autogen.team_file, cfg.autogen.team_file_env)

        # Run blocking AutoGen execution in a thread; bridge via queue.
        q: queue.Queue = queue.Queue()

        def _worker() -> None:
            try:
                result = _run_autogen_team_sync(
                    team_file=team_file,
                    message=text,
                    model=cfg.autogen.model,
                )
                q.put(result)
            except Exception as exc:
                q.put(exc)
            finally:
                q.put(_SENTINEL)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        openai_resp = None
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
            openai_resp = item

        if openai_resp is None:
            raise RuntimeError("AutoGen team returned no result")

        assistant_content = openai_resp.get("choices", [{}])[0].get("message", {}).get("content", "")

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

        # AutoGen does not natively stream; emit a single content chunk + stop chunk
        content_chunk = _openai_chat_completion_chunk(
            stream_id=stream_id,
            created=created,
            model=cfg.autogen.model,
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
            model=cfg.autogen.model,
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
# Also expose the original /predict/{task} endpoint from connectsample
# ---------------------------------------------------------------------------

def create_app(cfg: AppConfig) -> FastAPI:
    app = FastAPI()

    @app.get("/.well-known/agent-card.json")
    async def agent_card() -> JSONResponse:
        return JSONResponse(_extended_agent_card(cfg))

    @app.get("/predict/{task}")
    async def predict(task: str) -> JSONResponse:
        """Original connectsample.py endpoint - run a task via TeamManager."""
        try:
            team_file = _resolve_team_file(cfg.autogen.team_file, cfg.autogen.team_file_env)
            result = await _run_autogen_team(
                team_file=team_file,
                message=task,
                model=cfg.autogen.model,
            )
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse(
                {"error": {"message": str(e), "type": "server_error"}},
                status_code=500,
            )

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
