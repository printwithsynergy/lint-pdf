"""Tests for GPUInferenceClient and CircuitBreaker (lintpdf.ai.gpu_client)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from lintpdf.ai.gpu_client import CircuitBreaker, GPUInferenceClient, GPUServiceUnavailableError


class TestCircuitBreaker:
    """Tests for CircuitBreaker state machine."""

    @staticmethod
    def test_starts_closed() -> None:
        cb = CircuitBreaker()
        assert cb.state == "closed"

    @staticmethod
    def test_stays_closed_below_threshold() -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

    @staticmethod
    def test_opens_after_threshold_failures() -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

    @staticmethod
    def test_check_raises_when_open() -> None:
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        with pytest.raises(GPUServiceUnavailableError):
            cb.check()

    @staticmethod
    def test_check_passes_when_closed() -> None:
        cb = CircuitBreaker()
        cb.check()  # Should not raise

    @staticmethod
    def test_resets_to_closed_on_success() -> None:
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        cb.record_success()
        assert cb.state == "closed"
        cb.check()  # Should not raise

    @staticmethod
    def test_transitions_to_half_open_after_recovery_timeout() -> None:
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout_seconds=0.1,
        )
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.15)
        assert cb.state == "half_open"

    @staticmethod
    def test_failures_outside_window_are_discarded() -> None:
        cb = CircuitBreaker(
            failure_threshold=2,
            failure_window_seconds=0.1,
        )
        cb.record_failure()
        time.sleep(0.15)
        cb.record_failure()
        # The first failure should have been discarded (outside window)
        assert cb.state == "closed"


class TestGPUInferenceClient:
    """Tests for GPUInferenceClient with mocked httpx."""

    @staticmethod
    def _ok_response(body: dict) -> MagicMock:
        """Build a 200-response mock shaped for the new ``.request()`` path."""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = body
        r.raise_for_status = MagicMock()
        return r

    @staticmethod
    def test_assess_image_quality() -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = TestGPUInferenceClient._ok_response(
                {"score": 72.5, "model": "musiq"}
            )
            mock_client_cls.return_value.request.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.assess_image_quality(b"fake_image_bytes")

            assert result["score"] == 72.5
            mock_client_cls.return_value.request.assert_called_once()

    @staticmethod
    def test_classify_document() -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = TestGPUInferenceClient._ok_response(
                {"class": "packaging_artwork", "confidence": 0.92}
            )
            mock_client_cls.return_value.request.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.classify_document(b"fake_image")

            assert result["class"] == "packaging_artwork"

    @staticmethod
    def test_detect_logos_with_references() -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = TestGPUInferenceClient._ok_response(
                {"logos": [{"label": "brand", "confidence": 0.95}]}
            )
            mock_client_cls.return_value.request.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.detect_logos(
                b"fake_image",
                reference_embeddings=[{"id": "1", "embedding": [0.1] * 512}],
            )

            assert len(result["logos"]) == 1

    @staticmethod
    def test_translate_text() -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = TestGPUInferenceClient._ok_response(
                {
                    "translated_text": "Bonjour",
                    "source_lang": "en",
                    "target_lang": "fr",
                }
            )
            mock_client_cls.return_value.request.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.translate_text("Hello", "en", "fr")

            assert result["translated_text"] == "Bonjour"
            mock_client_cls.return_value.request.assert_called_once()

    @staticmethod
    def test_health_check_success() -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_cls.return_value.get.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            assert client.health_check() is True

    @staticmethod
    def test_health_check_failure() -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.get.side_effect = ConnectionError("down")

            client = GPUInferenceClient("http://gpu:8080")
            assert client.health_check() is False

    @staticmethod
    def test_circuit_breaker_opens_after_consecutive_failures() -> None:
        import httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.request.side_effect = httpx.ConnectError(
                "connection refused"
            )

            client = GPUInferenceClient("http://gpu:8080")

            # First 3 failures should raise GPUServiceUnavailableError from the httpx error
            for _ in range(3):
                with pytest.raises(GPUServiceUnavailableError):
                    client.assess_image_quality(b"img")

            # 4th call should fail immediately (circuit open) without making HTTP call
            mock_client_cls.return_value.request.reset_mock()
            with pytest.raises(GPUServiceUnavailableError, match="circuit breaker"):
                client.assess_image_quality(b"img")
            # No HTTP call should have been made because circuit is open
            mock_client_cls.return_value.request.assert_not_called()

    @staticmethod
    def test_circuit_breaker_resets_after_success() -> None:
        import httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.request.side_effect = httpx.ConnectError(
                "connection refused"
            )

            client = GPUInferenceClient("http://gpu:8080")

            # Record 3 failures to open circuit
            for _ in range(3):
                with pytest.raises(GPUServiceUnavailableError):
                    client.assess_image_quality(b"img")

            # Manually reset circuit and succeed
            client._breaker.record_success()

            mock_response = TestGPUInferenceClient._ok_response({"score": 80})
            mock_client_cls.return_value.request.side_effect = None
            mock_client_cls.return_value.request.return_value = mock_response

            result = client.assess_image_quality(b"img")
            assert result["score"] == 80

    @staticmethod
    def test_trailing_slash_stripped_from_base_url() -> None:
        with patch("httpx.Client"):
            client = GPUInferenceClient("http://gpu:8080/")
            assert client._base_url == "http://gpu:8080"


class TestSharedClientSingleton:
    """Process-wide ``get_gpu_client()`` must return the same instance.

    This is load-bearing for circuit-breaker semantics: if every
    analyzer built its own ``GPUInferenceClient``, the breaker would
    never accumulate failures across calls during a rate-limit storm.
    """

    @staticmethod
    def test_same_url_returns_same_instance() -> None:
        from lintpdf.ai.gpu_client import (
            _reset_shared_clients_for_tests,
            get_gpu_client,
        )

        _reset_shared_clients_for_tests()
        with patch("lintpdf.api.config.get_settings") as mock_settings:
            mock_settings.return_value.gpu_inference_url = "http://gpu:8080"
            a = get_gpu_client()
            b = get_gpu_client()
            assert a is b

    @staticmethod
    def test_different_urls_return_different_instances() -> None:
        """Test harness / multi-endpoint deployments shouldn't share breakers."""
        from lintpdf.ai.gpu_client import (
            _reset_shared_clients_for_tests,
            get_gpu_client,
        )

        _reset_shared_clients_for_tests()
        with patch("lintpdf.api.config.get_settings") as mock_settings:
            mock_settings.return_value.gpu_inference_url = "http://gpu-a:8080"
            a = get_gpu_client()
            mock_settings.return_value.gpu_inference_url = "http://gpu-b:8080"
            b = get_gpu_client()
            assert a is not b

    @staticmethod
    def test_breaker_failures_persist_across_get_calls() -> None:
        """After record_failure, the next get_gpu_client() sees the same breaker."""
        from lintpdf.ai.gpu_client import (
            _reset_shared_clients_for_tests,
            get_gpu_client,
        )

        _reset_shared_clients_for_tests()
        with patch("lintpdf.api.config.get_settings") as mock_settings:
            mock_settings.return_value.gpu_inference_url = "http://gpu:8080"
            a = get_gpu_client()
            a._breaker.record_failure()
            a._breaker.record_failure()
            b = get_gpu_client()
            # Same breaker: 2 failures carried over.
            assert len(b._breaker._failures) == 2


