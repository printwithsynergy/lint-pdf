"""GHS/CLP compliance analyzer per EU Regulation 1272/2008.

Validates hazard communication labels:
- GHS pictogram detection and sizing per package capacity
- Mutual exclusion rules (e.g., GHS06 supersedes GHS07)
- H-statement and P-statement detection
- Signal word validation
"""

from __future__ import annotations

import contextlib
import logging
import math
import re
from typing import TYPE_CHECKING, Any

from lintpdf.ai.analyzers.regulatory_compliance._gates import is_ghs_applicable
from lintpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# GHS pictogram identifiers and their meanings
_GHS_PICTOGRAMS: dict[str, str] = {
    "GHS01": "Exploding Bomb",
    "GHS02": "Flame",
    "GHS03": "Flame over Circle",
    "GHS04": "Gas Cylinder",
    "GHS05": "Corrosion",
    "GHS06": "Skull and Crossbones",
    "GHS07": "Exclamation Mark",
    "GHS08": "Health Hazard",
    "GHS09": "Environment",
}

# Mutual exclusion rules: if left is present, right should NOT be present
_MUTUAL_EXCLUSIONS: list[tuple[str, str, str]] = [
    ("GHS06", "GHS07", "GHS06 (acute toxicity) supersedes GHS07 (irritant)"),
    ("GHS05", "GHS07", "GHS05 (corrosive) supersedes GHS07 for skin/eye effects"),
    ("GHS02", "GHS04", "GHS02 (flammable) takes precedence over GHS04 for flammable gases"),
]

# Minimum pictogram sizes by package capacity (CLP Regulation Article 31)
# Format: (max_capacity_ml, min_side_mm)
_PICTOGRAM_SIZE_BY_CAPACITY: list[tuple[float, float]] = [
    (3.0, 10.0),  # ≤3 mL (or g): can be smaller, min 10mm if possible
    (50.0, 10.0),  # ≤50 mL: 10mm minimum
    (500.0, 16.0),  # ≤500 mL: 16mm minimum
    (float("inf"), 23.0),  # >500 mL: 23mm minimum (general rule)
]

# H-statement patterns
_H_STATEMENT_PATTERN = re.compile(r"\b(H[2-4]\d{2}[A-Za-z]?(?:\s*\+\s*H[2-4]\d{2}[A-Za-z]?)*)\b")

# P-statement patterns
_P_STATEMENT_PATTERN = re.compile(r"\b(P[1-5]\d{2}(?:\s*\+\s*P[1-5]\d{2})*)\b")

# Signal words
_SIGNAL_WORDS = {"Danger", "Warning"}

# Prop 65 cautionary text uses "WARNING" exactly the way CLP does,
# but it's regulated under California Health & Safety Code 25249.5
# -- not CLP Regulation 1272/2008. Signal-word hits that land
# inside a proximity window around any of these anchor phrases
# are treated as Prop 65, not GHS, and do NOT trigger AI_GHS_003.
_PROP65_ANCHORS = (
    "proposition 65",
    "prop 65",
    "prop. 65",
    "p65",
    "p65warnings.ca.gov",
    "cancer and/or reproductive harm",
    "cancer or reproductive harm",
    "known to the state of california",
)
# Chars of context either side of a signal-word match that we'll
# scan for a Prop 65 anchor. 500 matches the window the plan
# called out (wide enough to catch multi-line disclaimer blocks).
_PROP65_WINDOW_CHARS = 500


def _get_min_pictogram_size_mm(capacity_ml: float | None) -> float:
    """Determine minimum GHS pictogram side length for given package capacity."""
    if capacity_ml is None:
        return 16.0  # Default to medium package

    for max_capacity, min_side in _PICTOGRAM_SIZE_BY_CAPACITY:
        if capacity_ml <= max_capacity:
            return min_side

    return 23.0


