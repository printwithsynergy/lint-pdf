"""GPU inference service client with circuit breaker pattern."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GPUServiceUnavailableError(Exception):
    """Raised when GPU inference service is unreachable or circuit is open."""


class GPUServiceRateLimitedError(GPUServiceUnavailableError):
    """Raised when the upstream keeps returning 429 after our retry budget.

    Subclass of :class:`GPUServiceUnavailableError` so existing callers
    that already special-case ``except GPUServiceUnavailableError`` keep
    working — but we can still tell the two apart in the logs and in
    operational dashboards.
    """


class GPUServiceNotConfiguredError(GPUServiceUnavailableError):
    """Raised when ``LINTPDF_GPU_INFERENCE_URL`` is not set.

    Subclass of :class:`GPUServiceUnavailableError` so existing analyzer
    except blocks still catch it, but callers that want to distinguish
    "service intentionally disabled" from "service configured but
    unreachable" can match this subclass first and skip silently
    instead of emitting a reviewer-facing advisory. Same shape as the
    documented ClamAV fail-open behaviour in CLAUDE.md.
    """


# Retry budget for upstream 429s. Exponential backoff with full jitter;
# capped so a request never stalls longer than ~10s of waiting total.
_RATE_LIMIT_MAX_RETRIES = 3
_RATE_LIMIT_BASE_DELAY_S = 0.8
_RATE_LIMIT_MAX_DELAY_S = 5.0

# Per-call timeout for endpoints that may hit a Modal cold-start. The
# OCR / PaddleOCR container in particular can take ~150-180 s on its
# first request after scale-to-zero (multi-GB model weights pulled
# from cache volume). The global default of 30 s was killing those
# requests before the container could respond, leaving
# ``page.detected_text_regions`` permanently empty in production. Once
# Modal's warm pool is populated subsequent calls return in < 1 s.
_GPU_COLD_START_TIMEOUT_S = 240.0


class CircuitBreaker:
    """Simple circuit breaker for GPU service calls.

    States:
    - CLOSED: normal operation, requests pass through
    - OPEN: too many failures, requests fail immediately
    - HALF_OPEN: allow one test request after recovery timeout

    Note on 429s: individual 429 responses that resolve within our
    retry budget are NOT failures. The server is healthy and responsive;
    it's telling us to slow down, and our per-call retry loop already
    respects that with exponential backoff + ``Retry-After``.

    But a 429 that keeps reappearing AFTER the retry budget is exhausted
    does count as one failure. Persistent upstream rate-limiting (what
    you see when Modal throttles every call for minutes at a time) would
    otherwise burn 3 retries x N analyzers x M pages of wall-clock time
    before giving up on each job — driving job completion well past
    timeout. Counting exhausted-budget 429s lets the breaker open after
    ``failure_threshold`` such events, so subsequent calls fast-fail
    (analyzers silently skip AI findings) and the job completes in
    seconds instead of minutes.
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


