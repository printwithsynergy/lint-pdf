"""Processing steps AI fallback analyzer — visual layer analysis.

Performs visual analysis of PDF layer structure to detect processing step
indicators (e.g. varnish, foil, emboss, die-cut layers) that may not be
explicitly named in the PDF layer tree.  This serves as an AI fallback
when standard layer-name-based detection is inconclusive.

Reports detected processing steps as ADVISORY findings.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.gpu_client import (
    GPUInferenceClient,
    GPUServiceNotConfiguredError,
    GPUServiceRateLimitedError,
    GPUServiceUnavailableError,
)
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Known processing step keywords (case-insensitive patterns)
_PROCESSING_STEP_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("varnish", re.compile(r"\bvarnish\b|\bvarn\b|\black\b", re.IGNORECASE)),
    ("foil", re.compile(r"\bfoil\b|\bhot\s*stamp\b|\bmetallic\b", re.IGNORECASE)),
    ("emboss", re.compile(r"\bemboss\b|\bdeboss\b|\bblind\b", re.IGNORECASE)),
    ("die_cut", re.compile(r"\bdie[\s-]*cut\b|\bkiss[\s-]*cut\b|\bcutting\b", re.IGNORECASE)),
    ("spot_uv", re.compile(r"\bspot\s*uv\b|\bspot\s*gloss\b|\buv\s*coating\b", re.IGNORECASE)),
    ("braille", re.compile(r"\bbraille\b", re.IGNORECASE)),
    ("white_ink", re.compile(r"\bwhite\s*ink\b|\bopaque\s*white\b", re.IGNORECASE)),
    ("perforation", re.compile(r"\bperf\b|\bperforation\b", re.IGNORECASE)),
]

# Spot color names that often indicate processing steps
_SPOT_COLOR_INDICATORS: dict[str, str] = {
    "die": "die_cut",
    "diecut": "die_cut",
    "die cut": "die_cut",
    "varnish": "varnish",
    "foil": "foil",
    "emboss": "emboss",
    "braille": "braille",
    "white": "white_ink",
    "spot uv": "spot_uv",
    "kiss cut": "die_cut",
}


def _get_gpu_client() -> GPUInferenceClient:
    from lintpdf.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


def _analyze_layer_names(document: SemanticDocument) -> list[dict[str, Any]]:
    """Scan PDF layer/OCG names and spot color names for processing step indicators."""
    detected: list[dict[str, Any]] = []

    # Check optional content groups (layers)
    layers = getattr(document, "optional_content_groups", None) or []
    for layer in layers:
        layer_name = str(getattr(layer, "name", ""))
        for step_name, pattern in _PROCESSING_STEP_PATTERNS:
            if pattern.search(layer_name):
                detected.append(
                    {
                        "step": step_name,
                        "source": "layer_name",
                        "detail": layer_name,
                    }
                )
                break

    # Check spot color names from color spaces
    color_spaces = getattr(document, "color_spaces", None) or {}
    for cs_name in color_spaces:
        cs_lower = cs_name.lower()
        for indicator, step_name in _SPOT_COLOR_INDICATORS.items():
            if indicator in cs_lower:
                detected.append(
                    {
                        "step": step_name,
                        "source": "spot_color",
                        "detail": cs_name,
                    }
                )
                break

    return detected


def _analyze_events_for_steps(
    events: list[ContentStreamEvent],
) -> list[dict[str, Any]]:
    """Scan content stream events for processing step patterns."""
    from lintpdf.semantic.events import ColorChangedEvent

    detected: list[dict[str, Any]] = []
    seen_steps: set[str] = set()

    for event in events:
        if isinstance(event, ColorChangedEvent):
            cs_name = getattr(event, "color_space", "")
            cs_lower = cs_name.lower() if cs_name else ""
            for indicator, step_name in _SPOT_COLOR_INDICATORS.items():
                if indicator in cs_lower and step_name not in seen_steps:
                    seen_steps.add(step_name)
                    detected.append(
                        {
                            "step": step_name,
                            "source": "content_stream_color",
                            "detail": cs_name,
                            "page_num": event.page_num,
                        }
                    )

    return detected


@register_ai_analyzer
class ProcessingStepsFallbackAnalyzer(BaseAIAnalyzer):
    """Detect processing steps through visual layer analysis (AI fallback)."""

    category = "symbol_detection"
    feature_slug = "processing_steps_ai_fallback"
    tier = "gpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        findings: list[Finding] = []
        all_detected_steps: list[dict[str, Any]] = []

        # Phase 1: Structural analysis — layer names and spot colors (CPU)
        layer_steps = _analyze_layer_names(document)
        all_detected_steps.extend(layer_steps)

        # Phase 2: Content stream analysis — color space references (CPU)
        event_steps = _analyze_events_for_steps(events)
        all_detected_steps.extend(event_steps)

        # Phase 3: GPU visual analysis — render pages and look for visual
        # indicators of processing steps (e.g. varnish mask patterns,
        # spot color overlays that are visually distinct)
        if not all_detected_steps:
            # Only invoke GPU if structural analysis found nothing — this is
            # the "fallback" path
            from lintpdf.ai.rendering import render_page_to_image

            gpu = _get_gpu_client()

            # Check first page as representative sample
            try:
                first_page_png = render_page_to_image(pdf_bytes, page_num=1, dpi=150)
            except RuntimeError:
                logger.debug("processing_steps_fallback: PDF rendering backend unavailable")
                return []

            try:
                result = gpu.detect_objects(
                    first_page_png,
                    prompt="varnish mask. foil area. emboss region. die cut line. spot UV.",
                )
            except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
                logger.debug("processing_steps_fallback: GPU service not configured, skipping")
                return []
            except GPUServiceUnavailableError as exc:
                return [
                    self._make_finding(
                        inspection_id="AI_PSTEP_001",
                        severity=Severity.ADVISORY,
                        message=(
                            "GPU inference service unavailable for processing "
                            f"step detection: {exc}"
                        ),
                        details={"reason": "gpu_unavailable"},
                    )
                ]

            detections = result.get("detections", [])
            for detection in detections:
                label = detection.get("label", "")
                confidence = float(detection.get("confidence", 0))
                if confidence >= 0.4:
                    # Map detected label back to a processing step name
                    step_name = label.lower().replace(" ", "_")
                    all_detected_steps.append(
                        {
                            "step": step_name,
                            "source": "gpu_visual_detection",
                            "detail": label,
                            "confidence": round(confidence, 4),
                            "page_num": 1,
                        }
                    )

        # Deduplicate detected steps by name
        seen: set[str] = set()
        unique_steps: list[dict[str, Any]] = []
        for step in all_detected_steps:
            if step["step"] not in seen:
                seen.add(step["step"])
                unique_steps.append(step)

        # Generate findings for each detected processing step
        for step_info in unique_steps:
            step_name = step_info["step"]
            source = step_info["source"]
            detail = step_info.get("detail", "")
            page_num = step_info.get("page_num", 0)

            findings.append(
                self._make_finding(
                    inspection_id="AI_PSTEP_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Processing step detected: '{step_name}' "
                        f"(source: {source}, detail: '{detail}')"
                    ),
                    page_num=page_num,
                    details={
                        "processing_step": step_name,
                        "detection_source": source,
                        "detail": detail,
                        "confidence": step_info.get("confidence"),
                    },
                )
            )

        if not findings:
            findings.append(
                self._make_finding(
                    inspection_id="AI_PSTEP_003",
                    severity=Severity.ADVISORY,
                    message="No processing steps detected in document.",
                    details={"reason": "none_detected"},
                )
            )

        return findings
