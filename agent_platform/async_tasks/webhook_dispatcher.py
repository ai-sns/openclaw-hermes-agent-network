"""
Webhook Dispatcher (re-export from handlers)

This module re-exports the WebhookDispatcher from handlers for convenience.
"""

from agent_platform.gateway.handlers.webhook import WebhookDispatcher, get_webhook_dispatcher

__all__ = ["WebhookDispatcher", "get_webhook_dispatcher"]