class TestRateLimit429Handling:
    """Verify the retry-budget-exhausted 429 path records a breaker failure.

    Contract locked in here:

    1. A single 429 that resolves inside the retry budget DOES NOT hit
       the breaker. Normal rate-limit bursts shouldn't take the whole
       AI pipeline offline.
    2. A 429 that keeps coming back after the retry budget is exhausted
       counts as ONE breaker failure.
    3. After ``failure_threshold`` exhausted-budget events, the breaker
       opens and subsequent calls fast-fail (no retry budget spent).

    This contract is what keeps jobs from hanging in ``processing`` for
    10+ minutes during Modal throttling storms: each analyzer no longer
    burns its full 3x retry budget before giving up.
    """

    @staticmethod
    def _mock_response(status: int, body: dict | None = None) -> MagicMock:
        r = MagicMock()
        r.status_code = status
        r.headers = {}
        r.json.return_value = body or {}
        r.raise_for_status = MagicMock()
        return r

    @staticmethod
    def test_single_429_that_resolves_does_not_record_failure() -> None:
        from lintpdf.ai.gpu_client import GPUInferenceClient

        ok = TestRateLimit429Handling._mock_response(200, {"score": 90})
        throttled = TestRateLimit429Handling._mock_response(429)

        with patch("httpx.Client") as mock_client_cls:
            # 429 once, then 200. Should succeed without touching the breaker.
            mock_client_cls.return_value.request.side_effect = [throttled, ok]
            client = GPUInferenceClient("http://gpu:8080")
            result = client.assess_image_quality(b"img")
            assert result["score"] == 90
            assert len(client._breaker._failures) == 0

    @staticmethod
    def test_budget_exhausted_429_records_one_failure() -> None:
        from lintpdf.ai.gpu_client import (
            GPUInferenceClient,
            GPUServiceRateLimitedError,
        )

        throttled = TestRateLimit429Handling._mock_response(429)

        with patch("httpx.Client") as mock_client_cls:
            # 429 on every attempt. Budget (3 retries) exhausted.
            mock_client_cls.return_value.request.return_value = throttled
            client = GPUInferenceClient("http://gpu:8080")
            with pytest.raises(GPUServiceRateLimitedError):
                client.assess_image_quality(b"img")
            assert len(client._breaker._failures) == 1

    @staticmethod
    def test_three_budget_exhausted_429s_open_the_breaker() -> None:
        from lintpdf.ai.gpu_client import (
            GPUInferenceClient,
            GPUServiceRateLimitedError,
            GPUServiceUnavailableError,
        )

        throttled = TestRateLimit429Handling._mock_response(429)

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.request.return_value = throttled
            client = GPUInferenceClient("http://gpu:8080")
            # Breaker threshold is 3 failures in 60s.
            for _ in range(3):
                with pytest.raises(GPUServiceRateLimitedError):
                    client.assess_image_quality(b"img")
            # Next call: breaker open, fast-fails WITHOUT burning retries.
            call_count_before = mock_client_cls.return_value.request.call_count
            with pytest.raises(GPUServiceUnavailableError, match="circuit breaker"):
                client.assess_image_quality(b"img")
            assert mock_client_cls.return_value.request.call_count == call_count_before
