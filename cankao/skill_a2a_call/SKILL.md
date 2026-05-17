---
name: a2a-call
description: Call a peer agent's A2A JSON-RPC endpoint. Supports tasks/send (send a task message) and tasks/get (query task status). Trigger when the user or agent wants to invoke a remote A2A skill over HTTP JSON-RPC.
metadata:
  {
    "openclaw":
      {
        "emoji": "📡",
        "install":
          [
            {
              "id": "python-brew",
              "kind": "brew",
              "formula": "python",
              "bins": ["python3"],
              "label": "Install Python (brew)",
            },
          ],
      },
  }
---

# A2A JSON-RPC Call

Invoke A2A JSON-RPC methods on a remote agent endpoint. The script handles JSON-RPC 2.0 envelope construction, HTTP POST, and result parsing automatically.

## Quick Start

Send a task to a peer agent:

```bash
python3 {baseDir}/scripts/a2a_call.py \
  --url "http://localhost:8789/a2a/" \
  --method tasks/send \
  --message-text "Hello, what is your status?" \
  --skill-id "urn:xmpp:a2a:cmd:tasks"
```

Query a task status:

```bash
python3 {baseDir}/scripts/a2a_call.py \
  --url "http://localhost:8789/a2a/" \
  --method tasks/get \
  --task-id "task-abc123"
```

## Parameters

All parameters are optional on the CLI except `--url` and `--method`:

```bash
python3 {baseDir}/scripts/a2a_call.py \
  --url "http://localhost:8789/a2a/" \
  --method tasks/send \
  --message-text "Hello" \
  --message-data '{"key":"value"}' \
  --skill-id "urn:xmpp:a2a:cmd:tasks" \
  --metadata '{"sender":"alice@example.com"}'
```

- `--url` (string, **required**): The peer's A2A JSON-RPC endpoint URL.
- `--method` (string, **required**): `"tasks/send"` or `"tasks/get"`.
- `--task-id` (string, optional): Required for `tasks/get`. The task ID to query.
- `--message-text` (string, optional): For `tasks/send` — a text message to include.
- `--message-data` (string, optional): For `tasks/send` — a data payload as a JSON string.
- `--skill-id` (string, optional): For `tasks/send` — the target skill ID on the peer agent.
- `--metadata` (string, optional): For `tasks/send` — extra metadata as a JSON string.

### Stdin JSON Mode

Alternatively, pass parameters as JSON on stdin (this is the default OpenClaw invocation mode):

```bash
echo '{"url":"http://localhost:8789/a2a/","method":"tasks/send","message_text":"Hello"}' | \
  python3 {baseDir}/scripts/a2a_call.py --stdin
```

The JSON keys match the CLI long-option names with underscores (`message_text`, `message_data`, `skill_id`, etc.).

## Output

The script prints a JSON object to stdout:

- `ok` (bool): Whether the call succeeded.
- `result` (object): The JSON-RPC result on success.
- `error` (string): Error message on failure.

Example success output:

```json
{
  "ok": true,
  "result": {
    "id": "task-abc123",
    "status": "completed",
    "artifacts": [
      {
        "type": "text",
        "text": "I am online and ready to help."
      }
    ]
  }
}
```

Example error output:

```json
{
  "ok": false,
  "error": "HTTP 404: Not Found"
}
```
