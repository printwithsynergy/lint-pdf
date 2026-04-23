"""Customer-facing audit pass — Claude Haiku 4.5 via the Anthropic SDK.

The only customer auditor. After the wholesale Claude pivot the
Modal Qwen2-VL fallback is gone — API failures trigger the Celery
retry task :func:`lintpdf.queue.audit_tasks.audit_findings_async`
instead (WS-B). Verdicts land in ``JobFinding.audit_*``.

Why Haiku:

* Latency — ~1-2 s per batch. Audit runs async off the preflight
  critical path so this barely matters, but it's still the fastest
  vision pass available.
* Accuracy — Claude 4.5 scores well on structured-output +
  reasoning-heavy vision tasks. Disputed verdicts carry
  actionable rationales.
* Cost — prompt caching on the page image + Haiku's $0.80/$4 per
  million tokens puts per-job cost at ~$0.01.
* Ops — one SDK, one API key, zero GPU image builds.

Env:
    ANTHROPIC_API_KEY      required
    LINTPDF_AUDIT_MODEL    optional, defaults to ``claude-haiku-4-5``
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lintpdf.api.models import JobFinding

from lintpdf.audit.types import AuditResult

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = os.environ.get("LINTPDF_AUDIT_MODEL", "claude-haiku-4-5")
_MAX_FINDINGS_PER_CALL = 25
_PAGE_DPI = 150
# Anthropic prompt-caching TTL. Must be one of the API's supported
# shorthand strings — today ``"5m"`` or ``"1h"``. Passing an integer
# seconds value returns 400 ``Input should be '5m' or '1h'``.
_CACHE_TTL = "1h"


_SYSTEM_PROMPT = (
    "You audit findings from a PDF preflight engine against rendered "
    "page images. For each finding the engine emitted, reply by "
    "calling the ``record_verdict`` tool with a status and a "
    "one-sentence rationale.\n\n"
    "Status values:\n"
    "  * ``confirmed``     — the finding is visible / real in the pixels.\n"
    "  * ``disputed``      — the finding is clearly wrong; say what you see instead.\n"
    "  * ``needs_context`` — can't decide without JDF sidecar, brand spec, or similar.\n\n"
    "Default to ``confirmed`` when the finding is plausible against "
    "what you can see. Use ``disputed`` only when the engine's claim "
    "is provably wrong against the rendered pixels. Cite the page "
    "and region in the rationale."
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
                "description": "One-sentence explanation referencing the pixels.",
            },
        },
        "required": ["finding_index", "status", "rationale"],
    },
}


def _render_pages(pdf_bytes: bytes, page_numbers: list[int]) -> dict[int, bytes]:
    """Render each needed page once, memoize for the batch."""
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
            logger.exception(
                "claude-audit: failed to render page %d", page_num
            )
    return cache


def _finding_json(f: JobFinding, index: int) -> dict[str, Any]:
    bbox: list[float] | None = None
    if f.bbox_x0 is not None and f.bbox_y0 is not None:
        bbox = [f.bbox_x0, f.bbox_y0, f.bbox_x1 or 0.0, f.bbox_y1 or 0.0]
    return {
        "index": index,
        "inspection_id": f.inspection_id,
        "severity": f.severity,
        "message": f.message,
        "page_num": f.page_num,
        "bbox": bbox,
    }


def _image_block(png: bytes, *, cache: bool) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.standard_b64encode(png).decode("ascii"),
        },
    }
    if cache:
        block["cache_control"] = {
            "type": "ephemeral",
            "ttl": _CACHE_TTL,
        }
    return block


def _strip_ansi(text: str) -> str:
    """Anthropic rationales occasionally contain stray ANSI escapes."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class ClaudeAuditor:
    """Claude Haiku 4.5 vision auditor.

    ``audit(pdf_bytes, findings) -> list[AuditResult | None]`` — one
    entry per input finding, ``None`` where a batch failed.

    Failures degrade gracefully: an API 5xx / rate-limit error on a
    batch yields ``None`` for every finding in that batch. The
    caller (see :mod:`lintpdf.queue.audit_tasks`) schedules a
    retry with exponential back-off.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "ClaudeAuditor requires the ``anthropic`` package. "
                "Run ``uv sync --extra ai``."
            ) from exc

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required for ClaudeAuditor. Set "
                "it in the env or pass api_key= explicitly."
            )
        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model = model

    def audit(
        self,
        pdf_bytes: bytes,
        findings: Sequence[JobFinding],
    ) -> list[AuditResult | None]:
        if not findings:
            return []

        page_numbers = [f.page_num for f in findings if f.page_num]
        pages = _render_pages(pdf_bytes, page_numbers)

        results: list[AuditResult | None] = [None] * len(findings)
        for batch_start in range(0, len(findings), _MAX_FINDINGS_PER_CALL):
            batch = list(findings[batch_start : batch_start + _MAX_FINDINGS_PER_CALL])
            try:
                verdicts = self._audit_batch(batch, pages)
            except Exception:
                logger.exception(
                    "claude-audit: batch %d..%d failed; leaving verdicts NULL",
                    batch_start,
                    batch_start + len(batch) - 1,
                )
                continue
            for rel_idx, verdict in verdicts.items():
                abs_idx = batch_start + rel_idx
                if 0 <= abs_idx < len(results) and verdict is not None:
                    results[abs_idx] = verdict
        return results

    def _audit_batch(
        self,
        batch: list[JobFinding],
        pages: dict[int, bytes],
    ) -> dict[int, AuditResult | None]:
        """One Claude call per batch; returns index→AuditResult dict."""
        needed_pages = sorted({f.page_num for f in batch if f.page_num})

        content: list[dict[str, Any]] = []
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
            # Cache the last image in the batch — repeated calls
            # against the same PDF re-hit the cache.
            content.append(_image_block(png, cache=(i == len(needed_pages) - 1)))

        payload = [_finding_json(f, i) for i, f in enumerate(batch)]
        content.append(
            {
                "type": "text",
                "text": (
                    "Findings to audit (JSON). Call ``record_verdict`` "
                    "once per entry using the ``index`` field as "
                    "``finding_index``:\n\n"
                    + json.dumps(payload, indent=2)
                ),
            }
        )

        from lintpdf.audit.outage import record_outcome

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1536,
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
        except Exception:
            record_outcome(False)
            raise
        record_outcome(True)

        out: dict[int, AuditResult | None] = {}
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            if getattr(block, "name", None) != "record_verdict":
                continue
            payload = getattr(block, "input", None) or {}
            idx = payload.get("finding_index")
            status = payload.get("status")
            rationale = _strip_ansi(str(payload.get("rationale", ""))).strip()
            if not isinstance(idx, int):
                continue
            if status not in ("confirmed", "disputed", "needs_context"):
                continue
            out[idx] = AuditResult(
                status=status,  # type: ignore[arg-type]
                rationale=rationale or None,
                model=self._model,
                at=datetime.now(UTC),
            )
        return out
