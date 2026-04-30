"""Dieline detection by layer and spot color name matching.

Scans PDF layers (Optional Content Groups) and spot color definitions
for names that indicate die line, cut, crease, fold, or perforation
elements commonly used in packaging artwork.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from siftpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from siftpdf.ai.registry import register_ai_analyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.plugin.protocol import AnalyzerContext
    from siftpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Known dieline layer/OCG name patterns (case-insensitive)
_LAYER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bdie\b", re.IGNORECASE),
    re.compile(r"\bdieline\b", re.IGNORECASE),
    re.compile(r"\bdie\s*line\b", re.IGNORECASE),
    re.compile(r"\bcut\b", re.IGNORECASE),
    re.compile(r"\bcutcontour\b", re.IGNORECASE),
    re.compile(r"\bcut\s*contour\b", re.IGNORECASE),
    re.compile(r"\bkiss\s*cut\b", re.IGNORECASE),
    re.compile(r"\bcrease\b", re.IGNORECASE),
    re.compile(r"\bscore\b", re.IGNORECASE),
    re.compile(r"\bperf\b", re.IGNORECASE),
    re.compile(r"\bfold\b", re.IGNORECASE),
]

# Spot color names that typically indicate dieline elements.
# Extended 2026-04-28 to include the canonical ISO 19593-1
# ProcessingStep names so an artwork that uses /Cutting / /Crease
# / /Perforating spots gets detected as having dielines without
# the operator needing to alias them to /Dieline.
_SPOT_COLOR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcutcontour\b", re.IGNORECASE),
    re.compile(r"\bdieline\b", re.IGNORECASE),
    re.compile(r"\bdie\b", re.IGNORECASE),
    re.compile(r"\bcrease\b", re.IGNORECASE),
    re.compile(r"\bcut\b", re.IGNORECASE),
    re.compile(r"\bcutting\b", re.IGNORECASE),
    re.compile(r"\bperforating\b", re.IGNORECASE),
    re.compile(r"\bkiss\s*cut\b", re.IGNORECASE),
    re.compile(r"\bfold\s*line\b", re.IGNORECASE),
    re.compile(r"\bperf\s*line\b", re.IGNORECASE),
]

# Text indicators that the artwork carries a tear / perf / fold line
# even when no named dieline spot or layer is declared. Common on
# stick-pack and pouch labels where the dieline lives on a generic
# Cyan or Magenta stroke rather than a /Cutting separation. The
# 2026-04-28 Opus audit flagged 2 false-negative AI_DIE_002 findings
# on AN-Energy stick-packs that had bilingual EN/FR tear-line
# indicators but no dieline-named spot.
#
# Match must appear standalone (word-boundary) and must be in
# upper-or-mixed case to look like a callout, not body copy. The
# patterns intentionally cover both English and French because the
# dominant miss case was Canadian bilingual packaging.
_TEAR_LINE_INDICATORS: list[re.Pattern[str]] = [
    re.compile(r"\bTEAR\s+ACROSS\b", re.IGNORECASE),
    re.compile(r"\bTEAR\s+HERE\b", re.IGNORECASE),
    re.compile(r"\bTEAR\s+OPEN\b", re.IGNORECASE),
    re.compile(r"\bDÉCHIR(?:ER|EZ)\s+(?:ICI|LE\s+SACHET)\b", re.IGNORECASE),
    re.compile(r"\bDECHIR(?:ER|EZ)\s+(?:ICI|LE\s+SACHET)\b", re.IGNORECASE),
    re.compile(r"\bCUT\s+HERE\b", re.IGNORECASE),
    re.compile(r"\bCUT\s+ALONG\b", re.IGNORECASE),
    re.compile(r"\bCOUPER\s+ICI\b", re.IGNORECASE),
    re.compile(r"\bFOLD\s+HERE\b", re.IGNORECASE),
    re.compile(r"\bPLIER\s+ICI\b", re.IGNORECASE),
    re.compile(r"\bPERF(?:ORATION)?\s+LINE\b", re.IGNORECASE),
    re.compile(r"\bOUVRIR\s+ICI\b", re.IGNORECASE),  # FR "open here"
    re.compile(r"\bOPEN\s+HERE\b", re.IGNORECASE),
]


def _extract_text_dieline_indicators(document: SemanticDocument) -> list[str]:
    """Walk page content streams and return any matched tear / perf
    / fold callout phrases. These indicate that the artwork carries
    a dieline-equivalent (tear-line, perf, fold) even when no named
    dieline spot is declared.

    Returns a list of matched phrases (with original casing where
    available, lowercased otherwise) — caller treats each match as
    one dieline-detection signal.
    """
    matches: list[str] = []
    for page in document.pages:
        raw = page.content_stream
        if not raw:
            continue
        if isinstance(raw, bytes):
            try:
                text = raw.decode("latin-1")
            except Exception:
                continue
        else:
            text = str(raw)
        for pat in _TEAR_LINE_INDICATORS:
            m = pat.search(text)
            if m:
                phrase = m.group(0)
                if phrase not in matches:
                    matches.append(phrase)
    return matches


def _extract_ocg_names(document: SemanticDocument) -> list[str]:
    """Extract Optional Content Group (layer) names from the document catalog."""
    names: list[str] = []

    catalog = document.catalog
    if not catalog:
        return names

    # OCProperties → OCGs array contains the layer references
    oc_properties = catalog.get("OCProperties", {})
    if isinstance(oc_properties, dict):
        ocgs = oc_properties.get("OCGs", [])
        if isinstance(ocgs, list):
            for ocg in ocgs:
                if isinstance(ocg, dict):
                    name = ocg.get("Name", "")
                    if name:
                        names.append(str(name))

        # Also check the Order array in the D (default config) dict
        default_config = oc_properties.get("D", {})
        if isinstance(default_config, dict):
            order = default_config.get("Order", [])
            if isinstance(order, list):
                _collect_names_from_order(order, names)

    return names


def _collect_names_from_order(order: list[Any], names: list[str]) -> None:
    """Recursively collect OCG names from the Order array."""
    for item in order:
        if isinstance(item, dict):
            name = item.get("Name", "")
            if name:
                names.append(str(name))
        elif isinstance(item, list):
            _collect_names_from_order(item, names)
        elif isinstance(item, str):
            names.append(item)


def _extract_spot_color_names(document: SemanticDocument) -> list[str]:  # skipcq: PY-R1000
    """Extract spot color (Separation/DeviceN) names from page color spaces."""
    spot_names: list[str] = []

    for page in document.pages:
        for _cs_name, cs in page.color_spaces.items():
            if (cs.cs_type == "Separation" and cs.colorant_names) or (
                cs.cs_type == "DeviceN" and cs.colorant_names
            ):
                for name in cs.colorant_names:
                    if name and name not in ("All", "None"):
                        spot_names.append(str(name))

        # Also check resources dict for raw color space entries
        resources = page.resources
        if isinstance(resources, dict):
            color_spaces_dict = resources.get("ColorSpace", {})
            if isinstance(color_spaces_dict, dict):
                for _cs_key, cs_val in color_spaces_dict.items():
                    # Separation color spaces are arrays: [/Separation name alternateCS tintTransform]
                    if isinstance(cs_val, (list, tuple)) and len(cs_val) >= 2:
                        cs_type = str(cs_val[0]) if cs_val else ""
                        if "Separation" in cs_type and len(cs_val) >= 2:
                            colorant = str(cs_val[1])
                            if colorant and colorant not in ("All", "None"):
                                spot_names.append(colorant)

    return spot_names


def _is_packaging_file(document: SemanticDocument, ai_config: Any) -> bool:
    """Heuristic to determine if the file is packaging artwork.

    Checks industry type from config and document characteristics.
    """
    if ai_config is not None:
        industry = getattr(ai_config, "industry_type", None)
        if industry and industry.lower() in (
            "packaging",
            "labels",
            "folding_carton",
            "corrugated",
            "flexible_packaging",
            "shrink_sleeve",
        ):
            return True

    # Check if document has packaging-related spot colors (beyond dieline)
    for page in document.pages:
        for cs in page.color_spaces.values():
            if cs.cs_type in ("Separation", "DeviceN"):
                return True

    return False


@register_ai_analyzer
class DielineByNameAnalyzer(BaseAIAnalyzer):
    """Detect die lines by matching layer and spot color names."""

    category = "dieline_detection"
    feature_slug = "dieline_by_name"
    tier = "cpu"
    credits_per_run = 1

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses document
        # + ai_config (.industry_type). Reconstituted via
        # _reconstitute_ai_config to preserve attribute access.
        document = ctx.document
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        findings: list[Finding] = []
        detected_dielines: list[dict[str, Any]] = []

        # Check layers/OCGs
        ocg_names = _extract_ocg_names(document)
        for name in ocg_names:
            for pattern in _LAYER_PATTERNS:
                if pattern.search(name):
                    detected_dielines.append(
                        {
                            "source": "layer",
                            "name": name,
                            "pattern": pattern.pattern,
                        }
                    )
                    break

        # Check spot colors
        spot_names = _extract_spot_color_names(document)
        for name in spot_names:
            for pattern in _SPOT_COLOR_PATTERNS:
                if pattern.search(name):
                    detected_dielines.append(
                        {
                            "source": "spot_color",
                            "name": name,
                            "pattern": pattern.pattern,
                        }
                    )
                    break

        # Check page text for tear / perf / fold callouts. Catches
        # stick-packs and pouches that carry the dieline on a generic
        # Cyan/Magenta stroke rather than a named separation but
        # include bilingual EN/FR "TEAR ACROSS / DÉCHIRER ICI" markers.
        text_indicators = _extract_text_dieline_indicators(document)
        for phrase in text_indicators:
            detected_dielines.append(
                {
                    "source": "text_indicator",
                    "name": phrase,
                    "pattern": "tear_line_callout",
                }
            )

        if detected_dielines:
            # Deduplicate by name
            seen_names: set[str] = set()
            unique: list[dict[str, Any]] = []
            for dl in detected_dielines:
                lower_name = dl["name"].lower()
                if lower_name not in seen_names:
                    seen_names.add(lower_name)
                    unique.append(dl)

            layer_names = [d["name"] for d in unique if d["source"] == "layer"]
            spot_names_found = [d["name"] for d in unique if d["source"] == "spot_color"]
            text_indicators_found = [d["name"] for d in unique if d["source"] == "text_indicator"]

            parts: list[str] = []
            if layer_names:
                parts.append(f"layers: {', '.join(layer_names)}")
            if spot_names_found:
                parts.append(f"spot colors: {', '.join(spot_names_found)}")
            if text_indicators_found:
                parts.append(f"tear/perf indicators: {', '.join(text_indicators_found)}")

            findings.append(
                self._make_finding(
                    inspection_id="AI_DIE_001",
                    severity=Severity.ADVISORY,
                    message=f"Die line detected via {'; '.join(parts)}",
                    details={
                        "dieline_layers": layer_names,
                        "dieline_spot_colors": spot_names_found,
                        "dieline_text_indicators": text_indicators_found,
                        "matches": unique,
                    },
                )
            )
        else:
            # No dieline found
            is_packaging = _is_packaging_file(document, ai_config)
            if is_packaging:
                # The 2026-04-28 post-merge audit found AI_DIE_002 firing
                # at WARNING on Pink-Slush + HSI_ADM stick-packs whose
                # dieline is drawn as a stroke on a process color (e.g.
                # /Cyan or /Magenta) rather than a named separation.
                # Opus correctly saw the dieline visually. The engine's
                # name-based detection cannot find these without OCR or
                # a vector-perimeter heuristic. When the file has any
                # spot colors at all, demote to ADVISORY and explain the
                # limitation in the message — it's an honest "we may have
                # missed it" rather than an incorrect "missing".
                has_any_spots = bool(spot_names)
                severity = Severity.ADVISORY if has_any_spots else Severity.WARNING
                if has_any_spots:
                    message = (
                        "No NAMED die line layer or spot color detected. "
                        "The artwork has spot colors but none match common "
                        "dieline patterns (CutContour, Dieline, Crease, "
                        "Cutting, Perforating). The dieline may be drawn on "
                        "a process color stroke — verify visually."
                    )
                else:
                    message = (
                        "No die line detected in packaging file. "
                        "Expected a die line layer or spot color "
                        "(e.g., CutContour, Dieline, Crease)."
                    )
                findings.append(
                    self._make_finding(
                        inspection_id="AI_DIE_002",
                        severity=severity,
                        message=message,
                        details={
                            "checked_layers": ocg_names,
                            "checked_spot_colors": list(set(spot_names)),
                            "industry_type": getattr(ai_config, "industry_type", None)
                            if ai_config
                            else None,
                            "has_unnamed_spots": has_any_spots,
                        },
                    )
                )
            else:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_DIE_003",
                        severity=Severity.ADVISORY,
                        message="No die line detected (file does not appear to be packaging artwork).",
                        details={
                            "checked_layers": ocg_names,
                            "checked_spot_colors": list(set(spot_names)),
                        },
                    )
                )

        return findings
