"""ProcessingStepAnalyzer — OCG layer detection for print processing steps.

Detects Optional Content Groups (OCG layers) with ISO 19593 naming
or common print-related names (dieline, varnish, foil, white ink, etc.).

Check IDs:
    GRD_PROC_001 — Processing step layers detected
    GRD_PROC_002 — White ink layer detected
    GRD_PROC_003 — Dieline layer uses spot color (reserved)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

# Known processing step layer name patterns (case-insensitive)
_PROCESSING_STEP_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bdie\b",
        r"\bdieline\b",
        r"\bcut\s*contour\b",
        r"\bcutcontour\b",
        r"\bvarnish\b",
        r"\bfoil\b",
        r"\bemboss\b",
        r"\bbraille\b",
        r"\bwhite\b",
        r"\bspot\b",
    ]
)

_WHITE_INK_PATTERN = re.compile(r"\bwhite\b", re.IGNORECASE)


class ProcessingStepAnalyzer(BaseAnalyzer):
    """Analyzer for print processing step layers (OCG/OCProperties)."""

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document for processing step layers."""
        findings: list[Finding] = []
        catalog = document.catalog

        oc_properties = catalog.get("/OCProperties")
        if not isinstance(oc_properties, dict):
            return findings

        ocgs = oc_properties.get("/OCGs")
        if not isinstance(ocgs, list):
            return findings

        processing_layers: list[str] = []
        white_layers: list[str] = []

        for ocg in ocgs:
            if not isinstance(ocg, dict):
                continue
            name = ocg.get("/Name", "")
            if not isinstance(name, str) or not name:
                continue

            # Check if layer name matches a known processing step pattern
            for pattern in _PROCESSING_STEP_PATTERNS:
                if pattern.search(name):
                    processing_layers.append(name)
                    break

            # Check specifically for white ink
            if _WHITE_INK_PATTERN.search(name):
                white_layers.append(name)

        # GRD_PROC_001: Processing step layers detected
        if processing_layers:
            findings.append(
                Finding(
                    inspection_id="GRD_PROC_001",
                    severity=Severity.ADVISORY,
                    message=(f"Processing step layers detected: {', '.join(processing_layers)}"),
                    details={
                        "layer_names": processing_layers,
                        "layer_count": len(processing_layers),
                    },
                    iso_clause="ISO 19593-1:2018",
                )
            )

        # GRD_PROC_002: White ink layer detected
        if white_layers:
            findings.append(
                Finding(
                    inspection_id="GRD_PROC_002",
                    severity=Severity.ADVISORY,
                    message=(f"White ink layer detected: {', '.join(white_layers)}"),
                    details={
                        "white_layer_names": white_layers,
                    },
                    iso_clause="ISO 19593-1:2018",
                )
            )

        return findings
