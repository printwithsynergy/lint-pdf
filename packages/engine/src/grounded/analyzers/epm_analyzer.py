"""EpmAnalyzer — Extended Print Mode (CMY-only / K-less) checks.

Validates PDF documents for EPM printing readiness by detecting K channel
dependencies, pure black text, CMY composite quality, and related issues
that arise when printing without the Black (K) channel.

Check IDs:
    GRD_EPM_001 — K channel usage detection
    GRD_EPM_002 — Pure black text detection
    GRD_EPM_003 — CMY composite black quality
    GRD_EPM_004 — CMY-only TAC recalculation
    GRD_EPM_005 — Spot color K-dependency in fallbacks
    GRD_EPM_006 — Image K channel dependency
    GRD_EPM_007 — Registration color in EPM mode
    GRD_EPM_008 — Gray balance risk
    GRD_EPM_009 — EPM toner limit exceeded
    GRD_EPM_010 — Substrate-specific ink limit
    GRD_EPM_011 — EPM spot color fidelity warning
    GRD_EPM_012 — EPM variable data compatibility
    GRD_EPM_013 — EPM halftone incompatibility
    GRD_EPM_014 — EPM ICC profile class mismatch
    GRD_EPM_015 — EPM white ink underlayer detection
    GRD_EPM_016 — EPM overprint simulation mode
    GRD_EPM_017 — EPM maximum object count
    GRD_EPM_018 — EPM minimum line weight for digital
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

# Gray balance tolerance: C, M, Y within this percentage of each other
_GRAY_BALANCE_TOLERANCE = 0.05  # 5%
_GRAY_BALANCE_MIN = 0.20  # 20% minimum for each channel

# Registration color threshold
_REGISTRATION_THRESHOLD = 0.90  # 90% — all CMYK components high

# EPM digital press defaults
_EPM_MAX_OBJECTS_PER_PAGE = 5000  # advisory threshold for RIP performance
_EPM_MIN_LINE_WEIGHT_DEFAULT = 0.35  # pt — thinner threshold for digital
_EPM_TONER_LIMIT_DEFAULT = 280.0  # % total toner area coverage


class EpmAnalyzer(BaseAnalyzer):
    """Analyzer for Extended Print Mode (CMY-only) readiness.

    Args:
        cmy_tac_threshold: Maximum allowed CMY-only TAC percentage (default 240).
        epm_toner_limit: Maximum total toner area coverage (default 280).
        epm_min_line_weight: Minimum line weight for digital press (default 0.35pt).
    """

    def __init__(
        self,
        cmy_tac_threshold: float = 240.0,
        epm_toner_limit: float = 280.0,
        epm_min_line_weight: float = 0.35,
    ) -> None:
        self.cmy_tac_threshold = cmy_tac_threshold
        self.epm_toner_limit = epm_toner_limit
        self.epm_min_line_weight = epm_min_line_weight

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document for EPM (CMY-only) readiness."""
        from grounded.semantic.events import (
            PathPaintingEvent,
            TextRenderedEvent,
        )

        findings: list[Finding] = []

        k_usage_count = 0
        k_usage_pages: set[int] = set()
        pure_black_text_count = 0
        pure_black_text_pages: set[int] = set()
        registration_count = 0
        registration_pages: set[int] = set()
        gray_balance_count = 0
        gray_balance_pages: set[int] = set()
        max_cmy_tac = 0.0
        max_cmy_tac_page = 0
        max_cmy_tac_values: tuple[float, ...] = ()
        weak_black_count = 0
        weak_black_pages: set[int] = set()
        # Tracking for new EPM checks
        max_total_tac = 0.0
        max_total_tac_page = 0
        max_total_tac_values: tuple[float, ...] = ()
        thin_line_count = 0
        thin_line_pages: set[int] = set()
        object_counts_per_page: dict[int, int] = {}
        overprint_count = 0
        overprint_pages: set[int] = set()
        ink_limit_count = 0
        ink_limit_pages: set[int] = set()

        for event in events:
            if isinstance(event, PathPaintingEvent):
                # Track object count per page (GRD_EPM_017)
                object_counts_per_page[event.page_num] = (
                    object_counts_per_page.get(event.page_num, 0) + 1
                )

                # GRD_EPM_016: Overprint detection
                if hasattr(event, "overprint") and event.overprint:
                    overprint_count += 1
                    overprint_pages.add(event.page_num)

                # GRD_EPM_018: Minimum line weight for digital
                if event.stroke and hasattr(event, "line_width"):
                    if (
                        event.line_width is not None
                        and event.line_width > 0
                        and event.line_width < self.epm_min_line_weight
                    ):
                        thin_line_count += 1
                        thin_line_pages.add(event.page_num)

                # Process fill colors
                if event.fill and event.fill_color_space == "DeviceCMYK":
                    vals = event.fill_color_values
                    if len(vals) == 4:
                        c, m, y, k = vals

                        # GRD_EPM_001: K channel usage
                        if k > 0:
                            k_usage_count += 1
                            k_usage_pages.add(event.page_num)

                        # GRD_EPM_004: CMY-only TAC
                        cmy_tac = (c + m + y) * 100.0
                        if cmy_tac > max_cmy_tac:
                            max_cmy_tac = cmy_tac
                            max_cmy_tac_page = event.page_num
                            max_cmy_tac_values = vals

                        # GRD_EPM_009: Total toner TAC
                        total_tac = (c + m + y + k) * 100.0
                        if total_tac > max_total_tac:
                            max_total_tac = total_tac
                            max_total_tac_page = event.page_num
                            max_total_tac_values = vals

                        # GRD_EPM_010: Substrate-specific ink limit
                        if c > 0.95 or m > 0.95 or y > 0.95 or k > 0.95:
                            ink_limit_count += 1
                            ink_limit_pages.add(event.page_num)

                        # GRD_EPM_007: Registration color
                        if (
                            c >= _REGISTRATION_THRESHOLD
                            and m >= _REGISTRATION_THRESHOLD
                            and y >= _REGISTRATION_THRESHOLD
                            and k >= _REGISTRATION_THRESHOLD
                        ):
                            registration_count += 1
                            registration_pages.add(event.page_num)

                        # GRD_EPM_008: Gray balance risk
                        if (
                            c >= _GRAY_BALANCE_MIN
                            and m >= _GRAY_BALANCE_MIN
                            and y >= _GRAY_BALANCE_MIN
                            and k == 0
                            and abs(c - m) <= _GRAY_BALANCE_TOLERANCE
                            and abs(c - y) <= _GRAY_BALANCE_TOLERANCE
                            and abs(m - y) <= _GRAY_BALANCE_TOLERANCE
                        ):
                            gray_balance_count += 1
                            gray_balance_pages.add(event.page_num)

                        # GRD_EPM_003: CMY composite black quality
                        if k == 0 and (c + m + y) > 0.5:
                            total_cmy_pct = (c + m + y) * 100.0
                            if total_cmy_pct < 200.0:
                                weak_black_count += 1
                                weak_black_pages.add(event.page_num)

                # Process stroke colors
                if event.stroke and event.stroke_color_space == "DeviceCMYK":
                    vals = event.stroke_color_values
                    if len(vals) == 4:
                        c, m, y, k = vals

                        if k > 0:
                            k_usage_count += 1
                            k_usage_pages.add(event.page_num)

                        cmy_tac = (c + m + y) * 100.0
                        if cmy_tac > max_cmy_tac:
                            max_cmy_tac = cmy_tac
                            max_cmy_tac_page = event.page_num
                            max_cmy_tac_values = vals

                        total_tac = (c + m + y + k) * 100.0
                        if total_tac > max_total_tac:
                            max_total_tac = total_tac
                            max_total_tac_page = event.page_num
                            max_total_tac_values = vals

                        # GRD_EPM_010: Substrate-specific ink limit
                        if c > 0.95 or m > 0.95 or y > 0.95 or k > 0.95:
                            ink_limit_count += 1
                            ink_limit_pages.add(event.page_num)

                        if (
                            c >= _REGISTRATION_THRESHOLD
                            and m >= _REGISTRATION_THRESHOLD
                            and y >= _REGISTRATION_THRESHOLD
                            and k >= _REGISTRATION_THRESHOLD
                        ):
                            registration_count += 1
                            registration_pages.add(event.page_num)

                        if (
                            c >= _GRAY_BALANCE_MIN
                            and m >= _GRAY_BALANCE_MIN
                            and y >= _GRAY_BALANCE_MIN
                            and k == 0
                            and abs(c - m) <= _GRAY_BALANCE_TOLERANCE
                            and abs(c - y) <= _GRAY_BALANCE_TOLERANCE
                            and abs(m - y) <= _GRAY_BALANCE_TOLERANCE
                        ):
                            gray_balance_count += 1
                            gray_balance_pages.add(event.page_num)

                        if k == 0 and (c + m + y) > 0.5:
                            total_cmy_pct = (c + m + y) * 100.0
                            if total_cmy_pct < 200.0:
                                weak_black_count += 1
                                weak_black_pages.add(event.page_num)

            elif isinstance(event, TextRenderedEvent):
                # Track object count per page (GRD_EPM_017)
                object_counts_per_page[event.page_num] = (
                    object_counts_per_page.get(event.page_num, 0) + 1
                )

                if len(event.color_values) == 4 and event.color_space == "DeviceCMYK":
                    c, m, y, k = event.color_values

                    # GRD_EPM_001: K channel usage in text
                    if k > 0:
                        k_usage_count += 1
                        k_usage_pages.add(event.page_num)

                    # GRD_EPM_002: Pure black text
                    if abs(k - 1.0) < 0.01 and abs(c) < 0.01 and abs(m) < 0.01 and abs(y) < 0.01:
                        pure_black_text_count += 1
                        pure_black_text_pages.add(event.page_num)

                elif event.color_space == "DeviceGray" and len(event.color_values) == 1:
                    # GRD_EPM_002: DeviceGray black text (gray=0 means black)
                    if abs(event.color_values[0]) < 0.01:
                        pure_black_text_count += 1
                        pure_black_text_pages.add(event.page_num)

        # GRD_EPM_001: K channel usage detection
        if k_usage_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_001",
                    severity=Severity.SQUALL,
                    message=(
                        f"EPM K-channel dependency: {k_usage_count} object(s) use K "
                        f"across {len(k_usage_pages)} page(s)"
                    ),
                    details={
                        "k_usage_count": k_usage_count,
                        "pages": sorted(k_usage_pages),
                    },
                )
            )

        # GRD_EPM_002: Pure black text detection
        if pure_black_text_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_002",
                    severity=Severity.AGROUND,
                    message=(
                        f"EPM pure black text: {pure_black_text_count} text object(s) use "
                        f"pure K-only or DeviceGray black and will not print in EPM mode "
                        f"(CMY-only) across {len(pure_black_text_pages)} page(s)"
                    ),
                    details={
                        "pure_black_text_count": pure_black_text_count,
                        "pages": sorted(pure_black_text_pages),
                    },
                    object_type="text",
                )
            )

        # GRD_EPM_003: CMY composite black quality
        if weak_black_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_003",
                    severity=Severity.SQUALL,
                    message=(
                        f"EPM weak CMY black: {weak_black_count} object(s) with K=0 and "
                        f"C+M+Y < 200% may produce weak blacks in CMY-only mode "
                        f"across {len(weak_black_pages)} page(s) "
                        f"(good density requires C>80% M>70% Y>70%)"
                    ),
                    details={
                        "weak_black_count": weak_black_count,
                        "pages": sorted(weak_black_pages),
                        "recommended_minimum_cmy": "C>80% M>70% Y>70%",
                    },
                    object_type="path",
                )
            )

        # GRD_EPM_004: CMY-only TAC recalculation
        if max_cmy_tac > self.cmy_tac_threshold:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_004",
                    severity=Severity.SQUALL,
                    message=(
                        f"EPM CMY TAC {max_cmy_tac:.0f}% exceeds {self.cmy_tac_threshold:.0f}% "
                        f"threshold on page {max_cmy_tac_page} (K excluded)"
                    ),
                    page_num=max_cmy_tac_page,
                    details={
                        "cmy_tac": max_cmy_tac,
                        "cmy_tac_threshold": self.cmy_tac_threshold,
                        "color_values": list(max_cmy_tac_values),
                    },
                )
            )

        # GRD_EPM_005: Spot color K-dependency in fallbacks
        findings.extend(self._check_spot_k_dependency(document))

        # GRD_EPM_006: Image K channel dependency
        findings.extend(self._check_image_k_dependency(document))

        # GRD_EPM_007: Registration color in EPM mode
        if registration_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_007",
                    severity=Severity.ADVISORY,
                    message=(
                        f"EPM registration color: {registration_count} object(s) use "
                        f"registration color (all CMYK components >={_REGISTRATION_THRESHOLD * 100:.0f}%) "
                        f"across {len(registration_pages)} page(s); in EPM mode only CMY "
                        f"channels will print"
                    ),
                    details={
                        "registration_count": registration_count,
                        "pages": sorted(registration_pages),
                    },
                )
            )

        # GRD_EPM_008: Gray balance risk
        if gray_balance_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_008",
                    severity=Severity.SQUALL,
                    message=(
                        f"EPM gray balance risk: {gray_balance_count} object(s) with "
                        f"neutral CMY mix (C{chr(0x2248)}M{chr(0x2248)}Y within "
                        f"{_GRAY_BALANCE_TOLERANCE * 100:.0f}%, all >{_GRAY_BALANCE_MIN * 100:.0f}%) "
                        f"across {len(gray_balance_pages)} page(s) are high risk for "
                        f"color shift without K channel"
                    ),
                    details={
                        "gray_balance_count": gray_balance_count,
                        "pages": sorted(gray_balance_pages),
                        "tolerance": _GRAY_BALANCE_TOLERANCE,
                        "minimum_threshold": _GRAY_BALANCE_MIN,
                    },
                    object_type="path",
                )
            )

        # GRD_EPM_009: EPM toner limit exceeded
        if max_total_tac > self.epm_toner_limit:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_009",
                    severity=Severity.AGROUND,
                    message=(
                        f"EPM toner limit exceeded: total toner area coverage "
                        f"{max_total_tac:.0f}% exceeds EPM device limit "
                        f"{self.epm_toner_limit:.0f}% on page {max_total_tac_page}"
                    ),
                    page_num=max_total_tac_page,
                    details={
                        "total_tac": max_total_tac,
                        "epm_toner_limit": self.epm_toner_limit,
                        "color_values": list(max_total_tac_values),
                    },
                )
            )

        # GRD_EPM_010: Substrate-specific ink limit
        if ink_limit_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_010",
                    severity=Severity.SQUALL,
                    message=(
                        f"EPM substrate ink limit: {ink_limit_count} object(s) with "
                        f"individual ink channel >95% across "
                        f"{len(ink_limit_pages)} page(s) may exceed substrate-specific "
                        f"limits for digital devices"
                    ),
                    details={
                        "ink_limit_count": ink_limit_count,
                        "pages": sorted(ink_limit_pages),
                        "per_channel_limit": 0.95,
                    },
                )
            )

        # GRD_EPM_011: EPM spot color fidelity
        findings.extend(self._check_spot_color_fidelity(document))

        # GRD_EPM_012: EPM variable data
        findings.extend(self._check_variable_data(document))

        # GRD_EPM_013: EPM halftone incompatibility
        findings.extend(self._check_halftone_incompatibility(document))

        # GRD_EPM_014: EPM ICC profile class
        findings.extend(self._check_icc_profile_class(document))

        # GRD_EPM_015: EPM white ink underlayer
        findings.extend(self._check_white_ink_underlayer(document))

        # GRD_EPM_016: EPM overprint simulation
        findings.extend(self._check_overprint_simulation(document))

        # GRD_EPM_017: EPM maximum object count
        for page_num, count in sorted(object_counts_per_page.items()):
            if count > _EPM_MAX_OBJECTS_PER_PAGE:
                findings.append(
                    Finding(
                        inspection_id="GRD_EPM_017",
                        severity=Severity.ADVISORY,
                        message=(
                            f"EPM high object count: page {page_num} has {count} "
                            f"objects (threshold {_EPM_MAX_OBJECTS_PER_PAGE}) which "
                            f"may slow digital press RIP processing"
                        ),
                        page_num=page_num,
                        details={
                            "object_count": count,
                            "threshold": _EPM_MAX_OBJECTS_PER_PAGE,
                        },
                    )
                )

        # GRD_EPM_018: EPM minimum line weight
        if thin_line_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_018",
                    severity=Severity.SQUALL,
                    message=(
                        f"EPM thin line weight: {thin_line_count} stroked path(s) "
                        f"have line width below {self.epm_min_line_weight}pt "
                        f"across {len(thin_line_pages)} page(s)"
                    ),
                    details={
                        "thin_line_count": thin_line_count,
                        "epm_min_line_weight": self.epm_min_line_weight,
                        "pages": sorted(thin_line_pages),
                    },
                    object_type="path",
                )
            )

        return findings

    @staticmethod
    def _check_spot_color_fidelity(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_011: Check for spot colors that may not reproduce on digital."""
        findings: list[Finding] = []
        _SPOT_PREFIXES = ("PANTONE", "HKS", "TOYO")
        checked_colorants: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                if not cs.colorant_names:
                    continue

                for colorant in cs.colorant_names:
                    if colorant in checked_colorants:
                        continue
                    if colorant in ("All", "None"):
                        continue
                    upper = colorant.upper()
                    if any(upper.startswith(prefix) for prefix in _SPOT_PREFIXES):
                        checked_colorants.add(colorant)
                        findings.append(
                            Finding(
                                inspection_id="GRD_EPM_011",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"EPM spot color fidelity: spot color '{colorant}' "
                                    f"may not reproduce accurately on digital devices"
                                ),
                                page_num=page.page_num,
                                details={
                                    "colorant_name": colorant,
                                    "color_space_type": cs.cs_type,
                                },
                            )
                        )

        return findings

    @staticmethod
    def _check_variable_data(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_012: Check for variable data indicators."""
        findings: list[Finding] = []
        catalog = document.catalog

        has_af = "/AF" in catalog or "AF" in catalog
        mark_info = catalog.get("/MarkInfo", catalog.get("MarkInfo", {}))
        has_variable = False
        if isinstance(mark_info, dict):
            has_variable = bool(mark_info)

        if has_af or has_variable:
            indicators: list[str] = []
            if has_af:
                indicators.append("Associated Files (/AF)")
            if has_variable:
                indicators.append("MarkInfo")
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_012",
                    severity=Severity.ADVISORY,
                    message=(
                        f"EPM variable data: document contains variable data "
                        f"indicators ({', '.join(indicators)})"
                    ),
                    details={
                        "has_associated_files": has_af,
                        "has_mark_info": has_variable,
                    },
                )
            )

        return findings

    @staticmethod
    def _check_halftone_incompatibility(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_013: Check for custom halftone dictionaries in ExtGState."""
        findings: list[Finding] = []

        for page in document.pages:
            resources = page.resources
            ext_g_state = resources.get("/ExtGState", resources.get("ExtGState", {}))
            if not isinstance(ext_g_state, dict):
                continue

            for gs_name, gs_dict in ext_g_state.items():
                if not isinstance(gs_dict, dict):
                    continue
                if "/HT" in gs_dict or "HT" in gs_dict:
                    findings.append(
                        Finding(
                            inspection_id="GRD_EPM_013",
                            severity=Severity.ADVISORY,
                            message=(
                                f"EPM halftone incompatibility: custom halftone in "
                                f"ExtGState '{gs_name}' on page {page.page_num}; "
                                f"digital presses use their own screening"
                            ),
                            page_num=page.page_num,
                            details={
                                "ext_g_state_name": gs_name,
                            },
                        )
                    )

        return findings

    @staticmethod
    def _check_icc_profile_class(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_014: Check output intent ICC profile classes."""
        findings: list[Finding] = []
        _VALID_CLASSES = ("prtr", "mntr")

        for oi in document.output_intents:
            profile_class = oi.get("profile_class", oi.get("/ProfileClass", ""))
            if isinstance(profile_class, str) and profile_class and profile_class not in _VALID_CLASSES:
                findings.append(
                    Finding(
                        inspection_id="GRD_EPM_014",
                        severity=Severity.ADVISORY,
                        message=(
                            f"EPM ICC profile class mismatch: output intent has "
                            f"profile class '{profile_class}' (expected 'prtr' or "
                            f"'mntr'); digital presses need device-specific profiles"
                        ),
                        details={
                            "profile_class": profile_class,
                            "valid_classes": list(_VALID_CLASSES),
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_white_ink_underlayer(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_015: Check for white ink separation color spaces."""
        findings: list[Finding] = []
        detected = False

        for page in document.pages:
            if detected:
                break
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "Separation":
                    continue
                if not cs.colorant_names:
                    continue
                colorant = cs.colorant_names[0]
                if colorant.lower() == "white":
                    detected = True
                    findings.append(
                        Finding(
                            inspection_id="GRD_EPM_015",
                            severity=Severity.ADVISORY,
                            message=(
                                f"EPM white ink underlayer: Separation color space "
                                f"with colorant '{colorant}' detected on page "
                                f"{page.page_num}; white ink separations are used "
                                f"for dark substrate printing"
                            ),
                            page_num=page.page_num,
                            details={
                                "colorant_name": colorant,
                            },
                        )
                    )
                    break

        return findings

    @staticmethod
    def _check_overprint_simulation(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_016: Check ExtGState for overprint settings."""
        findings: list[Finding] = []

        for page in document.pages:
            resources = page.resources
            ext_g_state = resources.get("/ExtGState", resources.get("ExtGState", {}))
            if not isinstance(ext_g_state, dict):
                continue

            for gs_name, gs_dict in ext_g_state.items():
                if not isinstance(gs_dict, dict):
                    continue
                op_val = gs_dict.get("/OP", gs_dict.get("OP"))
                if op_val is True:
                    opm_val = gs_dict.get("/OPM", gs_dict.get("OPM", 0))
                    findings.append(
                        Finding(
                            inspection_id="GRD_EPM_016",
                            severity=Severity.ADVISORY,
                            message=(
                                f"EPM overprint simulation: ExtGState '{gs_name}' on "
                                f"page {page.page_num} has overprint enabled "
                                f"(OP=true, OPM={opm_val}); digital presses "
                                f"simulate overprint"
                            ),
                            page_num=page.page_num,
                            details={
                                "ext_g_state_name": gs_name,
                                "overprint": True,
                                "overprint_mode": opm_val,
                            },
                        )
                    )

        return findings

    @staticmethod
    def _check_spot_k_dependency(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_005: Check Separation color spaces for K-dependent alternates."""
        findings: list[Finding] = []
        checked_colorants: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "Separation":
                    continue
                if not cs.colorant_names:
                    continue

                colorant = cs.colorant_names[0] if cs.colorant_names else ""
                if not colorant or colorant in ("All", "None"):
                    continue
                if colorant in checked_colorants:
                    continue
                checked_colorants.add(colorant)

                # Check if the alternate color space is CMYK-based
                if cs.alternate is not None and cs.alternate.is_cmyk():
                    findings.append(
                        Finding(
                            inspection_id="GRD_EPM_005",
                            severity=Severity.ADVISORY,
                            message=(
                                f"EPM spot color K-dependency: Spot color '{colorant}' "
                                f"has a CMYK fallback (alternate: {cs.alternate.cs_type}) "
                                f"which may include K channel"
                            ),
                            page_num=page.page_num,
                            details={
                                "colorant_name": colorant,
                                "alternate_type": cs.alternate.cs_type,
                            },
                        )
                    )

        return findings

    @staticmethod
    def _check_image_k_dependency(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_EPM_006: Check images for CMYK K channel dependency."""
        findings: list[Finding] = []
        cmyk_image_count = 0
        cmyk_image_pages: set[int] = set()

        for page in document.pages:
            for image in page.images:
                if image.color_space is not None and image.color_space.is_cmyk():
                    cmyk_image_count += 1
                    cmyk_image_pages.add(page.page_num)

        if cmyk_image_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_EPM_006",
                    severity=Severity.SQUALL,
                    message=(
                        f"EPM image K-dependency: {cmyk_image_count} CMYK image(s) "
                        f"across {len(cmyk_image_pages)} page(s) have K channel "
                        f"dependency that affects EPM output"
                    ),
                    details={
                        "cmyk_image_count": cmyk_image_count,
                        "pages": sorted(cmyk_image_pages),
                    },
                    object_type="image",
                )
            )

        return findings
