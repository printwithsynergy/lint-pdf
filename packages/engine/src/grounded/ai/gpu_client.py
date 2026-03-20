"""GPU inference service client with circuit breaker pattern."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GPUServiceUnavailableError(Exception):
    """Raised when GPU inference service is unreachable or circuit is open."""


class CircuitBreaker:
    """Simple circuit breaker for GPU service calls.

    States:
    - CLOSED: normal operation, requests pass through
    - OPEN: too many failures, requests fail immediately
    - HALF_OPEN: allow one test request after recovery timeout
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        failure_window_seconds: float = 60.0,
        recovery_timeout_seconds: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._failure_window = failure_window_seconds
        self._recovery_timeout = recovery_timeout_seconds
        self._failures: list[float] = []
        self._opened_at: float | None = None
        self._state = "closed"

    @property
    def state(self) -> str:
        if (
            self._state == "open"
            and time.monotonic() - (self._opened_at or 0) > self._recovery_timeout
        ):
            self._state = "half_open"
        return self._state

    def record_success(self) -> None:
        self._failures.clear()
        self._opened_at = None
        self._state = "closed"

    def record_failure(self) -> None:
        now = time.monotonic()
        self._failures = [t for t in self._failures if now - t < self._failure_window]
        self._failures.append(now)

        if len(self._failures) >= self._failure_threshold:
            self._state = "open"
            self._opened_at = now
            logger.warning(
                "GPU circuit breaker OPEN: %d failures in %.0fs",
                len(self._failures),
                self._failure_window,
            )

    def check(self) -> None:
        """Raise if circuit is open."""
        if self.state == "open":
            raise GPUServiceUnavailableError(
                "GPU inference service circuit breaker is open. "
                "Service will be retried automatically."
            )


class GPUInferenceClient:
    """Client for the GPU inference service.

    All methods send images to the inference service and return structured results.
    Circuit breaker prevents cascading failures when the service is down.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._breaker = CircuitBreaker()
        self._client = httpx.Client(timeout=timeout)

    def _post(self, endpoint: str, image_bytes: bytes, **kwargs: Any) -> dict[str, Any]:
        """Send image to inference endpoint."""
        self._breaker.check()

        url = f"{self._base_url}{endpoint}"
        try:
            response = self._client.post(
                url,
                files={"image": ("image.png", image_bytes, "image/png")},
                data=kwargs,
                timeout=self._timeout,
            )
            response.raise_for_status()
            self._breaker.record_success()
            result: dict[str, Any] = response.json()
            return result
        except (httpx.HTTPError, httpx.TimeoutException, ConnectionError) as exc:
            self._breaker.record_failure()
            raise GPUServiceUnavailableError(f"GPU service error: {exc}") from exc

    def assess_image_quality(self, image_bytes: bytes) -> dict[str, Any]:
        """Assess perceptual image quality (MUSIQ/TOPIQ)."""
        return self._post("/inference/image-quality", image_bytes)

    def classify_document(self, image_bytes: bytes) -> dict[str, Any]:
        """Classify document type (DiT)."""
        return self._post("/inference/classify", image_bytes)

    def detect_logos(
        self,
        image_bytes: bytes,
        reference_embeddings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Detect and verify logos (YOLOv8 + CLIP)."""
        extra: dict[str, Any] = {}
        if reference_embeddings:
            import json

            extra["reference_embeddings"] = json.dumps(reference_embeddings)
        return self._post("/inference/detect-logo", image_bytes, **extra)

    def detect_nsfw(self, image_bytes: bytes) -> dict[str, Any]:
        """Detect NSFW content (NudeNet)."""
        return self._post("/inference/detect-nsfw", image_bytes)

    def detect_objects(
        self, image_bytes: bytes, prompt: str = "text. logo. barcode."
    ) -> dict[str, Any]:
        """Detect objects by text prompt (Grounding DINO)."""
        return self._post("/inference/detect-objects", image_bytes, prompt=prompt)

    def embed_image(self, image_bytes: bytes) -> dict[str, Any]:
        """Generate image embedding (DINOv2)."""
        return self._post("/inference/embed-image", image_bytes)

    def detect_outlines(self, image_bytes: bytes) -> dict[str, Any]:
        """OCR on path regions to detect outlined text."""
        return self._post("/inference/detect-outlines", image_bytes)

    def detect_symbols(self, image_bytes: bytes) -> dict[str, Any]:
        """Detect regulatory/recycling symbols."""
        return self._post("/inference/detect-symbols", image_bytes)

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> dict[str, Any]:
        """Translate text (OPUS-MT)."""
        self._breaker.check()

        url = f"{self._base_url}/inference/translate"
        try:
            response = self._client.post(
                url,
                json={
                    "text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            self._breaker.record_success()
            result: dict[str, Any] = response.json()
            return result
        except (httpx.HTTPError, httpx.TimeoutException, ConnectionError) as exc:
            self._breaker.record_failure()
            raise GPUServiceUnavailableError(f"GPU service error: {exc}") from exc

    def health_check(self) -> bool:
        """Check if GPU service is healthy."""
        try:
            response = self._client.get(f"{self._base_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
