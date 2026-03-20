"""Tests for GPUInferenceClient and CircuitBreaker (grounded.ai.gpu_client)."""

from __future__ import annotations

# skipcq: PYL-R0201
import time
from unittest.mock import MagicMock, patch

import pytest

from grounded.ai.gpu_client import CircuitBreaker, GPUInferenceClient, GPUServiceUnavailableError


class TestCircuitBreaker:
    """Tests for CircuitBreaker state machine."""

    def test_starts_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == "closed"

    def test_stays_closed_below_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

    def test_opens_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

    def test_check_raises_when_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        with pytest.raises(GPUServiceUnavailableError):
            cb.check()

    def test_check_passes_when_closed(self) -> None:
        cb = CircuitBreaker()
        cb.check()  # Should not raise

    def test_resets_to_closed_on_success(self) -> None:
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        cb.record_success()
        assert cb.state == "closed"
        cb.check()  # Should not raise

    def test_transitions_to_half_open_after_recovery_timeout(self) -> None:
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout_seconds=0.1,
        )
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.15)
        assert cb.state == "half_open"

    def test_failures_outside_window_are_discarded(self) -> None:
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

    def test_assess_image_quality(self) -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {"score": 72.5, "model": "musiq"}
            mock_response.raise_for_status = MagicMock()
            mock_client_cls.return_value.post.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.assess_image_quality(b"fake_image_bytes")

            assert result["score"] == 72.5
            mock_client_cls.return_value.post.assert_called_once()

    def test_classify_document(self) -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "class": "packaging_artwork",
                "confidence": 0.92,
            }
            mock_response.raise_for_status = MagicMock()
            mock_client_cls.return_value.post.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.classify_document(b"fake_image")

            assert result["class"] == "packaging_artwork"

    def test_detect_logos_with_references(self) -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {"logos": [{"label": "brand", "confidence": 0.95}]}
            mock_response.raise_for_status = MagicMock()
            mock_client_cls.return_value.post.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.detect_logos(
                b"fake_image",
                reference_embeddings=[{"id": "1", "embedding": [0.1] * 512}],
            )

            assert len(result["logos"]) == 1

    def test_translate_text(self) -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "translated_text": "Bonjour",
                "source_lang": "en",
                "target_lang": "fr",
            }
            mock_response.raise_for_status = MagicMock()
            mock_client_cls.return_value.post.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            result = client.translate_text("Hello", "en", "fr")

            assert result["translated_text"] == "Bonjour"
            mock_client_cls.return_value.post.assert_called_once()

    def test_health_check_success(self) -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_cls.return_value.get.return_value = mock_response

            client = GPUInferenceClient("http://gpu:8080")
            assert client.health_check() is True

    def test_health_check_failure(self) -> None:
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.get.side_effect = ConnectionError("down")

            client = GPUInferenceClient("http://gpu:8080")
            assert client.health_check() is False

    def test_circuit_breaker_opens_after_consecutive_failures(self) -> None:
        import httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.post.side_effect = httpx.ConnectError("connection refused")

            client = GPUInferenceClient("http://gpu:8080")

            # First 3 failures should raise GPUServiceUnavailableError from the httpx error
            for _ in range(3):
                with pytest.raises(GPUServiceUnavailableError):
                    client.assess_image_quality(b"img")

            # 4th call should fail immediately (circuit open) without making HTTP call
            mock_client_cls.return_value.post.reset_mock()
            with pytest.raises(GPUServiceUnavailableError, match="circuit breaker"):
                client.assess_image_quality(b"img")
            # No HTTP call should have been made because circuit is open
            mock_client_cls.return_value.post.assert_not_called()

    def test_circuit_breaker_resets_after_success(self) -> None:
        import httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.post.side_effect = httpx.ConnectError("connection refused")

            client = GPUInferenceClient("http://gpu:8080")

            # Record 3 failures to open circuit
            for _ in range(3):
                with pytest.raises(GPUServiceUnavailableError):
                    client.assess_image_quality(b"img")

            # Manually reset circuit and succeed
            client._breaker.record_success()

            mock_response = MagicMock()
            mock_response.json.return_value = {"score": 80}
            mock_response.raise_for_status = MagicMock()
            mock_client_cls.return_value.post.side_effect = None
            mock_client_cls.return_value.post.return_value = mock_response

            result = client.assess_image_quality(b"img")
            assert result["score"] == 80

    def test_trailing_slash_stripped_from_base_url(self) -> None:
        with patch("httpx.Client"):
            client = GPUInferenceClient("http://gpu:8080/")
            assert client._base_url == "http://gpu:8080"
