---
name: Send to Remote Agent
skill_key: send_to_remote_agent
description: Call a remote agent via A2A JSON-RPC protocol. Resolves the agent from the first aisns_cfg record (agent_id -> agent_cfg), then sends a SendMessage JSON-RPC request with xmpp_account, trade_id, and description as message content.
instructions: Call by agent when you need to invoke a remote agent, send a task or trade-related message to a peer agent via A2A protocol.
requires:
  always: true
runner:
  kind: python_file
  target: send_to_remote_agent.py
---

# Send to Remote Agent

Invoke a remote agent through the A2A (Agent-to-Agent) JSON-RPC protocol.

Agent resolution: first `aisns_cfg` record → `agent_id` → `agent_cfg` table → agent's `memo` JSON → `url` (A2A endpoint).

The `xmpp_account`, `trade_id`, and `description` are all included as message content sent to the remote agent.

## Parameters

This skill accepts a JSON object as input params.

- `description` (string, **required**)
  - The message content to send to the remote agent.

- `xmpp_account` (string, optional)
  - XMPP JID to include in the message content (e.g. `user@domain.com`).

- `trade_id` (string, optional)
  - A trade identifier to include in the message content.

- `context_id` (string, optional)
  - A2A conversation context ID. Defaults to `"default"` if not provided.

## How to use

1. Call `read_skill` with `skill_key: "send_to_remote_agent"` to read this document.
2. Then call `run_doc_skill` with `skill_key: "send_to_remote_agent"` and `params`.

Example (with xmpp_account and trade_id):

```json
{
  "skill_key": "send_to_remote_agent",
  "params": {
    "xmpp_account": "bob@example.com",
    "trade_id": "TRD-20250424-001",
    "description": "Payment received. Your digital artwork has been delivered."
  }
}
```

Example (description only):

```json
{
  "skill_key": "send_to_remote_agent",
  "params": {
    "description": "Please process this order."
  }
}
```

## Output

The runner prints a JSON object to stdout with:

- `ok` (bool): Whether the A2A call succeeded.
- `reply` (string): The text response from the remote agent.
- `agent_name` (string): The name of the resolved agent.
- `rpc_url` (string): The A2A endpoint URL that was called.
- `trade_id` (string, optional): The trade_id that was included, if any.
- `error` (string): Error message on failure.
