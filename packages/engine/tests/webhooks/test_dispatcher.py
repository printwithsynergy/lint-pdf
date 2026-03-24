"""Tests for webhook dispatcher."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from lintpdf.webhooks.dispatcher import WebhookDeliveryResult, WebhookDispatcher

TEST_WEBHOOK_SECRET = "test-webhook-secret"
TEST_WEBHOOK_SECRET_ALT = "test-webhook-secret-alt"


class TestWebhookDeliveryResult:
    """Tests for WebhookDeliveryResult."""

    @staticmethod
    def test_default_values() -> None:
        result = WebhookDeliveryResult(url="https://example.com", event="test")
        assert result.url == "https://example.com"
        assert result.event == "test"
        assert result.status_code == 0
        assert result.success is False
        assert result.error == ""

    @staticmethod
    def test_success_result() -> None:
        result = WebhookDeliveryResult(
            url="https://example.com",
            event="job.completed",
            status_code=200,
            success=True,
        )
        assert result.success is True
        assert result.status_code == 200

    @staticmethod
    def test_error_result() -> None:
        result = WebhookDeliveryResult(
            url="https://example.com",
            event="job.failed",
            success=False,
            error="Connection refused",
        )
        assert result.success is False
        assert result.error == "Connection refused"

    @staticmethod
    def test_slots() -> None:
        result = WebhookDeliveryResult(url="https://example.com", event="test")
        assert hasattr(result, "__slots__")
        with pytest.raises(AttributeError):
            result.extra = "nope"  # type: ignore[attr-defined]


class TestWebhookDispatcherSign:
    """Tests for HMAC-SHA256 signing."""

    @staticmethod
    def test_sign_payload_format() -> None:
        dispatcher = WebhookDispatcher()
        sig = dispatcher.sign_payload(TEST_WEBHOOK_SECRET, '{"key": "value"}')
        assert sig.startswith("sha256=")

    @staticmethod
    def test_sign_payload_deterministic() -> None:
        dispatcher = WebhookDispatcher()
        body = '{"test": true}'
        sig1 = dispatcher.sign_payload(TEST_WEBHOOK_SECRET, body)
        sig2 = dispatcher.sign_payload(TEST_WEBHOOK_SECRET, body)
        assert sig1 == sig2

    @staticmethod
    def test_sign_payload_different_secrets() -> None:
        dispatcher = WebhookDispatcher()
        body = '{"test": true}'
        sig1 = dispatcher.sign_payload(TEST_WEBHOOK_SECRET, body)
        sig2 = dispatcher.sign_payload(TEST_WEBHOOK_SECRET_ALT, body)
        assert sig1 != sig2

    @staticmethod
    def test_sign_payload_matches_manual_hmac() -> None:
        dispatcher = WebhookDispatcher()
        secret = TEST_WEBHOOK_SECRET
        body = '{"event": "test"}'
        expected = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        sig = dispatcher.sign_payload(secret, body)
        assert sig == f"sha256={expected}"


class TestWebhookDispatcherDeliver:
    """Tests for deliver method."""

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_successful_delivery(mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=0)
        result = dispatcher.deliver(
            url="https://example.com/webhook",
            secret=TEST_WEBHOOK_SECRET,
            event="job.completed",
            payload={"job_id": "123"},
        )

        assert result.success is True
        assert result.status_code == 200
        assert result.url == "https://example.com/webhook"
        assert result.event == "job.completed"
        mock_post.assert_called_once()

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_delivery_sends_correct_headers(mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=0)
        dispatcher.deliver(
            url="https://example.com/webhook",
            secret=TEST_WEBHOOK_SECRET,
            event="preflight.complete",
            payload={"data": "test"},
        )

        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["Content-Type"] == "application/json"
        assert headers["X-LintPDF-Event"] == "preflight.complete"
        assert headers["X-LintPDF-Signature"].startswith("sha256=")
        assert headers["User-Agent"] == "LintPDF-Webhook/0.1.0"

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_delivery_sends_sorted_json(mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=0)
        payload = {"z_key": "last", "a_key": "first"}
        dispatcher.deliver(
            url="https://example.com/webhook",
            secret=TEST_WEBHOOK_SECRET,
            event="test",
            payload=payload,
        )

        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content")
        parsed = json.loads(body)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_delivery_failure_http_error(mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=0)
        result = dispatcher.deliver(
            url="https://example.com/webhook",
            secret=TEST_WEBHOOK_SECRET,
            event="test",
            payload={},
        )

        assert result.success is False
        assert "HTTP 500" in result.error

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_delivery_failure_exception(mock_post: MagicMock) -> None:
        mock_post.side_effect = ConnectionError("Connection refused")

        dispatcher = WebhookDispatcher(max_retries=0)
        result = dispatcher.deliver(
            url="https://example.com/webhook",
            secret=TEST_WEBHOOK_SECRET,
            event="test",
            payload={},
        )

        assert result.success is False
        assert "Connection refused" in result.error

    @staticmethod
    @patch("time.sleep")
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_retry_with_backoff(mock_post: MagicMock, mock_sleep: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=2, base_delay=1.0)
        result = dispatcher.deliver(
            url="https://example.com/webhook",
            secret=TEST_WEBHOOK_SECRET,
            event="test",
            payload={},
        )

        assert result.success is False
        # 1 initial + 2 retries = 3 total calls
        assert mock_post.call_count == 3
        # 2 sleeps (not after last attempt)
        assert mock_sleep.call_count == 2
        # Exponential backoff: 1.0, 2.0
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @patch("time.sleep")
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_retry_succeeds_on_second_attempt(
        self, mock_post: MagicMock, mock_sleep: MagicMock
    ) -> None:
        fail_response = MagicMock()
        fail_response.status_code = 503
        ok_response = MagicMock()
        ok_response.status_code = 200
        mock_post.side_effect = [fail_response, ok_response]

        dispatcher = WebhookDispatcher(max_retries=2, base_delay=0.1)
        result = dispatcher.deliver(
            url="https://example.com/webhook",
            secret=TEST_WEBHOOK_SECRET,
            event="test",
            payload={},
        )

        assert result.success is True
        assert result.status_code == 200
        assert mock_post.call_count == 2

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_accepts_2xx_and_3xx(mock_post: MagicMock) -> None:
        for status in [200, 201, 204, 301, 302]:
            mock_response = MagicMock()
            mock_response.status_code = status
            mock_post.return_value = mock_response

            dispatcher = WebhookDispatcher(max_retries=0)
            result = dispatcher.deliver(
                url="https://example.com/webhook",
                secret=TEST_WEBHOOK_SECRET,
                event="test",
                payload={},
            )
            assert result.success is True, f"Expected success for status {status}"


class TestWebhookDispatcherDispatchToAll:
    """Tests for dispatch_to_all method."""

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_dispatch_to_multiple_endpoints(mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=0)
        endpoints = [
            {"url": "https://a.com/hook", "secret": TEST_WEBHOOK_SECRET, "events": []},
            {"url": "https://b.com/hook", "secret": TEST_WEBHOOK_SECRET_ALT, "events": []},
        ]

        results = dispatcher.dispatch_to_all(endpoints, "test.event", {"data": 1})

        assert len(results) == 2
        assert all(r.success for r in results)

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_filters_by_subscribed_events(mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=0)
        endpoints = [
            {
                "url": "https://a.com/hook",
                "secret": TEST_WEBHOOK_SECRET,
                "events": ["job.completed"],
            },
            {
                "url": "https://b.com/hook",
                "secret": TEST_WEBHOOK_SECRET_ALT,
                "events": ["job.failed"],
            },
        ]

        results = dispatcher.dispatch_to_all(endpoints, "job.completed", {"data": 1})

        assert len(results) == 1
        assert results[0].url == "https://a.com/hook"

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_empty_events_subscribes_to_all(mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = WebhookDispatcher(max_retries=0)
        endpoints = [
            {"url": "https://a.com/hook", "secret": TEST_WEBHOOK_SECRET, "events": []},
        ]

        results = dispatcher.dispatch_to_all(endpoints, "any.event", {"data": 1})

        assert len(results) == 1

    @staticmethod
    def test_empty_endpoints() -> None:
        dispatcher = WebhookDispatcher()
        results = dispatcher.dispatch_to_all([], "test", {})
        assert results == []

    @staticmethod
    @patch("lintpdf.webhooks.dispatcher.httpx.post")
    def test_partial_failure(mock_post: MagicMock) -> None:
        ok_response = MagicMock()
        ok_response.status_code = 200
        mock_post.side_effect = [ok_response, ConnectionError("fail")]

        dispatcher = WebhookDispatcher(max_retries=0)
        endpoints = [
            {"url": "https://a.com/hook", "secret": TEST_WEBHOOK_SECRET, "events": []},
            {"url": "https://b.com/hook", "secret": TEST_WEBHOOK_SECRET_ALT, "events": []},
        ]

        results = dispatcher.dispatch_to_all(endpoints, "test", {})

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
