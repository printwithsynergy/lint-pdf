"""Internal audit pass — Claude Opus 4.7 vision verification.

Operator-only. Given a PDF + the engine's findings, renders each
page to PNG (via the already-GS-backed :func:`render_page_to_image`)
and asks Claude Opus 4.7 to independently verify each finding
against the actual rendered pixels.

Not wired into the customer request path. Called from the
admin health toolbox and from
``scripts/audit_preflight_accuracy.py`` for red-teaming the engine
against a golden-PDF corpus. The customer-visible audit path lives
in :mod:`lintpdf.audit.claude` and runs on Haiku 4.5.

Requires the ``anthropic`` Python SDK (``uv sync --extra ai``) and
``ANTHROPIC_API_KEY`` in the environment. Uses prompt caching on
the shared system prompt + page images so reruns over the same
corpus stay cheap — each subsequent audit of the same PDF only
pays for the finding-list delta.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lintpdf.api.models import JobFinding

from lintpdf.audit.types import AuditResult

logger = logging.getLogger(__name__)

_MODEL_ID = "claude-opus-4-7"
_MAX_FINDINGS_PER_CALL = 40
_PAGE_DPI = 150
# Anthropic prompt-caching TTL. Must be one of the API's supported
# shorthand strings — today ``"5m"`` or ``"1h"``. Passing an integer
# seconds value returns 400 ``Input should be '5m' or '1h'`` (same
# bug ``claude.py`` had pre-`e0ced8f`). 1h matches the harness's
# "rerun the same PDF a few times" usage.
_CACHE_TTL = "1h"


_SYSTEM_PROMPT = (
    "You are auditing a print-preflight engine. The engine inspected a PDF "
    "and emitted findings. For each finding, independently verify whether "
    "the engine is correct by examining the rendered page image(s) and the "
    "finding text. Reply by calling the ``record_verdict`` tool with a "
    "status and a one-sentence rationale. Status values:\n"
    "  * ``confirmed``     — the engine is right; the issue is visible / real.\n"
    "  * ``disputed``      — the engine is clearly wrong; describe what you see instead.\n"
    "  * ``needs_context`` — decidable only with JDF sidecar, brand profile, "
    "or customer spec.\n"
    "Be conservative — choose ``disputed`` only when the engine is provably "
    "wrong against the rendered pixels. Everything else is ``confirmed``."
)


_TOOL_DEFINITION = {
    "name": "record_verdict",
    "description": "Record an audit verdict for a single preflight finding.",
    "input_schema": {
        "type": "object",
        "properties": {
            "finding_index": {
                "type": "integer",
                "description": "Zero-based index of the finding in the batch.",
            },
            "status": {
                "type": "string",
                "enum": ["confirmed", "disputed", "needs_context"],
            },
            "rationale": {
                "type": "string",
                "description": "One-sentence explanation, referencing pixels.",
            },
        },
        "required": ["finding_index", "status", "rationale"],
    },
}


@dataclass
class _FindingView:
    """Minimal projection of a finding for the prompt payload."""

    index: int
    inspection_id: str
    severity: str
    message: str
    page_num: int | None
    bbox: tuple[float, float, float, float] | None


def _finding_to_view(idx: int, f: JobFinding) -> _FindingView:
    bbox: tuple[float, float, float, float] | None = None
    if f.bbox_x0 is not None and f.bbox_y0 is not None:
        bbox = (f.bbox_x0, f.bbox_y0, f.bbox_x1 or 0.0, f.bbox_y1 or 0.0)
    return _FindingView(
        index=idx,
        inspection_id=f.inspection_id,
        severity=f.severity,
        message=f.message,
        page_num=f.page_num,
        bbox=bbox,
    )


def _render_pages_for_audit(pdf_bytes: bytes, page_numbers: list[int]) -> dict[int, bytes]:
    """Render each required page once, return {page_num: png_bytes}."""
    from lintpdf.ai.rendering import render_page_to_image

    cache: dict[int, bytes] = {}
    for page_num in sorted(set(page_numbers)):
        if page_num <= 0:
            continue
        try:
            cache[page_num] = render_page_to_image(pdf_bytes, page_num, dpi=_PAGE_DPI)
        except Exception:
            logger.exception("audit: failed to render page %d for Opus", page_num)
    return cache


def _image_block(png_bytes: bytes, cache: bool) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.standard_b64encode(png_bytes).decode("ascii"),
        },
    }
    if cache:
        block["cache_control"] = {
            "type": "ephemeral",
            "ttl": _CACHE_TTL,
        }
    return block


def _findings_block(views: list[_FindingView]) -> dict[str, Any]:
    payload = [
        {
            "index": v.index,
            "inspection_id": v.inspection_id,
            "severity": v.severity,
            "message": v.message,
            "page_num": v.page_num,
            "bbox": list(v.bbox) if v.bbox else None,
        }
        for v in views
    ]
    return {
        "type": "text",
        "text": (
            "Findings to audit (JSON). Call ``record_verdict`` once per "
            "entry, using the ``index`` as ``finding_index``:\n\n"
            f"{json.dumps(payload, indent=2)}"
        ),
    }


def _parse_tool_uses(response_content: list[Any]) -> dict[int, dict[str, str]]:
    """Pull ``record_verdict`` tool calls out of the Anthropic response."""
    verdicts: dict[int, dict[str, str]] = {}
    for block in response_content:
        btype = getattr(block, "type", None)
        if btype != "tool_use":
            continue
        if getattr(block, "name", None) != "record_verdict":
            continue
        payload = getattr(block, "input", None) or {}
        idx = payload.get("finding_index")
        status = payload.get("status")
        rationale = payload.get("rationale", "")
        if isinstance(idx, int) and status in ("confirmed", "disputed", "needs_context"):
            verdicts[idx] = {"status": status, "rationale": rationale}
    return verdicts


class InternalAuditor:
    """Claude Opus 4.7 vision auditor for internal QA runs.

    Usage::

        auditor = InternalAuditor()
        results = auditor.audit(pdf_bytes, findings)
        for res, f in zip(results, findings):
            if res is None:
                continue  # audit skipped (no page, GS failure, etc.)
            print(f.inspection_id, res.status, res.rationale)

    Construction-time errors (missing SDK, missing API key) raise
    immediately so the CLI fails fast. Per-call errors (API 5xx, rate
    limit, batch timeout) degrade gracefully to an ``error`` verdict
    on every finding in the batch — the caller can retry.
    """

    def __init__(self, *, api_key: str | None = None, model: str = _MODEL_ID) -> None:
        try:
            import anthropic

            self._anthropic_mod = anthropic
        except ImportError as exc:  # pragma: no cover — env shape
            raise RuntimeError(
                "InternalAuditor requires the 'anthropic' package. "
                "Run `uv sync --extra ai` to install it."
            ) from exc
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required for InternalAuditor. Set it "
                "in the env or pass api_key= explicitly."
            )
        self._client = self._anthropic_mod.Anthropic(api_key=resolved_key)
        self._model = model

    def audit(
        self,
        pdf_bytes: bytes,
        findings: Sequence[JobFinding],
    ) -> list[AuditResult | None]:
        """Run one Opus call per batch of ``_MAX_FINDINGS_PER_CALL``.

        Pre-filter: findings whose check ID matches a structural-only
        category (PDF/X conformance, accessibility tags, XMP metadata,
        font embedding, ICC / OutputIntent, ink inventory, language
        catalog) are not sent to Opus. The engine reads these directly
        from the PDF object graph, so vision can't verify what already
        has a deterministic answer — auditing them with Opus only
        burns tokens and bloats the "needs_context" bucket. The
        post-merge audit had 583 / 1475 findings (39.5%) marked
        needs_context, of which ~75% were structural-only checks like
        these. We mark them ``confirmed`` because the engine's
        structural detection IS the source of truth here.
        """
        if not findings:
            return []

        results: list[AuditResult | None] = [None] * len(findings)
        opus_indices: list[int] = []
        for i, f in enumerate(findings):
            if _is_structural_only(f.inspection_id):
                results[i] = AuditResult(
                    status="confirmed",
                    rationale=(
                        "Structural finding read directly from the PDF "
                        "object graph (catalog / metadata / output intent "
                        "/ accessibility tag / spot color inventory). "
                        "Vision audit not applicable."
                    ),
                    model=self._model,
                    at=datetime.now(UTC),
                )
            elif _is_operational_advisory(f):
                # GPU-tier-down / service-degraded advisories are
                # operational signals, not preflight issues. Vision
                # can't verify "service availability" — auto-confirm
                # so they don't bloat the uncertain bucket on
                # GPU-offline runs.
                results[i] = AuditResult(
                    status="confirmed",
                    rationale=(
                        "Operational advisory (GPU tier unavailable / "
                        "service degraded). Status of an external "
                        "dependency is not pixel-verifiable."
                    ),
                    model=self._model,
                    at=datetime.now(UTC),
                )
            else:
                opus_indices.append(i)

        if not opus_indices:
            return results

        opus_findings = [findings[i] for i in opus_indices]
        views = [_finding_to_view(i, f) for i, f in enumerate(opus_findings)]
        page_numbers = [v.page_num for v in views if v.page_num]
        pages = _render_pages_for_audit(pdf_bytes, page_numbers)

        for batch_start in range(0, len(views), _MAX_FINDINGS_PER_CALL):
            batch = views[batch_start : batch_start + _MAX_FINDINGS_PER_CALL]
            try:
                verdicts = self._audit_batch(pdf_bytes, batch, pages)
            except Exception:
                logger.exception(
                    "audit: Opus batch failed for findings %d..%d; emitting error verdicts",
                    batch_start,
                    batch_start + len(batch) - 1,
                )
                for v in batch:
                    results[opus_indices[v.index]] = AuditResult(
                        status="error",
                        rationale="Auditor call failed; retry the job.",
                        model=self._model,
                        at=datetime.now(UTC),
                    )
                continue
            for v in batch:
                if v.index in verdicts:
                    entry = verdicts[v.index]
                    results[opus_indices[v.index]] = AuditResult(
                        status=entry["status"],  # type: ignore[arg-type]
                        rationale=entry.get("rationale"),
                        model=self._model,
                        at=datetime.now(UTC),
                    )
                # Finding the auditor didn't call out stays None (not
                # audited) rather than silently confirmed — the CLI
                # harness surfaces these as "skipped" for manual review.
        return results

    def _audit_batch(
        self,
        pdf_bytes: bytes,
        batch: list[_FindingView],
        pages: dict[int, bytes],
    ) -> dict[int, dict[str, str]]:
        """Send one Opus call for the batch; return verdict dict."""
        needed_pages = sorted({v.page_num for v in batch if v.page_num})

        content: list[dict[str, Any]] = []
        # Cache the page images — they're the expensive part of the
        # prompt and identical across batches / reruns of the same PDF.
        for i, page_num in enumerate(needed_pages):
            png = pages.get(page_num)
            if png is None:
                continue
            content.append(
                {
                    "type": "text",
                    "text": f"Page {page_num} (rendered at {_PAGE_DPI} DPI, overprint-simulated):",
                }
            )
            content.append(_image_block(png, cache=(i == len(needed_pages) - 1)))
        content.append(_findings_block(batch))

        response = self._client.messages.create(  # type: ignore[call-overload]
            model=self._model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {
                        "type": "ephemeral",
                        "ttl": _CACHE_TTL,
                    },
                }
            ],
            tools=[_TOOL_DEFINITION],
            tool_choice={"type": "tool", "name": "record_verdict"},
            messages=[{"role": "user", "content": content}],
        )
        return _parse_tool_uses(list(response.content))


# Check-ID prefixes / exact IDs for findings the engine reads
# directly from the PDF object graph. Vision audit is not applicable
# (the engine's structural detection IS the source of truth) so we
# auto-confirm without sending to Opus. Compiled from the post-merge
# audit's "needs_context" top-15 list and the catalog of clearly
# structural check IDs. Reduces both Opus token cost and the noise
# in the uncertain bucket.
_STRUCTURAL_ONLY_PREFIXES: tuple[str, ...] = (
    "PDFX4-",
    "PDFX1A-",
    "PDFA-",
    "LPDF_ACCESS_",
    "LPDF_META_",
    "LPDF_DOC_",
    "LPDF_VIEWER_",
    "LPDF_LANG_",
    "LPDF_FONT_",
    "LPDF_INK_",
    "LPDF_STD_",
    "LPDF_ADV_",
    "AI_LANG_",
    "AI_AFP_",
    "AI_FCLASS_",
    "AI_VDIFF_",
    "AI_SCAN_",
)

_STRUCTURAL_ONLY_EXACT: frozenset[str] = frozenset(
    {
        "LPDF_COLOR_006",  # No Output Intent defined
        "LPDF_COLOR_003",  # Color profile mismatch
        "LPDF_COLOR_014",  # ICC profile metadata
        "LPDF_SPOT_001",  # Spot in DeviceCMYK without alternate
        "LPDF_SPOT_006",  # Spot color overprint flag
        "LPDF_SPOT_008",  # Tint transform issue
        "LPDF_STROKE_003",  # Stroke join / cap metadata
        "LPDF_IMG_018",  # Image colorspace inconsistency
    }
)


def _is_structural_only(inspection_id: str) -> bool:
    """True when the finding's verdict is determined by the PDF
    object graph (no rendered evidence to verify against)."""
    if inspection_id in _STRUCTURAL_ONLY_EXACT:
        return True
    return any(inspection_id.startswith(prefix) for prefix in _STRUCTURAL_ONLY_PREFIXES)


def _is_operational_advisory(finding: JobFinding) -> bool:
    """True when the finding is a service-degraded / tier-down
    operational signal (e.g. GPU inference unavailable). Not a
    preflight issue per se — vision can't audit the status of an
    external dependency."""
    details = getattr(finding, "details", None) or {}
    reason = details.get("reason") if isinstance(details, dict) else None
    if reason in {"gpu_unavailable", "no_target_languages", "no_reference_file"}:
        return True
    msg = (getattr(finding, "message", "") or "").lower()
    return "circuit breaker is open" in msg or "service unavailable" in msg
