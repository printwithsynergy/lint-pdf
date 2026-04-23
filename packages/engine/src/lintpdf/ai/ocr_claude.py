"""Claude Haiku 4.5 vision OCR for outlined PDFs (WS-C).

Called after preflight when the extractable-text pass returns
< 5 chars on any page *and* the tenant has ``ocr`` in
``ai_features``. Falls back to vision OCR so downstream checks
(typos, bleed-into-text, brand-spec matching) still fire on
outlined artwork.

Reuses the prompt-caching + tool-use pattern from
:mod:`lintpdf.audit.claude` verbatim — identical ``cache_control``
TTL (``"1h"``), identical page-rendering pipeline.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

from lintpdf.ai.ocr_types import OCRPage, OCRTextBlock
from lintpdf.audit.outage import record_outcome

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = os.environ.get("LINTPDF_OCR_MODEL", "claude-haiku-4-5")
_PAGE_DPI = 150
_CACHE_TTL = "1h"


_SYSTEM_PROMPT = (
    "You are performing OCR on a rendered PDF page. Extract every "
    "legible text run on the page — including outlined/vectorised "
    "text that the PDF's text extractor missed. For each text run, "
    "call ``record_text_block`` with the text, its bounding box in "
    "PDF user-space points (bottom-left origin), and a confidence "
    "score 0-1. Scan the whole page; don't stop at the first few blocks."
)


_TOOL_DEFINITION: dict[str, Any] = {
    "name": "record_text_block",
    "description": "Record one recovered text block on the current page.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 4,
                "maxItems": 4,
                "description": "[x0, y0, x1, y1] in PDF user-space points.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
        "required": ["text", "bbox", "confidence"],
    },
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
        block["cache_control"] = {"type": "ephemeral", "ttl": _CACHE_TTL}
    return block


class ClaudeOCR:
    """Vision OCR auditor for outlined PDFs.

    ``extract(pdf_bytes, page_nums) -> list[OCRPage]`` — one
    ``OCRPage`` per page successfully processed. Pages that
    error out are silently skipped (the caller treats their
    text layer as empty).
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
                "ClaudeOCR requires the ``anthropic`` package."
            ) from exc

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required for ClaudeOCR."
            )
        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model = model

    def extract(
        self,
        pdf_bytes: bytes,
        page_nums: list[int],
        *,
        tenant_id: Any | None = None,
        job_id: Any | None = None,
    ) -> list[OCRPage]:
        from lintpdf.ai.rendering import render_page_to_image

        out: list[OCRPage] = []
        for page_num in sorted(set(page_nums)):
            if page_num <= 0:
                continue
            try:
                png = render_page_to_image(pdf_bytes, page_num, dpi=_PAGE_DPI)
            except Exception:
                logger.exception(
                    "claude-ocr: failed to render page %d", page_num
                )
                continue
            try:
                blocks = self._ocr_page(
                    page_num, png, tenant_id=tenant_id, job_id=job_id
                )
            except Exception:
                logger.exception(
                    "claude-ocr: Claude call for page %d failed", page_num
                )
                continue
            out.append(OCRPage(page_num=page_num, blocks=blocks))
        return out

    def _ocr_page(
        self,
        page_num: int,
        png: bytes,
        *,
        tenant_id: Any | None = None,
        job_id: Any | None = None,
    ) -> list[OCRTextBlock]:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"OCR the full text of page {page_num} "
                    f"(rendered at {_PAGE_DPI} DPI). One "
                    "``record_text_block`` call per distinct run."
                ),
            },
            _image_block(png, cache=True),
        ]

        try:
            response = self._client.messages.create(
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
                tool_choice={"type": "tool", "name": "record_text_block"},
                messages=[{"role": "user", "content": content}],
            )
        except Exception:
            record_outcome(False)
            raise
        record_outcome(True)

        # Metering — OCR counts as its own feature line.
        if tenant_id is not None:
            try:
                from lintpdf.audit.metering import record_usage

                usage = getattr(response, "usage", None)
                record_usage(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    feature="ocr",
                    model=self._model,
                    input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                    cache_read_tokens=int(
                        getattr(usage, "cache_read_input_tokens", 0) or 0
                    ),
                    cache_write_tokens=int(
                        getattr(usage, "cache_creation_input_tokens", 0) or 0
                    ),
                )
            except Exception:
                logger.warning("claude-ocr: metering write failed", exc_info=True)

        blocks: list[OCRTextBlock] = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            if getattr(block, "name", None) != "record_text_block":
                continue
            payload = getattr(block, "input", None) or {}
            text = str(payload.get("text", "")).strip()
            if not text:
                continue
            bbox = payload.get("bbox")
            if (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or not all(isinstance(x, int | float) for x in bbox)
            ):
                continue
            confidence = float(payload.get("confidence", 0.0) or 0.0)
            blocks.append(
                OCRTextBlock(
                    text=text,
                    bbox=[float(x) for x in bbox],
                    confidence=max(0.0, min(1.0, confidence)),
                )
            )
        return blocks


def ocr_result_to_json(pages: list[OCRPage]) -> list[dict[str, Any]]:
    """Convert ``list[OCRPage]`` to the JSON-friendly shape used by
    ``JobResponse.ocr_text_layer`` and the ``Job.ocr_text_layer`` column."""
    return [
        {
            "page_num": p.page_num,
            "blocks": [
                {
                    "text": b.text,
                    "bbox": b.bbox,
                    "confidence": b.confidence,
                }
                for b in p.blocks
            ],
        }
        for p in pages
    ]
