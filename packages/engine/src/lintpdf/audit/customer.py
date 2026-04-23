"""Customer-facing audit pass — Modal-hosted vision LLM.

Runs after ``run_preflight`` when the tenant has
``entitlements.ai_audit_enabled`` (Scale + Enterprise plans).
Unlike :class:`lintpdf.audit.internal.InternalAuditor` (which uses
Claude Opus 4.7 and is operator-only), this pass calls a
Modal-hosted Qwen2-VL-7B-Instruct / Llama 3.2 11B Vision endpoint
configured via ``LINTPDF_AUDIT_MODAL_URL``.

The two auditors share :class:`lintpdf.audit.types.AuditResult` so
the ``run_preflight`` sink is identical — only the auditor class
differs. On Modal transport failure (timeout, 5xx, DNS) every
finding in the batch gets ``status="error"`` and the caller writes
``NULL`` to the DB columns; it re-audits on the next engine pass.

Transport: plain ``urllib.request.urlopen`` — no extra
dependencies. Adds ~1 KB per finding to request body (JSON
payload + base64 PNG). Each Modal container handles one batch at
a time on an A10G GPU.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lintpdf.api.models import JobFinding

from lintpdf.audit.types import AuditResult

logger = logging.getLogger(__name__)

# Keep batches smaller than the internal pass — Modal containers
# are memory-bound (A10G has 24 GB VRAM split between the model
# weights and the image tensor). 20 findings per call keeps us
# well inside the token budget even with multi-page PDFs.
_MAX_FINDINGS_PER_CALL = 20
_PAGE_DPI = 150
_DEFAULT_TIMEOUT_S = 120
_DEFAULT_MODEL_ID = "modal:qwen2-vl-7b"


def _render_pages(pdf_bytes: bytes, page_numbers: list[int]) -> dict[int, bytes]:
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
                "customer-audit: failed to render page %d", page_num
            )
    return cache


def _finding_payload(
    f: JobFinding, index: int, page_png_b64: str | None
) -> dict[str, Any]:
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
        "page_png_b64": page_png_b64,
    }


class CustomerAuditor:
    """Customer-facing Modal vision-LLM auditor.

    Wire-up:
      1. Modal app at :mod:`inference_service.modal_audit` deploys
         the vision LLM as an HTTPS endpoint.
      2. ``LINTPDF_AUDIT_MODAL_URL`` on the Railway Worker / Worker-AI
         services points at that endpoint.
      3. ``run_preflight`` constructs a ``CustomerAuditor`` and calls
         ``audit(pdf_bytes, findings)`` when the tenant has
         ``entitlements.ai_audit_enabled``.

    Errors degrade gracefully: a full-batch transport failure
    returns ``None`` for every verdict so the DB columns stay NULL
    rather than being filled with bogus "error" rows. The customer
    sees no chip, and the next preflight pass re-audits.
    """

    def __init__(
        self,
        *,
        endpoint_url: str | None = None,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
        model_id: str = _DEFAULT_MODEL_ID,
    ) -> None:
        resolved_url = endpoint_url or os.environ.get("LINTPDF_AUDIT_MODAL_URL")
        if not resolved_url:
            raise RuntimeError(
                "CustomerAuditor requires LINTPDF_AUDIT_MODAL_URL or "
                "endpoint_url= kwarg."
            )
        self._url = resolved_url.rstrip("/")
        self._timeout_s = timeout_s
        self._model_id = model_id

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
            except (urllib.error.URLError, TimeoutError, OSError):
                logger.exception(
                    "customer-audit: transport error on batch %d..%d",
                    batch_start,
                    batch_start + len(batch) - 1,
                )
                # Leave results[...] = None for the batch; caller
                # interprets None as "not audited" and writes NULL.
                continue
            for i, verdict in enumerate(verdicts):
                if verdict is None:
                    continue
                status = verdict.get("status")
                if status not in ("confirmed", "disputed", "needs_context"):
                    continue
                results[batch_start + i] = AuditResult(
                    status=status,  # type: ignore[arg-type]
                    rationale=verdict.get("rationale"),
                    model=self._model_id,
                    at=datetime.now(UTC),
                )
        return results

    def _audit_batch(
        self, batch: list[JobFinding], pages: dict[int, bytes]
    ) -> list[dict[str, Any] | None]:
        """POST one batch to the Modal endpoint; return verdict list aligned to batch order."""
        payload = {
            "findings": [
                _finding_payload(
                    f,
                    index=i,
                    page_png_b64=(
                        base64.standard_b64encode(pages[f.page_num]).decode("ascii")
                        if f.page_num and f.page_num in pages
                        else None
                    ),
                )
                for i, f in enumerate(batch)
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        # ``LINTPDF_AUDIT_MODAL_URL`` already points at the function's
        # full ``@modal.fastapi_endpoint(label="audit")`` URL — Modal
        # web endpoints serve at the function root, not a sub-path, so
        # we POST to the URL verbatim rather than appending ``/audit``.
        req = urllib.request.Request(
            self._url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
            raw = resp.read()
        doc = json.loads(raw)
        verdicts_in = doc.get("verdicts") or []

        # Align by index field so out-of-order responses still land on
        # the right finding. Missing indices stay None.
        aligned: list[dict[str, Any] | None] = [None] * len(batch)
        for entry in verdicts_in:
            idx = entry.get("finding_index")
            if isinstance(idx, int) and 0 <= idx < len(aligned):
                aligned[idx] = entry
        return aligned
