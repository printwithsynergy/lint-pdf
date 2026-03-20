"""Webhook dispatcher for delivering event notifications."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WebhookDeliveryResult:
    """Result of a webhook delivery attempt."""

    __slots__ = ("error", "event", "status_code", "success", "url")

    def __init__(
        self,
        url: str,
        event: str,
        status_code: int = 0,
        success: bool = False,
        error: str = "",
    ) -> None:
        self.url = url
        self.event = event
        self.status_code = status_code
        self.success = success
        self.error = error


class WebhookDispatcher:
    """Dispatches webhook notifications to registered endpoints.

    Supports HMAC-SHA256 signing, retry with exponential backoff,
    and delivery logging.
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout: float = 10.0,
        base_delay: float = 1.0,
    ) -> None:
        self._max_retries = max_retries
        self._timeout = timeout
        self._base_delay = base_delay

    @staticmethod
    def sign_payload(secret: str, body: str) -> str:
        """Generate HMAC-SHA256 signature for a webhook payload.

        Args:
            secret: Webhook secret key.
            body: JSON body string.

        Returns:
            Hex digest signature prefixed with "sha256=".
        """
        signature = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={signature}"

    def deliver(
        self,
        url: str,
        secret: str,
        event: str,
        payload: dict[str, Any],
    ) -> WebhookDeliveryResult:
        """Deliver a webhook notification with retry.

        Args:
            url: Webhook endpoint URL.
            secret: HMAC secret for signing.
            event: Event type (e.g. "job.completed").
            payload: Event payload dict.

        Returns:
            WebhookDeliveryResult with delivery status.
        """
        body = json.dumps(payload, sort_keys=True, default=str)
        signature = self.sign_payload(secret, body)

        headers = {
            "Content-Type": "application/json",
            "X-Grounded-Event": event,
            "X-Grounded-Signature": signature,
            "User-Agent": "Grounded-Webhook/0.1.0",
        }

        last_error = ""
        for attempt in range(self._max_retries + 1):
            try:
                response = httpx.post(
                    url,
                    content=body,
                    headers=headers,
                    timeout=self._timeout,
                )

                if response.status_code < 400:
                    logger.info(
                        "Webhook delivered: %s -> %s (status %d)",
                        event,
                        url,
                        response.status_code,
                    )
                    return WebhookDeliveryResult(
                        url=url,
                        event=event,
                        status_code=response.status_code,
                        success=True,
                    )

                last_error = f"HTTP {response.status_code}"
                logger.warning(
                    "Webhook delivery failed (attempt %d): %s -> %s: %s",
                    attempt + 1,
                    event,
                    url,
                    last_error,
                )

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Webhook delivery error (attempt %d): %s -> %s: %s",
                    attempt + 1,
                    event,
                    url,
                    last_error,
                )

            # Exponential backoff (skip on last attempt)
            if attempt < self._max_retries:
                import time

                delay = self._base_delay * (2**attempt)
                time.sleep(delay)

        logger.error(
            "Webhook delivery failed after %d attempts: %s -> %s",
            self._max_retries + 1,
            event,
            url,
        )
        return WebhookDeliveryResult(
            url=url,
            event=event,
            success=False,
            error=last_error,
        )

    def dispatch_to_all(
        self,
        endpoints: list[dict[str, Any]],
        event: str,
        payload: dict[str, Any],
    ) -> list[WebhookDeliveryResult]:
        """Dispatch event to all registered endpoints.

        Args:
            endpoints: List of dicts with "url", "secret", "events" keys.
            event: Event type to dispatch.
            payload: Event payload.

        Returns:
            List of delivery results.
        """
        results: list[WebhookDeliveryResult] = []

        for endpoint in endpoints:
            # Only deliver if endpoint subscribes to this event
            subscribed_events = endpoint.get("events", [])
            if subscribed_events and event not in subscribed_events:
                continue

            result = self.deliver(
                url=endpoint["url"],
                secret=endpoint["secret"],
                event=event,
                payload=payload,
            )
            results.append(result)

        return results