@register_ai_analyzer
class GhsClpAnalyzer(BaseAIAnalyzer):
    """Validate GHS/CLP hazard labels per EU Regulation 1272/2008."""

    category = "regulatory_compliance"
    feature_slug = "ghs_clp_compliance"
    tier = "cpu"
    credits_per_run = 1

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses document
        # + events + ai_config (.default_package_capacity_ml +
        # .is_ghs_applicable). Reconstituted via _reconstitute_ai_config.
        # pdf_bytes declared but never used.
        document = ctx.document
        events = ctx.events
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        findings: list[Finding] = []

        # Get package capacity from config
        capacity_ml: float | None = None
        if ai_config is not None:
            raw = getattr(ai_config, "default_package_capacity_ml", None)
            if raw is not None:
                with contextlib.suppress(TypeError, ValueError):
                    capacity_ml = float(raw)

        min_pictogram_mm = _get_min_pictogram_size_mm(capacity_ml)

        # Scan all pages for GHS content
        all_text = ""
        for page in document.pages:
            if page.content_stream:
                raw = page.content_stream
                if isinstance(raw, bytes):
                    try:
                        decoded = raw.decode("latin-1")
                    except Exception:
                        decoded = ""
                else:
                    decoded = str(raw)
                all_text += decoded + "\n"

        # Detect GHS pictograms by name in document resources and text
        detected_pictograms = self._detect_pictograms(document, all_text)
        h_statements = self._detect_h_statements(all_text)
        p_statements = self._detect_p_statements(all_text)
        signal_words = self._detect_signal_words(all_text)

        has_ghs_content = bool(detected_pictograms or h_statements or signal_words)

        if not has_ghs_content:
            # No GHS content detected — not an error unless expected
            return []

        # Report detected pictograms
        if detected_pictograms:
            findings.append(
                self._make_finding(
                    inspection_id="AI_GHS_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"GHS pictograms detected: {', '.join(sorted(detected_pictograms.keys()))}"
                    ),
                    details={
                        "pictograms": {
                            k: _GHS_PICTOGRAMS.get(k, "Unknown")
                            for k in sorted(detected_pictograms.keys())
                        },
                    },
                )
            )

            # Check mutual exclusion rules
            for superior, inferior, reason in _MUTUAL_EXCLUSIONS:
                if superior in detected_pictograms and inferior in detected_pictograms:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_GHS_002",
                            severity=Severity.ERROR,
                            message=(
                                f"GHS mutual exclusion violation: {superior} and "
                                f"{inferior} both present. {reason}."
                            ),
                            details={
                                "superior": superior,
                                "inferior": inferior,
                                "reason": reason,
                                "regulation": "EU Regulation 1272/2008",
                            },
                        )
                    )

            # Check pictogram sizing
            self._check_pictogram_sizes(
                document, events, detected_pictograms, min_pictogram_mm, findings
            )
        else:
            # Gate 1 (WS-3): skip the whole rule on food / supplement /
            # cosmetic products -- they're not CLP-regulated.
            # Gate 2 (WS-4): signal words landing inside a Prop 65
            # proximity window are cautionary, not CLP hazard labels,
            # so filter them out before deciding if anything remains.
            if is_ghs_applicable(ai_config):
                non_prop65 = self._non_prop65_signal_words(all_text)
                if h_statements or non_prop65:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_GHS_003",
                            severity=Severity.ERROR,
                            message=(
                                "H-statements or signal words detected but no GHS "
                                "pictograms found. CLP requires pictograms when "
                                "hazard statements are present."
                            ),
                            details={
                                "h_statements": h_statements,
                                "signal_words": non_prop65,
                                "regulation": "EU Regulation 1272/2008 Article 19",
                            },
                        )
                    )

        # Report H-statements
        if h_statements:
            findings.append(
                self._make_finding(
                    inspection_id="AI_GHS_004",
                    severity=Severity.ADVISORY,
                    message=f"H-statements detected: {', '.join(h_statements)}",
                    details={"h_statements": h_statements},
                )
            )

        # Report P-statements
        if p_statements:
            findings.append(
                self._make_finding(
                    inspection_id="AI_GHS_005",
                    severity=Severity.ADVISORY,
                    message=f"P-statements detected: {', '.join(p_statements)}",
                    details={"p_statements": p_statements},
                )
            )

        # Report signal words
        if signal_words:
            if len(signal_words) > 1:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_GHS_006",
                        severity=Severity.ERROR,
                        message=(
                            "Multiple signal words detected: "
                            f"{', '.join(signal_words)}. "
                            "CLP allows only one signal word (the more severe)."
                        ),
                        details={
                            "signal_words": signal_words,
                            "regulation": "EU Regulation 1272/2008 Article 20",
                        },
                    )
                )
            else:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_GHS_007",
                        severity=Severity.ADVISORY,
                        message=f"Signal word detected: {signal_words[0]}",
                        details={"signal_word": signal_words[0]},
                    )
                )

        return findings

    @staticmethod
    def _detect_pictograms(  # skipcq: PY-R1000
        document: SemanticDocument,
        all_text: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Detect GHS pictograms via name matching in resources and text.

        Looks for image XObject names and text references containing GHS
        pictogram identifiers (GHS01-GHS09).
        """
        found: dict[str, list[dict[str, Any]]] = {}

        # Check image names in document resources
        for page in document.pages:
            for image in page.images:
                for ghs_id in _GHS_PICTOGRAMS:
                    if ghs_id.lower() in image.name.lower():
                        if ghs_id not in found:
                            found[ghs_id] = []
                        found[ghs_id].append(
                            {
                                "source": "image_name",
                                "name": image.name,
                                "page_num": page.page_num,
                                "width_px": image.width,
                                "height_px": image.height,
                            }
                        )

            # Check resource names
            resources = page.resources
            if isinstance(resources, dict):
                xobjects = resources.get("XObject", {})
                if isinstance(xobjects, dict):
                    for xobj_name in xobjects:
                        for ghs_id in _GHS_PICTOGRAMS:
                            if ghs_id.lower() in str(xobj_name).lower():
                                if ghs_id not in found:
                                    found[ghs_id] = []
                                found[ghs_id].append(
                                    {
                                        "source": "xobject_name",
                                        "name": str(xobj_name),
                                        "page_num": page.page_num,
                                    }
                                )

        # Check text content for GHS references
        for ghs_id in _GHS_PICTOGRAMS:
            if re.search(r"\b" + re.escape(ghs_id) + r"\b", all_text, re.IGNORECASE):
                if ghs_id not in found:
                    found[ghs_id] = []
                found[ghs_id].append({"source": "text_reference"})

        return found

    @staticmethod
    def _detect_h_statements(text: str) -> list[str]:
        """Find H-statements (H2xx, H3xx, H4xx) in document text."""
        matches = _H_STATEMENT_PATTERN.findall(text)
        # Deduplicate while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for m in matches:
            normalized = m.strip().upper()
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    @staticmethod
    def _detect_p_statements(text: str) -> list[str]:
        """Find P-statements (P1xx-P5xx) in document text."""
        matches = _P_STATEMENT_PATTERN.findall(text)
        seen: set[str] = set()
        result: list[str] = []
        for m in matches:
            normalized = m.strip().upper()
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    @staticmethod
    def _detect_signal_words(text: str) -> list[str]:
        """Detect GHS signal words (Danger, Warning)."""
        found: list[str] = []
        for word in _SIGNAL_WORDS:
            if re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE):
                found.append(word)
        return found

    @staticmethod
    def _non_prop65_signal_words(text: str) -> list[str]:
        """Return signal words whose match is NOT inside a Prop 65
        proximity window.

        The 2026-04-23 Opus audit flagged one false-positive
        ``AI_GHS_003`` where "WARNING: This product can expose you
        to ... known to the State of California to cause cancer"
        on a dietary supplement was treated as a CLP hazard
        statement. Rather than suppress the whole match, we check
        each occurrence individually -- a product page carrying
        both a real H-statement block AND a Prop 65 disclaimer
        should still flag the CLP portion.
        """
        lowered = text.lower()
        # Map anchor->list of (start, end) spans.
        anchor_spans: list[tuple[int, int]] = []
        for anchor in _PROP65_ANCHORS:
            start = 0
            while True:
                idx = lowered.find(anchor, start)
                if idx < 0:
                    break
                anchor_spans.append((idx, idx + len(anchor)))
                start = idx + len(anchor)

        def _near_anchor(pos: int) -> bool:
            for a_start, a_end in anchor_spans:
                if (
                    abs(pos - a_start) <= _PROP65_WINDOW_CHARS
                    or abs(pos - a_end) <= _PROP65_WINDOW_CHARS
                ):
                    return True
            return False

        out: list[str] = []
        for word in _SIGNAL_WORDS:
            pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
            any_non_prop65 = False
            for m in pattern.finditer(text):
                if not _near_anchor(m.start()):
                    any_non_prop65 = True
                    break
            if any_non_prop65:
                out.append(word)
        return out

    def _check_pictogram_sizes(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        detected: dict[str, list[dict[str, Any]]],
        min_side_mm: float,
        findings: list[Finding],
    ) -> None:
        """Check that GHS pictograms meet minimum sizing requirements."""
        from lintpdf.semantic.events import ImagePlacedEvent

        for ghs_id, occurrences in detected.items():
            for occ in occurrences:
                if occ.get("source") != "image_name":
                    continue

                image_name = occ.get("name", "")
                page_num = occ.get("page_num", 0)

                # Find the corresponding ImagePlacedEvent for sizing
                for event in events:
                    if not isinstance(event, ImagePlacedEvent):
                        continue
                    if event.image_name != image_name or event.page_num != page_num:
                        continue

                    # Compute rendered size in mm from CTM
                    # CTM maps 1x1 image space to page space (points)
                    # Width in points = sqrt(a² + c²), Height = sqrt(b² + d²)
                    ctm = event.ctm
                    width_pt = math.sqrt(ctm.a**2 + ctm.c**2) if hasattr(ctm, "a") else 0
                    height_pt = math.sqrt(ctm.b**2 + ctm.d**2) if hasattr(ctm, "b") else 0

                    width_mm = width_pt * 0.3528
                    height_mm = height_pt * 0.3528
                    min_side = min(width_mm, height_mm)

                    if 0 < min_side < min_side_mm:
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_GHS_008",
                                severity=Severity.WARNING,
                                message=(
                                    f"GHS pictogram {ghs_id} ({_GHS_PICTOGRAMS[ghs_id]}) "
                                    f"is {min_side:.1f}mm, below minimum "
                                    f"{min_side_mm:.1f}mm for package capacity"
                                ),
                                page_num=page_num,
                                details={
                                    "pictogram": ghs_id,
                                    "rendered_width_mm": round(width_mm, 2),
                                    "rendered_height_mm": round(height_mm, 2),
                                    "min_side_mm": round(min_side, 2),
                                    "required_min_mm": min_side_mm,
                                    "regulation": "EU Regulation 1272/2008 Article 31",
                                },
                                object_type="image",
                                object_id=image_name,
                            )
                        )
                    break
