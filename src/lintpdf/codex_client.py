"""HTTP-backed CodexClient — talks to the unified-extraction endpoints.

Mirrors the Phase 0 contract from the cross-repo handoff:

* ``GET /documents/{id}/text-regions?page_index=...&dpi=...``
* ``POST /documents/{id}/conformance/{profile}``
* ``X-Codex-Stage-Durations-Ms`` response header carrying per-stage
  timings codex measured.

The codex implementation may not have shipped yet — this client is
written against the locked contract so the lint-pdf orchestrator can
flag-flip when codex publishes. Until then, factory falls back to the
no-op stub so calls never reach the wire.

The class deliberately catches ``ImportError`` on ``codex_pdf.client``
and surfaces network failures as ``CodexUnavailableError`` so the
orchestrator's ``if flag and is_enabled()`` guard keeps the fallback
path explicit.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lintpdf.plugin.services import (
    ClauseFailure,
    CodexClient,
    ConformanceVerdict,
    noop_codex_client,
)

if TYPE_CHECKING:
    from lintpdf.semantic.model import DetectedTextRegion

logger = logging.getLogger(__name__)

# Codex stage names that may appear in ``X-Codex-Stage-Durations-Ms``.
# Locked so the orchestrator can prefix-namespace them under
# ``stage_durations_ms["codex"]`` without surprises. Codex emitting a
# new stage name is fine — we keep unknown keys as-is.
_KNOWN_CODEX_STAGES = ("extract", "render", "text_regions", "conformance")


class CodexUnavailableError(RuntimeError):
    """Raised when the codex HTTP surface is unreachable or misconfigured.

    Callers MUST gate calls on ``CodexClient.is_enabled()`` — that
    accessor returns ``False`` when the underlying SDK isn't importable
    or no endpoint is configured, short-circuiting before any method
    that would raise this.
    """


@dataclass
class _CodexHttpClient:
    """Concrete CodexClient wrapping ``codex_pdf.client.HttpClient``.

    The wrapped HttpClient already handles route mode / plant /
    affinity-key env vars, retry, and in-process fallback to
    ``codex_pdf.extract`` when no HTTP base is configured.

    Stage-duration mailbox: each call captures the response header
    (or response-envelope ``stage_durations_ms`` field, whichever
    codex emits) into ``_last_durations``. The orchestrator drains
    it via ``last_stage_durations_ms()`` after each request.
    """

    _last_durations: dict[str, int]

    def __init__(self) -> None:
        self._last_durations = {}

    # ------------------------------------------------------------------
    # CodexClient Protocol
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        """Return ``True`` when the codex SDK is importable AND the
        unified-extraction endpoints are exposed by the running codex.

        Conservative: returns ``False`` on any ImportError so callers
        fall back to the local text-region / verapdf modules without
        ever hitting the network.
        """
        try:
            from codex_pdf.client import HttpClient  # noqa: F401
        except ImportError:
            return False
        return True

    def get_text_regions(
        self,
        *,
        pdf_hash: str,
        page_index: int,
        dpi: int,
    ) -> list[DetectedTextRegion]:
        """Fetch one page's OCR text regions from codex.

        Raises ``CodexUnavailableError`` if the endpoint is missing or
        the request fails — callers MUST gate with ``is_enabled()``.
        """
        payload = self._get_json(
            path=f"/documents/{pdf_hash}/text-regions",
            params={"page_index": page_index, "dpi": dpi},
        )
        regions_raw = payload.get("regions") if isinstance(payload, dict) else []
        return [_to_detected_text_region(r) for r in regions_raw if isinstance(r, dict)]

    def get_conformance_verdict(
        self,
        *,
        document_id: str,
        profile: str,
    ) -> ConformanceVerdict:
        """Trigger / fetch the codex conformance verdict for one profile.

        Per the handoff: codex caches by ``(pdf_hash, profile)``; lint-pdf
        forwards ``document_id`` (the codex doc id, often the pdf_hash).
        """
        payload = self._post_json(
            path=f"/documents/{document_id}/conformance/{profile}",
            body={},
        )
        if not isinstance(payload, dict):
            raise CodexUnavailableError(f"codex conformance/{profile} returned non-object payload")
        clauses_raw = payload.get("clauses") or []
        clauses = [_to_clause_failure(c) for c in clauses_raw if isinstance(c, dict)]
        return ConformanceVerdict(
            passed=bool(payload.get("passed", not clauses)),
            clauses=clauses,
        )

    def last_stage_durations_ms(self) -> dict[str, int]:
        """Return the codex per-stage durations captured on the most
        recent call. Empty dict when codex did not emit telemetry."""
        return dict(self._last_durations)

    # ------------------------------------------------------------------
    # internals — keep request plumbing in one place
    # ------------------------------------------------------------------

    def _http_client(self) -> Any:
        """Construct the codex HttpClient on each call.

        Cheap and stateless (env-driven config); avoids a long-lived
        connection pool that would outlive a single preflight run.
        Mirrors the pattern at ``codex_adapter.py:202-209``.
        """
        from codex_pdf.client import HttpClient

        return HttpClient(
            route_mode=os.getenv("CODEX_ROUTE_MODE"),
            plant=os.getenv("CODEX_PLANT"),
            affinity_key=os.getenv("CODEX_AFFINITY_KEY"),
        )

    def _get_json(self, *, path: str, params: dict[str, Any]) -> Any:
        try:
            client = self._http_client()
        except ImportError as exc:
            raise CodexUnavailableError("codex_pdf.client not importable") from exc

        # The wrapped HttpClient exposes a generic ``.request`` /
        # ``.get`` once codex publishes the unified endpoints. Until
        # then, surface a clear error so callers know to keep the
        # feature flag off.
        get = getattr(client, "get_json", None) or getattr(client, "get", None)
        if get is None:
            raise CodexUnavailableError(
                f"codex_pdf.client.HttpClient does not expose GET {path} — "
                "is your codex-pdf version too old?"
            )
        try:
            response = get(path, params=params)
        except Exception as exc:  # pragma: no cover — network failure
            raise CodexUnavailableError(f"codex GET {path} failed: {exc}") from exc
        self._capture_stage_durations(response)
        return _decode_response(response)

    def _post_json(self, *, path: str, body: dict[str, Any]) -> Any:
        try:
            client = self._http_client()
        except ImportError as exc:
            raise CodexUnavailableError("codex_pdf.client not importable") from exc

        post = getattr(client, "post_json", None) or getattr(client, "post", None)
        if post is None:
            raise CodexUnavailableError(
                f"codex_pdf.client.HttpClient does not expose POST {path} — "
                "is your codex-pdf version too old?"
            )
        try:
            response = post(path, json=body)
        except Exception as exc:  # pragma: no cover — network failure
            raise CodexUnavailableError(f"codex POST {path} failed: {exc}") from exc
        self._capture_stage_durations(response)
        return _decode_response(response)

    def _capture_stage_durations(self, response: Any) -> None:
        """Drain ``X-Codex-Stage-Durations-Ms`` (or response-envelope
        ``stage_durations_ms``) into ``_last_durations``. Best-effort —
        a missing or malformed header just leaves the mailbox empty
        for this call.
        """
        self._last_durations = {}
        headers = getattr(response, "headers", None)
        if headers is not None:
            raw = headers.get("X-Codex-Stage-Durations-Ms") or headers.get(
                "x-codex-stage-durations-ms"
            )
            if raw:
                try:
                    parsed = json.loads(raw)
                except (TypeError, ValueError):
                    parsed = None
                if isinstance(parsed, dict):
                    self._last_durations = {
                        str(k): int(v) for k, v in parsed.items() if isinstance(v, (int, float))
                    }
                    return

        # Envelope fallback: ``response.json()`` may carry the durations
        # inline when the wire transport is the in-process Codex fallback.
        body = _decode_response(response) if response is not None else None
        if isinstance(body, dict):
            inline = body.get("stage_durations_ms")
            if isinstance(inline, dict):
                self._last_durations = {
                    str(k): int(v) for k, v in inline.items() if isinstance(v, (int, float))
                }


def _decode_response(response: Any) -> Any:
    """Turn the HttpClient response into a Python value.

    Accepts both:
    * a ``requests``/``httpx``-like response with ``.json()``;
    * a plain dict / list already decoded by an in-process fallback.
    """
    if response is None:
        return None
    if isinstance(response, (dict, list)):
        return response
    if hasattr(response, "json") and callable(response.json):
        try:
            return response.json()
        except Exception:  # pragma: no cover — malformed payload
            return None
    return None


def _to_detected_text_region(raw: dict[str, Any]) -> DetectedTextRegion:
    """Convert codex's wire shape to lint-pdf's ``DetectedTextRegion``.

    Codex emits PDF-point coordinates per the contract, so no
    pixel→point conversion happens here (that's the local fallback's
    job, see ``ai/text_region_pass.py:_scale_bbox``).
    """
    from lintpdf.semantic.model import DetectedTextRegion, PdfBox

    bbox_raw = raw.get("bbox") or {}
    bbox = PdfBox(
        float(bbox_raw.get("x0", 0.0)),
        float(bbox_raw.get("y0", 0.0)),
        float(bbox_raw.get("x1", 0.0)),
        float(bbox_raw.get("y1", 0.0)),
    )

    polygon_raw = raw.get("polygon")
    polygon: tuple[tuple[float, float], ...] | None = None
    if isinstance(polygon_raw, list) and len(polygon_raw) >= 3:
        pts: list[tuple[float, float]] = []
        for p in polygon_raw:
            if not isinstance(p, (list, tuple)) or len(p) < 2:
                continue
            pts.append((float(p[0]), float(p[1])))
        if len(pts) >= 3:
            polygon = tuple(pts)

    return DetectedTextRegion(
        bbox=bbox,
        text=(raw.get("text") or None),
        confidence=float(raw.get("confidence") or 0.0),
        polygon=polygon,
        source=str(raw.get("source") or "codex"),
    )


def _to_clause_failure(raw: dict[str, Any]) -> ClauseFailure:
    return ClauseFailure(
        clause=str(raw.get("clause", "")),
        test_number=str(raw.get("test_number", "")),
        description=str(raw.get("description", "")),
        failed_check_count=int(raw.get("failed_check_count", 0) or 0),
    )


def get_codex_client() -> CodexClient:
    """Return the active CodexClient for this process.

    Returns the HTTP-backed client when codex's SDK is importable,
    otherwise the no-op stub. Importable-but-endpoint-missing is
    handled at call time (raises ``CodexUnavailableError``); callers
    gate on ``is_enabled()`` to decide whether to attempt the call
    in the first place.

    Universal — every lint-pdf host calls this. There is no separate
    SaaS-vs-self-hosted path: codex is the data boundary and the
    fallback to ``_NoOpCodexClient`` only triggers when codex itself
    is unavailable.
    """
    try:
        from codex_pdf.client import HttpClient  # noqa: F401
    except ImportError:
        return noop_codex_client()
    return _CodexHttpClient()


__all__ = [
    "_KNOWN_CODEX_STAGES",
    "CodexUnavailableError",
    "_CodexHttpClient",
    "get_codex_client",
]
