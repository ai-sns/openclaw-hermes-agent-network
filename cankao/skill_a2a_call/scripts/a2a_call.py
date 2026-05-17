"""
A2A JSON-RPC Call Skill

Sends a JSON-RPC 2.0 request to a peer agent's A2A endpoint.
Supports methods: tasks/send, tasks/get.

Usage (CLI):
  python3 {baseDir}/scripts/a2a_call.py \
    --url http://localhost:8789/a2a/ \
    --method tasks/send \
    --message-text "Hello!" \
    --skill-id urn:xmpp:a2a:cmd:tasks

Usage (stdin JSON - OpenClaw mode):
  echo '{"url":"http://localhost:8789/a2a/","method":"tasks/send","message_text":"Hello"}' | \
    python3 {baseDir}/scripts/a2a_call.py --stdin

Output (stdout JSON):
  {"ok": true, "result": {...}}
  {"ok": false, "error": "..."}
"""

import argparse
import json
import sys
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description="A2A JSON-RPC Call Skill")
    parser.add_argument("--url", help="Peer A2A JSON-RPC endpoint URL")
    parser.add_argument("--method", help='JSON-RPC method, e.g. "tasks/send" or "tasks/get"')
    parser.add_argument("--task-id", help="Task ID (for tasks/get)")
    parser.add_argument("--message-text", help="Text message (for tasks/send)")
    parser.add_argument("--message-data", help="Data payload as JSON string (for tasks/send)")
    parser.add_argument("--skill-id", help="Target skill ID on the peer agent (for tasks/send)")
    parser.add_argument("--metadata", help="Extra metadata as JSON string (for tasks/send)")
    parser.add_argument("--stdin", action="store_true", help="Read parameters from stdin as JSON")
    args = parser.parse_args()

    # ── Resolve parameters ──
    if args.stdin:
        try:
            raw = sys.stdin.read().strip()
            if not raw:
                _output(False, error="No input provided on stdin")
                return
            params = json.loads(raw)
        except json.JSONDecodeError as e:
            _output(False, error=f"Invalid JSON input: {e}")
            return
    else:
        params = {}
        if args.url:
            params["url"] = args.url
        if args.method:
            params["method"] = args.method
        if args.task_id:
            params["task_id"] = args.task_id
        if args.message_text:
            params["message_text"] = args.message_text
        if args.message_data:
            try:
                params["message_data"] = json.loads(args.message_data)
            except json.JSONDecodeError:
                _output(False, error="--message-data must be valid JSON")
                return
        if args.skill_id:
            params["skill_id"] = args.skill_id
        if args.metadata:
            try:
                params["metadata"] = json.loads(args.metadata)
            except json.JSONDecodeError:
                _output(False, error="--metadata must be valid JSON")
                return

    url = (params.get("url") or "").strip()
    method = (params.get("method") or "").strip()

    if not url:
        _output(False, error="'url' is required")
        return

    if not method:
        _output(False, error="'method' is required")
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
