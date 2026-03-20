"""ColorAnalyzer — TAC calculation, prohibited spaces, ICC validation.

Processes ColorChangedEvent and PathPaintingEvent events plus
SemanticDocument color space data to detect color-related preflight issues.

TAC (Total Area Coverage) = sum of CMYK component values as percentages.
For example, C=100% M=80% Y=70% K=30% = TAC 280%.

Check IDs:
    GRD_COLOR_001 — Prohibited color space used
    GRD_COLOR_002 — DeviceRGB used without ICC profile
    GRD_COLOR_003 — Spot color with no backing color space
    GRD_COLOR_004 — TAC exceeds limit
    GRD_COLOR_005 — Registration color (all CMYK at 100%)
    GRD_COLOR_006 — Output intent missing from document
    GRD_COLOR_007 — Spot color detected (informational catalog)
    GRD_COLOR_008 — Rich black on small text (<12pt, >1 ink)
    GRD_COLOR_009 — 100% K not overprinting (knockout black)
    GRD_COLOR_010 — Pure K-only on large fill area
    GRD_COLOR_011 — Spot color name conflict (same name, different alternate)
    GRD_COLOR_012 — Minimum printing dot below threshold (scum dot risk)
    GRD_COLOR_013 — Gamut warning / out-of-gamut color (RGB in CMYK workflow)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import (
        ColorChangedEvent,
        ContentStreamEvent,
        PathPaintingEvent,
        TextRenderedEvent,
    )
    from grounded.semantic.model import SemanticDocument

# Default TAC limits by print method
DEFAULT_TAC_LIMIT = 300.0  # Conservative default
TAC_LIMIT_SHEETFED = 330.0
TAC_LIMIT_WEB = 260.0

# Color spaces prohibited in PDF/X-4
_PROHIBITED_SPACES = frozenset({"CalGray", "CalRGB"})


class ColorAnalyzer(BaseAnalyzer):
    """Analyzer for color space usage and TAC compliance.

    Args:
        tac_limit: Maximum allowed TAC percentage (default 300).
    """

    def __init__(self, tac_limit: float = DEFAULT_TAC_LIMIT) -> None:
        self.tac_limit = tac_limit

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze color usage across the document."""
        from grounded.semantic.events import (
            ColorChangedEvent,
            OverprintChangedEvent,
            PathPaintingEvent,
            TextRenderedEvent,
        )

        findings: list[Finding] = []
        seen_spaces: set[tuple[int, str]] = set()
        overprint_non_stroking = False

        for event in events:
            if isinstance(event, OverprintChangedEvent):
                if event.overprint_non_stroking is not None:
                    overprint_non_stroking = event.overprint_non_stroking
            elif isinstance(event, ColorChangedEvent):
                findings.extend(self._check_color_event(event, seen_spaces))
            elif isinstance(event, PathPaintingEvent):
                findings.extend(self._check_path_tac(event))
                findings.extend(self._check_registration_color(event))
                findings.extend(self._check_knockout_black(event, overprint_non_stroking))
                findings.extend(self._check_pure_k_fill(event))
            elif isinstance(event, TextRenderedEvent):
                findings.extend(self._check_rich_black_text(event))

        # GRD_COLOR_006: Output intent missing
        if not document.output_intents:
            findings.append(
                Finding(
                    inspection_id="GRD_COLOR_006",
                    severity=Severity.SQUALL,
                    message="No Output Intent defined in document",
                    iso_clause="ISO 15930-7:2010 6.2.3",
                )
            )

        # GRD_COLOR_011: Spot color name conflicts
        findings.extend(self._check_spot_color_conflicts(document))

        # GRD_COLOR_012: Minimum printing dot below threshold
        findings.extend(self._check_minimum_dot(document))

        # GRD_COLOR_013: Gamut warning — RGB values in CMYK workflow
        findings.extend(self._check_gamut_warning(document))

        # Check page-level color spaces from SemanticDocument
        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                key = (page.page_num, cs.cs_type)
                if key not in seen_spaces:
                    seen_spaces.add(key)
                    if cs.cs_type in _PROHIBITED_SPACES:
                        findings.append(
                            Finding(
                                inspection_id="GRD_COLOR_001",
                                severity=Severity.AGROUND,
                                message=(
                                    f"Prohibited color space '{cs.cs_type}' "
                                    f"defined in page {page.page_num} resources"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                    "color_space_type": cs.cs_type,
                                },
                                iso_clause="ISO 15930-7:2010 6.2.4",
                            )
                        )

                    # GRD_COLOR_002: DeviceRGB without ICC
                    if cs.cs_type == "DeviceRGB" and cs.icc_profile_ref is None:
                        findings.append(
                            Finding(
                                inspection_id="GRD_COLOR_002",
                                severity=Severity.SQUALL,
                                message=(
                                    f"DeviceRGB color space '{cs_name}' "
                                    f"used without ICC profile on page {page.page_num}"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                },
                                iso_clause="ISO 15930-7:2010 6.2.3",
                            )
                        )

                    # GRD_COLOR_003: Separation without alternate
                    if cs.cs_type in ("Separation", "DeviceN") and cs.alternate is None:
                        findings.append(
                            Finding(
                                inspection_id="GRD_COLOR_003",
                                severity=Severity.SQUALL,
                                message=(
                                    f"Spot color '{cs_name}' ({cs.cs_type}) "
                                    f"has no alternate color space on page {page.page_num}"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                    "color_space_type": cs.cs_type,
                                },
                                iso_clause="ISO 32000-2:2020 8.6.6.4",
                            )
                        )

                    # GRD_COLOR_007: Spot color catalog
                    if cs.cs_type in ("Separation", "DeviceN") and cs.colorant_names:
                        for colorant in cs.colorant_names:
                            if colorant and colorant not in ("All", "None"):
                                findings.append(
                                    Finding(
                                        inspection_id="GRD_COLOR_007",
                                        severity=Severity.ADVISORY,
                                        message=(
                                            f"Spot color '{colorant}' used on page {page.page_num}"
                                        ),
                                        page_num=page.page_num,
                                        details={
                                            "colorant_name": colorant,
                                            "color_space_name": cs_name,
                                            "color_space_type": cs.cs_type,
                                        },
                                    )
                                )

        return findings

    @staticmethod
    def _check_color_event(
        event: ColorChangedEvent,
        seen_spaces: set[tuple[int, str]],
    ) -> list[Finding]:
        """Check a color change event for prohibited spaces."""
        findings: list[Finding] = []
        key = (event.page_num, event.color_space)

        if key not in seen_spaces:
            seen_spaces.add(key)
            if event.color_space in _PROHIBITED_SPACES:
                findings.append(
                    Finding(
                        inspection_id="GRD_COLOR_001",
                        severity=Severity.AGROUND,
                        message=(
                            f"Prohibited color space '{event.color_space}' "
                            f"used on page {event.page_num}"
                        ),
                        page_num=event.page_num,
                        details={
                            "color_space": event.color_space,
                            "stroking": event.stroking,
                        },
                        iso_clause="ISO 15930-7:2010 6.2.4",
                    )
                )

        return findings

    def _check_path_tac(self, event: PathPaintingEvent) -> list[Finding]:
        """Check TAC for CMYK colors in path painting events."""
        findings: list[Finding] = []

        if event.fill and event.fill_color_space == "DeviceCMYK":
            tac = self._calculate_tac(event.fill_color_values)
            if tac > self.tac_limit:
                findings.append(
                    Finding(
                        inspection_id="GRD_COLOR_004",
                        severity=Severity.SQUALL,
                        message=(
                            f"TAC {tac:.0f}% exceeds limit {self.tac_limit:.0f}% "
                            f"(fill color on page {event.page_num})"
                        ),
                        page_num=event.page_num,
                        details={
                            "tac": tac,
                            "tac_limit": self.tac_limit,
                            "color_values": list(event.fill_color_values),
                            "stroking": False,
                        },
                        iso_clause="GWG 2022 6.3",
                    )
                )

        if event.stroke and event.stroke_color_space == "DeviceCMYK":
            tac = self._calculate_tac(event.stroke_color_values)
            if tac > self.tac_limit:
                findings.append(
                    Finding(
                        inspection_id="GRD_COLOR_004",
                        severity=Severity.SQUALL,
                        message=(
                            f"TAC {tac:.0f}% exceeds limit {self.tac_limit:.0f}% "
                            f"(stroke color on page {event.page_num})"
                        ),
                        page_num=event.page_num,
                        details={
                            "tac": tac,
                            "tac_limit": self.tac_limit,
                            "color_values": list(event.stroke_color_values),
                            "stroking": True,
                        },
                        iso_clause="GWG 2022 6.3",
                    )
                )

        return findings

    @staticmethod
    def _check_registration_color(event: PathPaintingEvent) -> list[Finding]:
        """Check for registration color (all CMYK components at 100%).

        GRD_COLOR_005: Registration color is usually an error unless
        intentionally used for registration marks.
        """
        findings: list[Finding] = []

        def _is_registration(cs: str, vals: tuple[float, ...]) -> bool:
            if cs != "DeviceCMYK" or len(vals) != 4:
                return False
            return all(abs(v - 1.0) < 0.01 for v in vals)

        if event.fill and _is_registration(event.fill_color_space, event.fill_color_values):
            findings.append(
                Finding(
                    inspection_id="GRD_COLOR_005",
                    severity=Severity.SQUALL,
                    message=(
                        f"Registration color (100% all CMYK) used as fill on page {event.page_num}"
                    ),
                    page_num=event.page_num,
                    details={"color_values": list(event.fill_color_values), "stroking": False},
                    object_type="path",
                )
            )

        if event.stroke and _is_registration(event.stroke_color_space, event.stroke_color_values):
            findings.append(
                Finding(
                    inspection_id="GRD_COLOR_005",
                    severity=Severity.SQUALL,
                    message=(
                        f"Registration color (100% all CMYK) used as stroke "
                        f"on page {event.page_num}"
                    ),
                    page_num=event.page_num,
                    details={"color_values": list(event.stroke_color_values), "stroking": True},
                    object_type="path",
                )
            )

        return findings

    @staticmethod
    def _check_rich_black_text(event: TextRenderedEvent) -> list[Finding]:
        """Check for rich black on small text (GRD_COLOR_008).

        Rich black = CMYK fill with >1 non-zero ink on text <12pt.
        """
        import math

        findings: list[Finding] = []
        if event.color_space != "DeviceCMYK" or len(event.color_values) != 4:
            return findings

        # Calculate effective size
        tm_scale_y = math.sqrt(event.text_matrix.b**2 + event.text_matrix.d**2)
        ctm_scale_y = math.sqrt(event.ctm.b**2 + event.ctm.d**2)
        effective_size = event.font_size * tm_scale_y * ctm_scale_y

        if effective_size >= 12.0 or effective_size <= 0:
            return findings

        # Count non-zero ink channels
        non_zero = sum(1 for v in event.color_values if v > 0.01)
        if non_zero > 1:
            findings.append(
                Finding(
                    inspection_id="GRD_COLOR_008",
                    severity=Severity.SQUALL,
                    message=(
                        f"Rich black on small text ({effective_size:.1f}pt) "
                        f"on page {event.page_num} "
                        f"({non_zero} ink channels — risk of misregistration)"
                    ),
                    page_num=event.page_num,
                    details={
                        "font_name": event.font_name,
                        "effective_size": effective_size,
                        "color_values": list(event.color_values),
                        "non_zero_inks": non_zero,
                    },
                    object_type="text",
                )
            )
        return findings

    @staticmethod
    def _check_knockout_black(
        event: PathPaintingEvent, overprint_non_stroking: bool
    ) -> list[Finding]:
        """Check for 100% K fill without overprint (GRD_COLOR_009).

        Knockout black = 0/0/0/100% CMYK fill with overprint OFF.
        """
        findings: list[Finding] = []
        if not event.fill or event.fill_color_space != "DeviceCMYK":
            return findings
        vals = event.fill_color_values
        if len(vals) != 4:
            return findings
        # Check if pure 100% K without overprint
        is_pure_k = abs(vals[3] - 1.0) < 0.01 and all(abs(v) < 0.01 for v in vals[:3])
        if is_pure_k and not overprint_non_stroking:
            findings.append(
                Finding(
                    inspection_id="GRD_COLOR_009",
                    severity=Severity.ADVISORY,
                    message=(
                        f"100% K fill without overprint on page {event.page_num} "
                        f"(knockout black may cause white gaps)"
                    ),
                    page_num=event.page_num,
                    details={
                        "color_values": list(vals),
                        "overprint": False,
                    },
                    object_type="path",
                )
            )
        return findings

    @staticmethod
    def _check_pure_k_fill(event: PathPaintingEvent) -> list[Finding]:
        """Check for pure K-only on fill (GRD_COLOR_010).

        Advisory: large fills in K-only may appear washed out compared to rich black.
        Only flags fills (not strokes) as these are the visible ones.
        """
        findings: list[Finding] = []
        if not event.fill or event.fill_color_space != "DeviceCMYK":
            return findings
        vals = event.fill_color_values
        if len(vals) != 4:
            return findings
        # Pure K-only: K > 50% and C/M/Y all near 0
        if vals[3] > 0.50 and all(abs(v) < 0.01 for v in vals[:3]):
            findings.append(
                Finding(
                    inspection_id="GRD_COLOR_010",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Pure K-only fill ({vals[3] * 100:.0f}% K) on page {event.page_num} "
                        f"(may appear washed out on large areas)"
                    ),
                    page_num=event.page_num,
                    details={
                        "color_values": list(vals),
                        "k_percent": vals[3] * 100.0,
                    },
                    object_type="path",
                )
            )
        return findings

    @staticmethod
    def _check_spot_color_conflicts(
        document: SemanticDocument,
    ) -> list[Finding]:  # skipcq: PY-R1000
        """Check for spot color name conflicts (GRD_COLOR_011).

        Same colorant name defined with different alternates on different pages.
        """
        findings: list[Finding] = []
        # Collect: colorant_name -> set of alternates
        colorant_alternates: dict[str, set[str | None]] = {}
        colorant_pages: dict[str, list[int]] = {}

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type in ("Separation", "DeviceN") and cs.colorant_names:
                    for colorant in cs.colorant_names:
                        if colorant in ("All", "None"):
                            continue
                        alt = cs.alternate if hasattr(cs, "alternate") else None
                        if colorant not in colorant_alternates:
                            colorant_alternates[colorant] = set()
                            colorant_pages[colorant] = []
                        colorant_alternates[colorant].add(str(alt) if alt is not None else None)
                        if page.page_num not in colorant_pages[colorant]:
                            colorant_pages[colorant].append(page.page_num)

        for colorant, alternates in colorant_alternates.items():
            if len(alternates) > 1:
                findings.append(
                    Finding(
                        inspection_id="GRD_COLOR_011",
                        severity=Severity.SQUALL,
                        message=(
                            f"Spot color '{colorant}' has conflicting alternate "
                            f"color spaces across pages {colorant_pages[colorant]}"
                        ),
                        details={
                            "colorant_name": colorant,
                            "alternate_count": len(alternates),
                            "pages": colorant_pages[colorant],
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_minimum_dot(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
        """Check for separation tint values below 2% (GRD_COLOR_012).

        When a Separation or DeviceN color space has tint values below 2%,
        there is a risk of scum dots in flexographic printing. Looks at
        color space definitions in page resources for tint transform hints.
        """
        findings: list[Finding] = []
        min_dot_threshold = 0.02  # 2%

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                # Check the resources for tint values associated with this space
                resources = page.resources
                color_space_res = resources.get("/ColorSpace", {})
                if not isinstance(color_space_res, dict):
                    continue
                cs_array = color_space_res.get(cs_name)
                if not isinstance(cs_array, list) or len(cs_array) < 4:
                    continue
                # The tint transform is the last element; we look for sampled
                # function dictionaries that contain low values
                tint_fn = cs_array[-1]
                if isinstance(tint_fn, dict):
                    # Check /Range or /C0 for near-zero start values
                    c0 = tint_fn.get("/C0", [])
                    if isinstance(c0, list):
                        for val in c0:
                            try:
                                fval = float(val)
                            except (ValueError, TypeError):
                                continue
                            if 0 < fval < min_dot_threshold:
                                colorant = cs.colorant_names[0] if cs.colorant_names else cs_name
                                findings.append(
                                    Finding(
                                        inspection_id="GRD_COLOR_012",
                                        severity=Severity.SQUALL,
                                        message=(
                                            f"Separation '{colorant}' has tint value "
                                            f"{fval * 100:.1f}% below 2% minimum dot "
                                            f"on page {page.page_num} (scum dot risk for flexo)"
                                        ),
                                        page_num=page.page_num,
                                        details={
                                            "colorant_name": colorant,
                                            "tint_value": fval,
                                            "threshold": min_dot_threshold,
                                        },
                                    )
                                )
                                return findings  # One finding is enough
        return findings

    @staticmethod
    def _check_gamut_warning(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
        """Check for RGB color spaces used in a CMYK workflow (GRD_COLOR_013).

        Flags when DeviceRGB or CalRGB color spaces are found on pages
        but the document has a CMYK output intent, indicating potential
        out-of-gamut colors.
        """
        findings: list[Finding] = []

        # Determine if document has a CMYK output intent
        is_cmyk_workflow = False
        for oi in document.output_intents:
            # Check output condition identifier or dest profile
            oi_subtype = oi.get("/S", "")
            dest_cs = oi.get("/DestOutputProfileRef", "")
            info = oi.get("/Info", "")
            condition = oi.get("/OutputConditionIdentifier", "")
            # Heuristic: if any output intent mentions CMYK-related terms
            for val in (str(dest_cs), str(info), str(condition), str(oi_subtype)):
                if "CMYK" in val.upper() or "FOGRA" in val.upper() or "SWOP" in val.upper():
                    is_cmyk_workflow = True
                    break
            if is_cmyk_workflow:
                break

        if not is_cmyk_workflow:
            return findings

        # Check for RGB usage on pages
        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type in ("DeviceRGB", "CalRGB"):
                    findings.append(
                        Finding(
                            inspection_id="GRD_COLOR_013",
                            severity=Severity.ADVISORY,
                            message=(
                                f"RGB color space '{cs_name}' ({cs.cs_type}) used "
                                f"on page {page.page_num} in a CMYK workflow "
                                f"(potential out-of-gamut colors)"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "color_space_type": cs.cs_type,
                            },
                        )
                    )
                    return findings  # One finding is enough

        return findings

    @staticmethod
    def _calculate_tac(color_values: tuple[float, ...]) -> float:
        """Calculate Total Area Coverage from CMYK values.

        CMYK values are in 0.0-1.0 range. TAC is the sum as percentages.
        For example: (1.0, 0.8, 0.7, 0.3) = 280%.
        """
        return sum(color_values) * 100.0
