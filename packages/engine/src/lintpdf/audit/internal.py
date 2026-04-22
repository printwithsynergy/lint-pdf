"""Internal audit pass — Claude Opus 4.7 vision verification.

Operator-only. Given a PDF + the engine's findings, renders each
page to PNG (via the already-GS-backed :func:`render_page_to_image`)
and asks Claude Opus 4.7 to independently verify each finding
against the actual rendered pixels.

Not wired into the customer request path. Called from
``scripts/audit_preflight_accuracy.py`` for red-teaming the engine
against a golden-PDF corpus. A customer-equivalent path lives in
:mod:`lintpdf.audit.customer` and runs on Modal.

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
# ~1h cache TTL on the shared system + page images so the harness
# can rerun against the same PDF multiple times without re-billing
# the vision ingest. Anthropic prompt-caching minimum input is
# ~1024 tokens; the system prompt + one page image easily clears that.
_CACHE_TTL_SECONDS = 3600


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


def _render_pages_for_audit(
    pdf_bytes: bytes, page_numbers: list[int]
) -> dict[int, bytes]:
    """Render each required page once, return {page_num: png_bytes}."""
    from lintpdf.ai.rendering import render_page_to_image

    cache: dict[int, bytes] = {}
    for page_num in sorted(set(page_numbers)):
        if page_num <= 0:
            continue
        try:
            cache[page_num] = render_page_to_image(
                pdf_bytes, page_num, dpi=_PAGE_DPI
            )
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
            "ttl": _CACHE_TTL_SECONDS,
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
        """Run one Opus call per batch of ``_MAX_FINDINGS_PER_CALL``."""
        if not findings:
            return []

        views = [_finding_to_view(i, f) for i, f in enumerate(findings)]
        page_numbers = [v.page_num for v in views if v.page_num]
        pages = _render_pages_for_audit(pdf_bytes, page_numbers)

        results: list[AuditResult | None] = [None] * len(findings)
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
                    results[v.index] = AuditResult(
                        status="error",
                        rationale="Auditor call failed; retry the job.",
                        model=self._model,
                        at=datetime.now(UTC),
                    )
                continue
            for v in batch:
                if v.index in verdicts:
                    entry = verdicts[v.index]
                    results[v.index] = AuditResult(
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

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {
                        "type": "ephemeral",
                        "ttl": _CACHE_TTL_SECONDS,
                    },
                }
            ],
            tools=[_TOOL_DEFINITION],
            tool_choice={"type": "tool", "name": "record_verdict"},
            messages=[{"role": "user", "content": content}],
        )
        return _parse_tool_uses(list(response.content))
