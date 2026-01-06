"""
Webhook Handlers

Provides webhook callback functionality for async tasks.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
import asyncio
import httpx
import hashlib
import hmac
import json
from datetime import datetime
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from agent_platform.gateway.schemas.requests import WebhookPayload, TaskStatus


logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


class WebhookDispatcher:
    """
    Webhook Dispatcher

    Handles sending webhook callbacks with:
    - Retry logic
    - Signature verification
    - Delivery tracking
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        timeout: float = 30.0
    ):
        """
        Initialize webhook dispatcher.

        Args:
            secret_key: Secret for HMAC signature
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
            timeout: HTTP request timeout
        """
        self.secret_key = secret_key or "default-webhook-secret"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self._delivery_log: Dict[str, Dict] = {}

    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for payload"""
        signature = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def _verify_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature"""
        expected = self._generate_signature(payload)
        return hmac.compare_digest(expected, signature)

    async def send_webhook(
        self,
        url: str,
        payload: WebhookPayload,
        webhook_id: Optional[str] = None
    ) -> bool:
        """
        Send a webhook callback.

        Args:
            url: Webhook URL
            payload: Webhook payload
            webhook_id: Optional webhook ID for tracking

        Returns:
            True if successful
        """
        webhook_id = webhook_id or f"wh_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        # Convert payload to JSON
        payload_json = payload.json()

        # Generate signature
        signature = self._generate_signature(payload_json)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-ID": webhook_id,
            "X-Webhook-Timestamp": datetime.now().isoformat()
        }

        # Track delivery
        self._delivery_log[webhook_id] = {
            "url": url,
            "payload": payload.dict(),
            "status": "pending",
            "attempts": 0,
            "created_at": datetime.now().isoformat()
        }

        # Send with retries
        for attempt in range(self.max_retries):
            try:
                self._delivery_log[webhook_id]["attempts"] = attempt + 1

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        url,
                        content=payload_json,
                        headers=headers
                    )

                    if response.status_code >= 200 and response.status_code < 300:
                        self._delivery_log[webhook_id]["status"] = "success"
                        self._delivery_log[webhook_id]["response_code"] = response.status_code
                        self._delivery_log[webhook_id]["delivered_at"] = datetime.now().isoformat()
                        logger.info(f"Webhook delivered: {webhook_id} to {url}")
                        return True
                    else:
                        logger.warning(
                            f"Webhook failed (attempt {attempt + 1}): "
                            f"{response.status_code} - {response.text[:200]}"
                        )

            except Exception as e:
                logger.error(f"Webhook error (attempt {attempt + 1}): {e}")

            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        # All retries failed
        self._delivery_log[webhook_id]["status"] = "failed"
        self._delivery_log[webhook_id]["failed_at"] = datetime.now().isoformat()
        logger.error(f"Webhook failed after {self.max_retries} attempts: {webhook_id}")
        return False

    async def send_task_completed(
        self,
        url: str,
        task_id: str,
        output_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send task completed webhook"""
        payload = WebhookPayload(
            event_type="task.completed",
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            output_data=output_data
        )
        return await self.send_webhook(url, payload)

    async def send_task_failed(
        self,
        url: str,
        task_id: str,
        error: str
    ) -> bool:
        """Send task failed webhook"""
        payload = WebhookPayload(
            event_type="task.failed",
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=error
        )
        return await self.send_webhook(url, payload)

    def get_delivery_status(self, webhook_id: str) -> Optional[Dict]:
        """Get delivery status for a webhook"""
        return self._delivery_log.get(webhook_id)


# Global dispatcher instance
_webhook_dispatcher: Optional[WebhookDispatcher] = None


def get_webhook_dispatcher() -> WebhookDispatcher:
    """Get the webhook dispatcher instance"""
    global _webhook_dispatcher
    if _webhook_dispatcher is None:
        _webhook_dispatcher = WebhookDispatcher()
    return _webhook_dispatcher


# ============ Webhook Registration Endpoints ============

@webhook_router.post("/test")
async def test_webhook(
    url: str,
    background_tasks: BackgroundTasks
):
    """Test a webhook URL"""
    dispatcher = get_webhook_dispatcher()

    payload = WebhookPayload(
        event_type="test",
        task_id="test_task",
        status=TaskStatus.COMPLETED,
        output_data={"message": "This is a test webhook"}
    )

    # Send in background
    background_tasks.add_task(dispatcher.send_webhook, url, payload)

    return {
        "success": True,
        "message": "Test webhook queued"
    }


@webhook_router.get("/deliveries/{webhook_id}")
async def get_delivery_status(webhook_id: str):
    """Get webhook delivery status"""
    dispatcher = get_webhook_dispatcher()
    status = dispatcher.get_delivery_status(webhook_id)

    if not status:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return status
