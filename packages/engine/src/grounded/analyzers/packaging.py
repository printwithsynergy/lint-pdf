"""PackagingAnalyzer — packaging-specific geometry and structure checks.

Validates PDF documents for packaging print readiness: dieline detection,
panel identification, safe zones, substrate compatibility.

Check IDs:
    GRD_PKG_001 — Dieline layer detected
    GRD_PKG_002 — Missing dieline layer
    GRD_PKG_003 — Dieline on wrong layer
    GRD_PKG_004 — Content outside dieline boundary
    GRD_PKG_005 — Insufficient safe zone from dieline
    GRD_PKG_006 — Bleed insufficient for packaging
    GRD_PKG_007 — Multiple panel sizes detected
    GRD_PKG_008 — Crossover alignment check
    GRD_PKG_009 — Varnish/coating layer detected
    GRD_PKG_010 — White ink separation detected
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

# Layer name sets for detection
_DIELINE_LAYER_NAMES = {"Dieline", "Die", "CutLine", "Cut", "Stanz"}
_COATING_LAYER_NAMES = {"Varnish", "Coating", "Spot UV", "Foil"}
_WHITE_LAYER_NAMES = {"White"}

# Conversion factor: 1 mm = 2.834645669 pt
_MM_TO_PTS = 2.834645669


class PackagingAnalyzer(BaseAnalyzer):
    """Analyzer for packaging-specific geometry and structure checks.

    Validates dieline detection, safe zones, bleed, coating/varnish layers,
    and white ink separations relevant to packaging workflows.

    Args:
        min_safe_zone_mm: Minimum safe zone distance from dieline/trim edge
            in millimeters (default 3.0).
        min_bleed_mm: Minimum bleed distance for packaging in millimeters
            (default 5.0 — packaging typically needs more bleed than flat print).
    """

    def __init__(
        self,
        *,
        min_safe_zone_mm: float = 3.0,
        min_bleed_mm: float = 5.0,
    ) -> None:
        self.min_safe_zone_mm = min_safe_zone_mm
        self.min_bleed_mm = min_bleed_mm
        self._min_safe_zone_pts = min_safe_zone_mm * _MM_TO_PTS
        self._min_bleed_pts = min_bleed_mm * _MM_TO_PTS

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document for packaging-specific issues."""
        findings: list[Finding] = []

        # Extract OCProperties (optional content / layer info) from catalog
        oc_properties = document.catalog.get("OCProperties", {})
        oc_groups = self._extract_oc_groups(oc_properties)
        layer_names = {name.strip() for name in oc_groups.values()}

        # --- GRD_PKG_001 / GRD_PKG_002: Dieline layer detection ---
        dieline_layers = self._find_matching_layers(layer_names, _DIELINE_LAYER_NAMES)
        if dieline_layers:
            findings.append(
                Finding(
                    inspection_id="GRD_PKG_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Dieline layer detected: {', '.join(sorted(dieline_layers))}"
                    ),
                    details={"dieline_layers": sorted(dieline_layers)},
                    category="packaging",
                )
            )
        else:
            findings.append(
                Finding(
                    inspection_id="GRD_PKG_002",
                    severity=Severity.WARNING,
                    message=(
                        "No dieline layer found. Packaging artwork should include a "
                        "dedicated dieline layer (expected names: "
                        + ", ".join(sorted(_DIELINE_LAYER_NAMES))
                        + ")"
                    ),
                    details={"expected_names": sorted(_DIELINE_LAYER_NAMES)},
                    category="packaging",
                )
            )

        # --- GRD_PKG_003: Dieline on wrong layer ---
        # Check if any dieline layer is marked as non-printing in OCProperties
        if dieline_layers:
            non_printing_dielines = self._find_non_printing_layers(
                oc_properties, dieline_layers
            )
            for layer_name in non_printing_dielines:
                findings.append(
                    Finding(
                        inspection_id="GRD_PKG_003",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Dieline layer '{layer_name}' is on a non-printing layer. "
                            "Verify this is intentional for your packaging workflow."
                        ),
                        details={"layer_name": layer_name},
                        category="packaging",
                    )
                )

        # --- GRD_PKG_004: Content outside dieline boundary ---
        # Approximate: check for content positioned significantly outside trim box
        from grounded.semantic.events import PathPaintingEvent, TextRenderedEvent

        for page in document.pages:
            trim_box = page.trim_box
            if trim_box is None:
                continue

            # Check events on this page
            outside_margin_pts = 20.0  # ~7mm outside trim = likely outside dieline
            for event in events:
                if event.page_num != page.page_num:
                    continue
                if not isinstance(event, (PathPaintingEvent, TextRenderedEvent)):
                    continue
                bbox = event.bbox
                if bbox is None:
                    continue
                bx0, by0, bx1, by1 = bbox
                significantly_outside = (
                    bx1 < trim_box.x0 - outside_margin_pts
                    or bx0 > trim_box.x1 + outside_margin_pts
                    or by1 < trim_box.y0 - outside_margin_pts
                    or by0 > trim_box.y1 + outside_margin_pts
                )
                if significantly_outside:
                    findings.append(
                        Finding(
                            inspection_id="GRD_PKG_004",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Content on page {page.page_num} is positioned "
                                "significantly outside the trim box — may be "
                                "outside the dieline boundary"
                            ),
                            page_num=page.page_num,
                            details={
                                "content_bbox": list(bbox),
                                "trim_box": trim_box.as_tuple(),
                            },
                            bbox=bbox,
                            category="packaging",
                        )
                    )
                    # Only report once per page
                    break

        # --- GRD_PKG_005: Insufficient safe zone from dieline/trim edge ---
        for page in document.pages:
            trim_box = page.trim_box
            if trim_box is None:
                continue
            for event in events:
                if event.page_num != page.page_num:
                    continue
                if not isinstance(event, (PathPaintingEvent, TextRenderedEvent)):
                    continue
                bbox = event.bbox
                if bbox is None:
                    continue
                bx0, by0, bx1, by1 = bbox
                margin = self._min_safe_zone_pts
                in_safety = (
                    bx0 < trim_box.x0 + margin
                    or by0 < trim_box.y0 + margin
                    or bx1 > trim_box.x1 - margin
                    or by1 > trim_box.y1 - margin
                )
                # Only flag if content is inside the trim box
                in_trim = (
                    bx1 > trim_box.x0
                    and bx0 < trim_box.x1
                    and by1 > trim_box.y0
                    and by0 < trim_box.y1
                )
                if in_safety and in_trim:
                    findings.append(
                        Finding(
                            inspection_id="GRD_PKG_005",
                            severity=Severity.WARNING,
                            message=(
                                f"Content within {self.min_safe_zone_mm:.1f}mm "
                                f"packaging safe zone on page {page.page_num}"
                            ),
                            page_num=page.page_num,
                            details={
                                "content_bbox": list(bbox),
                                "trim_box": trim_box.as_tuple(),
                                "min_safe_zone_mm": self.min_safe_zone_mm,
                            },
                            bbox=bbox,
                            category="packaging",
                        )
                    )
                    # Only report once per page
                    break

        # --- GRD_PKG_006: Bleed insufficient for packaging ---
        for page in document.pages:
            trim_box = page.trim_box
            bleed_box = page.bleed_box
            if trim_box is None or bleed_box is None:
                continue

            bleed_left = trim_box.x0 - bleed_box.x0
            bleed_right = bleed_box.x1 - trim_box.x1
            bleed_bottom = trim_box.y0 - bleed_box.y0
            bleed_top = bleed_box.y1 - trim_box.y1

            bleeds = {
                "left": bleed_left,
                "right": bleed_right,
                "bottom": bleed_bottom,
                "top": bleed_top,
            }
            inadequate = {
                side: dist
                for side, dist in bleeds.items()
                if dist < self._min_bleed_pts
            }

            if inadequate:
                findings.append(
                    Finding(
                        inspection_id="GRD_PKG_006",
                        severity=Severity.WARNING,
                        message=(
                            f"Packaging bleed insufficient on page {page.page_num}: "
                            + ", ".join(
                                f"{side} {dist:.1f}pt"
                                for side, dist in inadequate.items()
                            )
                            + f" (minimum {self._min_bleed_pts:.1f}pt / "
                            f"{self.min_bleed_mm:.1f}mm for packaging)"
                        ),
                        page_num=page.page_num,
                        details={
                            "bleeds": bleeds,
                            "inadequate_sides": inadequate,
                            "min_bleed_pts": self._min_bleed_pts,
                            "min_bleed_mm": self.min_bleed_mm,
                        },
                        category="packaging",
                    )
                )

        # --- GRD_PKG_007: Multiple panel sizes ---
        if len(document.pages) > 1:
            page_sizes: dict[tuple[float, float], list[int]] = {}
            for page in document.pages:
                ref_box = page.trim_box or page.media_box
                width = round(ref_box.x1 - ref_box.x0, 0)
                height = round(ref_box.y1 - ref_box.y0, 0)
                size_key = (width, height)
                page_sizes.setdefault(size_key, []).append(page.page_num)
            if len(page_sizes) > 1:
                unique_sizes = [
                    {"width_pt": w, "height_pt": h, "pages": pages}
                    for (w, h), pages in page_sizes.items()
                ]
                findings.append(
                    Finding(
                        inspection_id="GRD_PKG_007",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Multiple distinct panel sizes detected across "
                            f"{len(document.pages)} pages ({len(page_sizes)} "
                            f"unique sizes) — common in multi-panel packaging"
                        ),
                        details={"unique_sizes": unique_sizes},
                        category="packaging",
                    )
                )

        # --- GRD_PKG_008: Crossover alignment advisory ---
        if len(document.pages) > 1:
            findings.append(
                Finding(
                    inspection_id="GRD_PKG_008",
                    severity=Severity.ADVISORY,
                    message=(
                        "Multi-page packaging layout detected. Verify crossover "
                        "alignment between adjacent panels to ensure seamless "
                        "print across fold/cut lines."
                    ),
                    details={"page_count": document.page_count},
                    category="packaging",
                )
            )

        # --- GRD_PKG_009: Varnish/coating layer detected ---
        coating_layers = self._find_matching_layers(layer_names, _COATING_LAYER_NAMES)
        if coating_layers:
            findings.append(
                Finding(
                    inspection_id="GRD_PKG_009",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Varnish/coating layer detected: "
                        f"{', '.join(sorted(coating_layers))}"
                    ),
                    details={"coating_layers": sorted(coating_layers)},
                    category="packaging",
                )
            )

        # --- GRD_PKG_010: White ink separation detected ---
        white_detected = False
        # Check layers for "White"
        white_layers = self._find_matching_layers(layer_names, _WHITE_LAYER_NAMES)
        if white_layers:
            white_detected = True

        # Check color spaces for Separation with "White" colorant
        if not white_detected:
            for page in document.pages:
                for _cs_name, cs in page.color_spaces.items():
                    if (
                        cs.cs_type == "Separation"
                        and "White" in cs.colorant_names
                    ):
                        white_detected = True
                        break
                if white_detected:
                    break

        if white_detected:
            findings.append(
                Finding(
                    inspection_id="GRD_PKG_010",
                    severity=Severity.ADVISORY,
                    message=(
                        "White ink separation detected. Ensure white ink layer "
                        "is correctly configured for your substrate and print process."
                    ),
                    details={
                        "white_layers": sorted(white_layers) if white_layers else [],
                        "found_in_separations": not bool(white_layers),
                    },
                    category="packaging",
                )
            )

        return findings

    @staticmethod
    def _extract_oc_groups(oc_properties: dict) -> dict[str, str]:
        """Extract optional content group names from OCProperties.

        Returns a mapping of group reference/index to layer name.
        """
        groups: dict[str, str] = {}
        ocgs = oc_properties.get("OCGs", [])
        for i, ocg in enumerate(ocgs):
            if isinstance(ocg, dict):
                name = ocg.get("Name", "")
                if name:
                    groups[str(i)] = str(name)
            elif isinstance(ocg, str):
                groups[str(i)] = ocg
        return groups

    @staticmethod
    def _find_matching_layers(
        layer_names: set[str], target_names: set[str]
    ) -> set[str]:
        """Find layers whose names match any target name (case-insensitive)."""
        target_lower = {t.lower() for t in target_names}
        return {
            name
            for name in layer_names
            if name.lower() in target_lower
        }

    @staticmethod
    def _find_non_printing_layers(
        oc_properties: dict, target_layers: set[str]
    ) -> list[str]:
        """Find layers from target set that are marked as non-printing.

        Checks the Usage dict of each OCG for a Print entry with
        PrintState=OFF, or checks the AS (auto-state) array.
        """
        non_printing: list[str] = []
        ocgs = oc_properties.get("OCGs", [])
        for ocg in ocgs:
            if not isinstance(ocg, dict):
                continue
            name = str(ocg.get("Name", ""))
            if name not in target_layers:
                continue
            usage = ocg.get("Usage", {})
            if isinstance(usage, dict):
                print_usage = usage.get("Print", {})
                if isinstance(print_usage, dict):
                    print_state = print_usage.get("PrintState", "ON")
                    if str(print_state).upper() == "OFF":
                        non_printing.append(name)
        return non_printing