def _parse_retry_after(value: str | None) -> float | None:
    """Parse an HTTP ``Retry-After`` header into seconds, or ``None``.

    RFC 9110 allows either a delta-seconds integer or an HTTP-date. We
    only honour the integer form here — the date form is rare in modern
    APIs and not worth the parser surface area. Values are clamped to
    our own max delay so a misbehaving upstream can't wedge a worker
    waiting 10 minutes.
    """
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return min(seconds, _RATE_LIMIT_MAX_DELAY_S)


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with full jitter, capped at ``_RATE_LIMIT_MAX_DELAY_S``."""
    cap = _RATE_LIMIT_MAX_DELAY_S
    base = min(cap, _RATE_LIMIT_BASE_DELAY_S * (2**attempt))
    return random.uniform(0, base)


class GPUInferenceClient:
    """Client for the GPU inference service.

    All methods send images to the inference service and return structured results.
    Circuit breaker prevents cascading failures when the service is down.
    Transient HTTP 429 responses are retried with exponential backoff +
    ``Retry-After`` support so normal rate-limit bursts don't escalate
    into analyzer-level outages.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._breaker = CircuitBreaker()
        self._client = httpx.Client(timeout=timeout)

    @property
    def configured(self) -> bool:
        """True when ``LINTPDF_GPU_INFERENCE_URL`` is set to a non-empty value."""
        return bool(self._base_url)

    def _require_configured(self) -> None:
        """Short-circuit any request when the service URL isn't configured.

        Raises :class:`GPUServiceNotConfiguredError` (a subclass of
        :class:`GPUServiceUnavailableError`) so analyzers that already
        handle the generic unavailable error keep working, but ones
        that want to skip silently on the unconfigured path can match
        the subclass first.
        """
        if not self._base_url:
            raise GPUServiceNotConfiguredError(
                "LINTPDF_GPU_INFERENCE_URL is not set; GPU analyzer skipped."
            )

    def _send_with_retry(
        self,
        method: str,
        url: str,
        *,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Shared HTTP send path with 429 retry + circuit breaker.

        ``timeout`` overrides ``self._timeout`` for this single call. Used
        by endpoints whose Modal cold-start budget exceeds the global
        default (e.g. ``/inference/detect-outlines`` first-hit on a
        scaled-to-zero container can take ~150-180 s).

        * Treats 429 as a "retry soon" signal (honours ``Retry-After``
          when the server provides a delta-seconds value) instead of a
          hard failure. The breaker is not notified so normal rate
          limiting doesn't take the whole AI pipeline down.
        * Genuine connection / timeout / 5xx errors are recorded on the
          breaker and re-raised as ``GPUServiceUnavailableError`` as
          before.
        * A 429 that keeps reappearing after our retry budget is
          exhausted surfaces as ``GPUServiceRateLimitedError`` so callers
          can tell it apart from "the upstream is actually down".
        """
        self._breaker.check()
        request_timeout = timeout if timeout is not None else self._timeout

        last_retry_after: str | None = None
        for attempt in range(_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    files=files,
                    data=data,
                    json=json,
                    timeout=request_timeout,
                )
            except (httpx.TimeoutException, httpx.TransportError, ConnectionError) as exc:
                self._breaker.record_failure()
                raise GPUServiceUnavailableError(f"GPU service error: {exc}") from exc

            if response.status_code == 429:
                last_retry_after = response.headers.get("Retry-After")
                if attempt >= _RATE_LIMIT_MAX_RETRIES:
                    # Budget exhausted. Mark the breaker: a single 429
                    # that retries successfully is fine (bursty traffic),
                    # but 429s that outlast our retry loop signal the
                    # upstream is persistently throttling. Without this,
                    # every analyzer for every page burns the full 3x
                    # retry budget during a rate-limit storm -- jobs
                    # appear to hang in ``processing`` until the client
                    # poll loop times out. With this, the breaker opens
                    # after ``failure_threshold`` exhausted-budget
                    # events and subsequent calls fast-fail; analyzers
                    # silently skip AI findings and the job completes.
                    self._breaker.record_failure()
                    logger.warning(
                        "GPU service rate-limited after %d retries "
                        "(Retry-After=%s); giving up on this request",
                        attempt,
                        last_retry_after,
                    )
                    raise GPUServiceRateLimitedError(
                        f"GPU service rate-limited (HTTP 429) after {attempt} retries"
                    )
                delay = (
                    _parse_retry_after(last_retry_after) if last_retry_after is not None else None
                )
                if delay is None:
                    delay = _backoff_delay(attempt)
                logger.info(
                    "GPU service 429 on attempt %d/%d; sleeping %.2fs before retry",
                    attempt + 1,
                    _RATE_LIMIT_MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # 4xx other than 429 or 5xx. These are genuine upstream
                # problems worth counting toward the breaker threshold.
                self._breaker.record_failure()
                raise GPUServiceUnavailableError(f"GPU service error: {exc}") from exc

            self._breaker.record_success()
            payload: dict[str, Any] = response.json()
            return payload

        # The loop only exits via return or raise — this is unreachable.
        raise GPUServiceUnavailableError("GPU service retry loop exited unexpectedly")

    def _post(
        self,
        endpoint: str,
        image_bytes: bytes,
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send image to inference endpoint.

        ``timeout`` is the per-call HTTP timeout in seconds; ``None``
        falls back to ``self._timeout``. Use a longer value for
        endpoints that may hit a Modal cold-start (e.g.
        ``/inference/detect-outlines`` — the OCR container can take
        ~150-180 s on first hit after scale-to-zero).
        """
        self._require_configured()
        url = f"{self._base_url}{endpoint}"
        return self._send_with_retry(
            "POST",
            url,
            files={"image": ("image.png", image_bytes, "image/png")},
            data=kwargs,
            timeout=timeout,
        )

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
        """OCR a rendered page; returns ``{"text_regions": [...]}``.

        The inference service wraps PaddleOCR results in a ``{"result": {...},
        "processing_time_ms": N, "model": "paddleocr"}`` envelope. Engine-side
        callers only care about the inner ``text_regions`` payload, so we
        unwrap here. Callers that mock this client (see
        ``tests/ai/conftest.py``) can return the inner dict directly.

        Uses the cold-start timeout (240 s) because PaddleOCR's container
        can take ~150-180 s on first hit when Modal has scaled to zero.
        """
        raw = self._post(
            "/inference/detect-outlines",
            image_bytes,
            timeout=_GPU_COLD_START_TIMEOUT_S,
        )
        if isinstance(raw, dict) and "result" in raw and isinstance(raw["result"], dict):
            inner = raw["result"]
            # Preserve metadata fields if a caller wants them.
            for meta in ("processing_time_ms", "model"):
                if meta in raw and meta not in inner:
                    inner[meta] = raw[meta]
            return inner
        return raw

    def detect_symbols(self, image_bytes: bytes) -> dict[str, Any]:
        """Detect regulatory/recycling symbols."""
        return self._post("/inference/detect-symbols", image_bytes)

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> dict[str, Any]:
        """Translate text (OPUS-MT)."""
        self._require_configured()
        url = f"{self._base_url}/inference/translate"
        return self._send_with_retry(
            "POST",
            url,
            json={
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
            },
        )

    def health_check(self) -> bool:
        """Check if GPU service is healthy."""
        try:
            response = self._client.get(f"{self._base_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Process-level shared client
# ---------------------------------------------------------------------------
# Every analyzer used to call ``GPUInferenceClient(settings.gpu_inference_url)``
# in its own ``_get_gpu_client()`` factory, which returned a FRESH instance
# (and hence a fresh ``CircuitBreaker``) on every call. That defeats the
# breaker entirely during a Modal rate-limit storm -- each analyzer burns its
# full retry budget, records a failure on its OWN breaker, and then throws
# the breaker away. Analyzer N+1 starts with a clean breaker and repeats.
#
# The fix is a module-level singleton keyed on ``gpu_inference_url``: every
# analyzer calling ``get_gpu_client()`` sees the same ``CircuitBreaker``, so
# ``failure_threshold`` accumulates across calls. Once it trips, subsequent
# analyzers ``check()`` returns immediately, they raise
# ``GPUServiceUnavailableError``, the analyzer silently bails out, and the
# job completes fast instead of burning budget on every call.
#
# Per-URL keying lets tests and alternate deployments (different inference
# endpoints) coexist without stepping on each other's breakers.
_shared_clients: dict[str, GPUInferenceClient] = {}


def get_gpu_client() -> GPUInferenceClient:
    """Return the process-wide ``GPUInferenceClient`` for the configured URL.

    Lazy-initialized on first access, memoized for the lifetime of the
    process. ``GPUInferenceClient`` does its own configured-vs-unconfigured
    check internally, so callers can always treat the returned instance as
    valid and let ``_require_configured`` raise at call time if the
    inference URL isn't set.
    """
    from lintpdf.api.config import get_settings

    url = get_settings().gpu_inference_url or ""
    client = _shared_clients.get(url)
    if client is None:
        client = GPUInferenceClient(url)
        _shared_clients[url] = client
    return client


def _reset_shared_clients_for_tests() -> None:
    """Drop the memoized client map. Tests only."""
    _shared_clients.clear()
