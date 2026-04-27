"""
A2A JSON-RPC Call Skill

Sends a JSON-RPC 2.0 request to a peer agent's A2A endpoint.
Supports methods: tasks/send, tasks/get.

Input (stdin JSON):
  url          - A2A endpoint URL (required)
  method       - "tasks/send" or "tasks/get" (required)
  task_id      - task ID for tasks/get (optional)
  message_text - text message for tasks/send (optional)
  message_data - data payload for tasks/send (optional)
  skill_id     - target skill on the peer agent (optional)
  metadata     - extra metadata dict (optional)

Output (stdout JSON):
  ok     - bool
  result - JSON-RPC result object on success
  error  - error string on failure
"""

import sys
import json
import urllib.request
import uuid


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            _output(False, error="No input provided")
            return
        params = json.loads(raw)
    except json.JSONDecodeError as e:
        _output(False, error=f"Invalid JSON input: {e}")
        return

    url = (params.get("url") or "").strip()
    method = (params.get("method") or "").strip()

    if not url:
        _output(False, error="'url' is required")
        return

    if method not in ("tasks/send", "tasks/get"):
        _output(False, error=f"Unsupported method: {method}. Use 'tasks/send' or 'tasks/get'.")
        return

    rpc_id = str(uuid.uuid4())[:8]

    if method == "tasks/send":
        rpc_params = _build_tasks_send_params(params, rpc_id)
    else:
        rpc_params = _build_tasks_get_params(params)

    if rpc_params is None:
        # Error already output inside builder
        return

    body = {
        "jsonrpc": "2.0",
        "method": method,
        "params": rpc_params,
        "id": rpc_id,
    }

    try:
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        # Replace localhost with 127.0.0.1 to avoid IPv6 issues on Windows
        fetch_url = url.replace("://localhost", "://127.0.0.1")
        req = urllib.request.Request(
            fetch_url,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Host": "localhost" if "localhost" in url else "",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_text = resp.read().decode("utf-8")

        resp_json = json.loads(resp_text)

        if "error" in resp_json and resp_json["error"]:
            err = resp_json["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            _output(False, error=f"JSON-RPC error: {msg}")
            return

        result = resp_json.get("result", {})
        # Truncate large results to avoid overwhelming the LLM context
        result_str = json.dumps(result, ensure_ascii=False)
        if len(result_str) > 3000:
            result_str = result_str[:3000] + "...(truncated)"
            result = json.loads(result_str[:3000] + "}")  # best-effort
        _output(True, result=resp_json.get("result"))

    except urllib.error.HTTPError as e:
        resp_body = ""
        try:
            resp_body = e.read().decode("utf-8")[:500]
        except Exception:
            pass
        _output(False, error=f"HTTP {e.code}: {resp_body or e.reason}")
    except urllib.error.URLError as e:
        _output(False, error=f"URL error: {e.reason}")
    except Exception as e:
        _output(False, error=f"Request failed: {e}")


def _build_tasks_send_params(params: dict, rpc_id: str) -> dict:
    """Build the params object for tasks/send."""
    parts = []

    message_text = (params.get("message_text") or "").strip()
    if message_text:
        parts.append({"type": "text", "text": message_text})

    message_data = params.get("message_data")
    if isinstance(message_data, dict) and message_data:
        parts.append({"type": "data", "data": message_data})

    if not parts:
        # Default: send an empty text part so the request is valid
        parts.append({"type": "text", "text": "Hello"})

    rpc_params = {
        "id": f"task-{rpc_id}",
        "message": {
            "role": "user",
            "parts": parts,
        },
    }

    skill_id = (params.get("skill_id") or "").strip()
    if skill_id:
        rpc_params["skillId"] = skill_id

    metadata = params.get("metadata")
    if isinstance(metadata, dict) and metadata:
        rpc_params["metadata"] = metadata

    return rpc_params


def _build_tasks_get_params(params: dict):
    """Build the params object for tasks/get."""
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        _output(False, error="'task_id' is required for tasks/get")
        return None
    return {"id": task_id}


def _output(ok: bool, result=None, error: str = ""):
    """Write the result JSON to stdout."""
    out = {"ok": ok}
    if result is not None:
        out["result"] = result
    if error:
        out["error"] = error
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
