import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import requests
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing dependency 'requests'. Install it in the Python environment you're using:\n"
        "  python -m pip install requests\n"
        "Or, if you're using a venv:\n"
        "  <venv>\\Scripts\\python.exe -m pip install requests"
    ) from e


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


DEFAULT_BASE_URL = "http://172.29.218.26:8642"
DEFAULT_MODEL = "hermes-agent"


def _iter_sse_data_lines(resp: requests.Response) -> Iterable[str]:
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if raw.startswith("data: "):
            yield raw[len("data: ") :].strip()


def _hermes_chat_stream(
    *,
    base_url: str,
    api_key: str,
    model: str,
    message: str,
    timeout_seconds: int,
) -> Iterable[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    print("cjrok")
    print(message)
    body = {
        "model": model,
        "stream": True,
        "messages": [{"role": "user", "content": message}],
    }

    s = requests.Session()
    s.trust_env = False

    with s.post(
        url,
        headers=headers,
        json=body,
        stream=True,
        timeout=timeout_seconds,
        allow_redirects=False,
    ) as r:
        if 300 <= r.status_code < 400:
            location = r.headers.get("Location")
            raise RuntimeError(
                f"Unexpected redirect ({r.status_code}) to {location!r}. "
                f"Refusing to follow redirects; check baseUrl (use the Hermes root like {DEFAULT_BASE_URL})."
            )
        if r.status_code == 405:
            allow = r.headers.get("Allow")
            raise RuntimeError(
                f"HTTP 405 Method Not Allowed from {r.url}. "
                f"method={getattr(r.request, 'method', None)!r} allow={allow!r}. "
                "This often happens if a redirect/proxy turned your POST into a GET."
            )
        r.raise_for_status()
        for data_str in _iter_sse_data_lines(r):
            if data_str == "[DONE]":
                break
            yield json.loads(data_str)


@dataclass(frozen=True)
class ServerConfig:
    bind_host: str
    port: int
    rpc_path: str
    public_url: Optional[str]


@dataclass(frozen=True)
class HermesConfig:
    base_url: str
    api_key: Optional[str]
    api_key_env: list[str]
    model: str
    timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    hermes: HermesConfig


def chat_once(
    *,
    base_url: str,
    api_key: str,
    model: str,
    message: str,
    stream: bool,
    timeout_seconds: int = 60,
) -> str:
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    print("cjrok2")
    print(message)
    body = {
        "model": model,
        "stream": stream,
        "messages": [{"role": "user", "content": message}],
    }

    s = requests.Session()
    s.trust_env = False

    if not stream:
        r = s.post(url, headers=headers, json=body, timeout=timeout_seconds, allow_redirects=False)
        if 300 <= r.status_code < 400:
            location = r.headers.get("Location")
            raise RuntimeError(
                f"Unexpected redirect ({r.status_code}) to {location!r}. "
                f"Refusing to follow redirects; check --base-url (use the Hermes root like {DEFAULT_BASE_URL})."
            )
        if r.status_code == 405:
            allow = r.headers.get("Allow")
            raise RuntimeError(
                f"HTTP 405 Method Not Allowed from {r.url}. "
                f"method={getattr(r.request, 'method', None)!r} allow={allow!r}. "
                "This often happens if a redirect/proxy turned your POST into a GET."
            )
        r.raise_for_status()
        data = r.json()
        return str(data["choices"][0]["message"]["content"])

    full: list[str] = []
    with s.post(
        url,
        headers=headers,
        json=body,
        stream=True,
        timeout=timeout_seconds,
        allow_redirects=False,
    ) as r:
        if 300 <= r.status_code < 400:
            location = r.headers.get("Location")
            raise RuntimeError(
                f"Unexpected redirect ({r.status_code}) to {location!r}. "
                f"Refusing to follow redirects; check --base-url (use the Hermes root like {DEFAULT_BASE_URL})."
            )
        if r.status_code == 405:
            allow = r.headers.get("Allow")
            raise RuntimeError(
                f"HTTP 405 Method Not Allowed from {r.url}. "
                f"method={getattr(r.request, 'method', None)!r} allow={allow!r}. "
                "This often happens if a redirect/proxy turned your POST into a GET."
            )
        r.raise_for_status()
        for data_str in _iter_sse_data_lines(r):
            if data_str == "[DONE]":
                break
            chunk = json.loads(data_str)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if isinstance(content, str) and content:
                print(content, end="", flush=True)
                full.append(content)
        print()

    return "".join(full)


def _resolve_api_key(api_key: Optional[str], api_key_env: list[str]) -> str:
    if api_key:
        return api_key
    for env_key in api_key_env:
        v = os.environ.get(env_key)
        if v:
            return v
    raise SystemExit("Missing API key. Set HERMES_API_KEY (or configure hermes.apiKey / hermes.apiKeyEnv).")


def _get_config_path() -> str:
    path = os.environ.get("HERMES_A2A_CONFIG")
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

    server_obj = obj.get("server")
    if not isinstance(server_obj, dict):
        raise SystemExit("Invalid config: server must be an object")

    bind_host = server_obj.get("bindHost", "127.0.0.1")
    port = server_obj.get("port", 19099)
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

    hermes_obj = obj.get("hermes")
    if not isinstance(hermes_obj, dict):
        raise SystemExit("Invalid config: hermes must be an object")

    base_url = hermes_obj.get("baseUrl", DEFAULT_BASE_URL)
    api_key = hermes_obj.get("apiKey")
    api_key_env = hermes_obj.get("apiKeyEnv", ["HERMES_API_KEY"])
    model = hermes_obj.get("model", DEFAULT_MODEL)
    timeout_seconds = hermes_obj.get("timeoutSeconds", 60)

    if not isinstance(base_url, str) or not base_url:
        raise SystemExit("Invalid config: hermes.baseUrl must be a non-empty string")
    if api_key is not None and not isinstance(api_key, str):
        raise SystemExit("Invalid config: hermes.apiKey must be a string or null")
    if isinstance(api_key_env, str):
        api_key_env = [api_key_env]
    if not isinstance(api_key_env, list) or not all(isinstance(x, str) and x for x in api_key_env):
        raise SystemExit("Invalid config: hermes.apiKeyEnv must be a string or array of strings")
    if not isinstance(model, str) or not model:
        raise SystemExit("Invalid config: hermes.model must be a non-empty string")
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise SystemExit("Invalid config: hermes.timeoutSeconds must be a positive integer")

    return AppConfig(
        server=ServerConfig(bind_host=bind_host, port=port, rpc_path=rpc_path, public_url=public_url),
        hermes=HermesConfig(
            base_url=base_url,
            api_key=api_key,
            api_key_env=api_key_env,
            model=model,
            timeout_seconds=timeout_seconds,
        ),
    )


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


def _openai_chat_completion_chunk(*, stream_id: str, created: int, model: str, delta: dict[str, Any], finish_reason: Optional[str]) -> dict[str, Any]:
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


def _jsonrpc_error(*, req_id: Any, code: int, message: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _extended_agent_card(cfg: AppConfig) -> dict[str, Any]:
    url = cfg.server.public_url
    if not url:
        url = f"http://{cfg.server.bind_host}:{cfg.server.port}{cfg.server.rpc_path}"
    return {
        "name": "Hermes A2A Chat",
        "description": "A2A JSON-RPC wrapper for Hermes API /v1/chat/completions",
        "supportedInterfaces": [{"url": url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
        "capabilities": {"streaming": True, "pushNotifications": False},
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json"],
    }


async def _handle_send_message(*, params: Any, cfg: AppConfig) -> dict[str, Any]:
    text = _extract_text_from_a2a_send_message_params(params)
    if not text:
        raise ValueError("missing message text")

    api_key = _resolve_api_key(cfg.hermes.api_key, cfg.hermes.api_key_env)

    assistant = await run_in_threadpool(
        chat_once,
        base_url=cfg.hermes.base_url,
        api_key=api_key,
        model=cfg.hermes.model,
        message=text,
        stream=False,
        timeout_seconds=cfg.hermes.timeout_seconds,
    )

    openai = _openai_chat_completion_response(model=cfg.hermes.model, content=assistant)

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
        "parts": [{"data": openai}],
    }
    if task_id is not None:
        message_obj["taskId"] = task_id

    return {"message": message_obj}


def _send_message_sse(*, req_id: Any, params: Any, cfg: AppConfig) -> Iterable[str]:
    if req_id is None:
        return

    try:
        text = _extract_text_from_a2a_send_message_params(params)
        if not text:
            raise ValueError("missing message text")

        api_key = _resolve_api_key(cfg.hermes.api_key, cfg.hermes.api_key_env)

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

        for chunk in _hermes_chat_stream(
            base_url=cfg.hermes.base_url,
            api_key=api_key,
            model=cfg.hermes.model,
            message=text,
            timeout_seconds=cfg.hermes.timeout_seconds,
        ):
            choice0 = chunk.get("choices", [{}])[0] if isinstance(chunk, dict) else {}
            if not isinstance(choice0, dict):
                continue

            delta = choice0.get("delta", {})
            if not isinstance(delta, dict):
                delta = {}
            finish_reason = choice0.get("finish_reason")
            if finish_reason is not None and not isinstance(finish_reason, str):
                finish_reason = None

            openai_chunk = _openai_chat_completion_chunk(
                stream_id=stream_id,
                created=created,
                model=cfg.hermes.model,
                delta={k: v for k, v in delta.items() if k in ("role", "content") and v is not None},
                finish_reason=finish_reason,
            )

            message_obj: dict[str, Any] = {
                "messageId": str(uuid.uuid4()),
                "contextId": context_id,
                "role": "ROLE_AGENT",
                "parts": [{"data": openai_chunk}],
            }
            if task_id is not None:
                message_obj["taskId"] = task_id

            frame = {"jsonrpc": "2.0", "id": req_id, "result": {"message": message_obj}}
            yield f"data: {json.dumps(frame)}\n\n"

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
                    return JSONResponse(_jsonrpc_error(req_id=req_id, code=-32600, message="Invalid Request"))

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
