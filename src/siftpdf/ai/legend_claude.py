"""Sonnet 4.6 fallback for ambiguous legend/art swatch classification (WS-D).

One call per batch of ambiguous swatches. Returns one verdict per
input swatch (``None`` where Sonnet declined). The caller only
invokes this path when the tenant has ``sonnet_fallback``.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

from siftpdf.audit.outage import record_outcome

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = os.environ.get("LINTPDF_LEGEND_FALLBACK_MODEL", "claude-sonnet-4-6")
_CACHE_TTL = "1h"
_PAGE_DPI = 150


_TOOL_DEFINITION: dict[str, Any] = {
    "name": "record_swatch_verdict",
    "description": "Label one swatch as legend or art.",
    "input_schema": {
        "type": "object",
        "properties": {
            "index": {"type": "integer"},
            "kind": {"type": "string", "enum": ["legend", "art", "unknown"]},
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
        "required": ["index", "kind", "confidence"],
    },
}


_SYSTEM_PROMPT = (
    "You classify color swatches on a packaging page as either "
    "'legend' (part of a print-operator legend / key / ink list) "
    "or 'art' (actual artwork on the package). Call "
    "``record_swatch_verdict`` once per input index."
)


def classify_swatches_via_claude(
    pdf_bytes: bytes,
    swatches: list[dict[str, Any]],
    llm_client: Any | None = None,
) -> list[Any]:
    """Run Sonnet on a batch of ambiguous swatches.

    Returns ``[SwatchClassification | None, ...]`` aligned with
    ``swatches``. Lazy-imports ``SwatchClassification`` to keep
    this module free of analyzer imports at load time.

    Phase 3d: ``llm_client`` parameter — the LLMClient service
    instance. When ``None``, falls back to instantiating
    ``anthropic.Anthropic()`` directly for backwards compat with
    non-orchestrator callers.
    """
    from siftpdf.analyzers.legend import SwatchClassification
    from siftpdf.rendering import render_page_to_image

    if not swatches:
        return [None] * len(swatches)

    if llm_client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return [None] * len(swatches)

        try:
            import anthropic
        except ImportError:
            logger.warning("legend-claude: anthropic SDK not installed; skipping")
            return [None] * len(swatches)

        client = anthropic.Anthropic()

        class _DirectAdapter:
            def messages_create(self, **kwargs: Any) -> Any:
                return client.messages.create(**kwargs)

        llm_client = _DirectAdapter()

    try:
        png = render_page_to_image(pdf_bytes, 1, dpi=_PAGE_DPI)
    except Exception:
        logger.exception("legend-claude: page render failed")
        return [None] * len(swatches)

    payload = [
        {
            "index": i,
            "spot_name": str(sw.get("spot_name", "")),
            "bbox": sw.get("bbox"),
        }
        for i, sw in enumerate(swatches)
    ]

    try:
        response = llm_client.messages_create(
            model=_DEFAULT_MODEL,
            max_tokens=1024,
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
            tool_choice={"type": "tool", "name": "record_swatch_verdict"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Ambiguous swatches (JSON). One verdict "
                                "per index:\n" + _json_dump(payload)
                            ),
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64.standard_b64encode(png).decode("ascii"),
                            },
                            "cache_control": {
                                "type": "ephemeral",
                                "ttl": _CACHE_TTL,
                            },
                        },
                    ],
                }
            ],
        )
    except Exception:
        record_outcome(False)
        logger.exception("legend-claude: Sonnet call failed")
        return [None] * len(swatches)
    record_outcome(True)

    verdicts: list[Any] = [None] * len(swatches)
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if getattr(block, "name", None) != "record_swatch_verdict":
            continue
        p = getattr(block, "input", None) or {}
        idx = p.get("index")
        kind = p.get("kind")
        confidence = float(p.get("confidence", 0.0) or 0.0)
        if not isinstance(idx, int) or idx < 0 or idx >= len(swatches):
            continue
        if kind not in ("legend", "art", "unknown"):
            continue
        sw = swatches[idx]
        bbox = sw.get("bbox") or [0.0, 0.0, 0.0, 0.0]
        verdicts[idx] = SwatchClassification(
            spot_name=str(sw.get("spot_name", "")),
            bbox=[float(x) for x in bbox],
            kind=kind,
            source="vision",
            confidence=max(0.0, min(1.0, confidence)),
        )
    return verdicts


def _json_dump(obj: Any) -> str:
    import json

    return json.dumps(obj, indent=2)
