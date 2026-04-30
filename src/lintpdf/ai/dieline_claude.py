"""Sonnet 4.6 visual fallback for dieline detection (WS-D).

Only fires when the name-match heuristic returns zero hits AND the
tenant has ``sonnet_fallback`` in ``ai_features``. One call per
job (page 1 only). Returns a ``DielineResult(source='vision')`` or
``None`` when Sonnet couldn't identify a dieline either.

Sonnet over Haiku: dieline detection is the single spatial-reasoning
call in the pipeline; Haiku's bounding-box output on complex vector
art is unreliable. Cost delta is ~$0.01/job on typical Sonnet
consumption — the dieline fallback rarely fires, so fleet-wide
cost stays bounded.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

from lintpdf.audit.outage import record_outcome

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = os.environ.get("LINTPDF_DIELINE_FALLBACK_MODEL", "claude-sonnet-4-6")
_PAGE_DPI = 150
_CACHE_TTL = "1h"


_SYSTEM_PROMPT = (
    "You inspect a rendered PDF page for a packaging dieline — the "
    "cut / crease / perforation / score contour printed as a "
    "non-ink layer that bounds the art. Trace the outermost "
    "closed polygon that is clearly a dieline (not the art itself). "
    "If the page has no visible dieline, call ``record_dieline`` "
    "with ``polylines=[]`` and explain why in ``reason``."
)


_TOOL_DEFINITION: dict[str, Any] = {
    "name": "record_dieline",
    "description": (
        "Record the dieline contour found on the page, or empty "
        "polylines when no dieline is present."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "polylines": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                "description": "List of closed polygons in PDF user-space points.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "reason": {"type": "string"},
        },
        "required": ["polylines", "confidence", "reason"],
    },
}


def detect_dieline_via_claude(pdf_bytes: bytes, llm_client: Any | None = None) -> Any | None:
    """Call Sonnet for a one-shot dieline verdict; return None on failure.

    Returns a ``DielineResult(source='vision', ...)`` on success,
    or ``None`` if Sonnet couldn't find a dieline (empty polylines
    returned in the tool call). Import kept lazy so the analyzer
    doesn't pull Anthropic at module-load time.

    Phase 3d: ``llm_client`` parameter — the LLMClient service
    instance from ``ctx.services.llm_client``. When ``None``, falls
    back to instantiating ``anthropic.Anthropic()`` directly so
    the helper still runs from contexts without a Services bundle
    (e.g. tests, ad-hoc scripts). Production goes through the
    service.
    """
    from lintpdf.analyzers.dieline import DielineResult
    from lintpdf.rendering import render_page_to_image

    # Phase 3d: prefer ctx.services.llm_client when supplied;
    # otherwise fall back to direct Anthropic SDK instantiation
    # for backwards compat with non-orchestrator callers.
    if llm_client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None

        try:
            import anthropic
        except ImportError:
            logger.warning("dieline-claude: anthropic SDK not installed; skipping fallback")
            return None

        client = anthropic.Anthropic()

        class _DirectAdapter:
            def messages_create(self, **kwargs: Any) -> Any:
                return client.messages.create(**kwargs)

        llm_client = _DirectAdapter()

    try:
        png = render_page_to_image(pdf_bytes, 1, dpi=_PAGE_DPI)
    except Exception:
        logger.exception("dieline-claude: page render failed")
        return None

    try:
        response = llm_client.messages_create(
            model=_DEFAULT_MODEL,
            max_tokens=2048,
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
            tool_choice={"type": "tool", "name": "record_dieline"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Inspect this rendered PDF page and report the dieline contour."
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
        logger.exception("dieline-claude: Sonnet call failed")
        return None
    record_outcome(True)

    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if getattr(block, "name", None) != "record_dieline":
            continue
        payload = getattr(block, "input", None) or {}
        polylines = payload.get("polylines") or []
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        if not polylines:
            return None
        return DielineResult(
            source="vision",
            polylines=[
                [[float(x), float(y)] for x, y in poly]
                for poly in polylines
                if isinstance(poly, list)
            ],
            confidence=max(0.0, min(1.0, confidence)),
            spot_name=None,
        )
    return None
