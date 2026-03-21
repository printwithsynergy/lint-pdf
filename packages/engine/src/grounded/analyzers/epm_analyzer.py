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


class EpmAnalyzer(BaseAnalyzer):
    """Analyzer for Extended Print Mode (CMY-only) readiness.

    Args:
        cmy_tac_threshold: Maximum allowed CMY-only TAC percentage (default 240).
    """

    def __init__(self, cmy_tac_threshold: float = 240.0) -> None:
        self.cmy_tac_threshold = cmy_tac_threshold

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

        for event in events:
            if isinstance(event, PathPaintingEvent):
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
