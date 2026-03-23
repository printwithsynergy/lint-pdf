"""OverprintAnalyzer — OP/op/OPM interaction analysis.

Processes OverprintChangedEvent and ColorChangedEvent events to detect
overprint-related preflight issues.

Overprint Mode (OPM) interactions per ISO 32000-2:2020 section 8.6.7:
- OPM=0: Source color replaces destination (black knockout)
- OPM=1: Only non-zero source components replace destination

Check IDs:
    GRD_OVER_001 — Overprint active on non-CMYK color space
    GRD_OVER_002 — OPM=0 with DeviceCMYK (potential knockout issues)
    GRD_OVER_003 — Overprint active with transparency
    GRD_OVER_004 — White overprint (fill is white + OP active)
    GRD_OVER_005 — Overprint inventory (informational)
    GRD_OVER_006 — RGB overprint
    GRD_OVER_007 — Small text knockout detection
    GRD_OVER_008 — Registration color outside marks
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_CMYK_SPACES = frozenset({"DeviceCMYK", "ICCBased"})


class OverprintAnalyzer(BaseAnalyzer):
    """Analyzer for overprint mode interactions."""

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze overprint events for problematic patterns."""
        from grounded.semantic.events import (
            ColorChangedEvent,
            OpacityChangedEvent,
            OverprintChangedEvent,
            TextRenderedEvent,
        )

        findings: list[Finding] = []

        # Track state
        op_stroking = False
        op_non_stroking = False
        opm = 0
        stroking_cs = "DeviceGray"
        non_stroking_cs = "DeviceGray"
        has_transparency = False
        overprint_active = False

        # GRD_OVER_005: Overprint inventory tracking
        overprint_inventory: dict[str, int] = {}

        # GRD_OVER_007: Track current non-stroking color for text knockout check
        non_stroking_color_values: tuple[float, ...] = ()

        for event in events:
            if isinstance(event, OverprintChangedEvent):
                if event.overprint_stroking is not None:
                    op_stroking = event.overprint_stroking
                if event.overprint_non_stroking is not None:
                    op_non_stroking = event.overprint_non_stroking
                if event.overprint_mode is not None:
                    opm = event.overprint_mode

                overprint_active = op_stroking or op_non_stroking

                # GRD_OVER_002: OPM=0 with DeviceCMYK
                if (
                    overprint_active
                    and opm == 0
                    and (stroking_cs == "DeviceCMYK" or non_stroking_cs == "DeviceCMYK")
                ):
                    findings.append(
                        Finding(
                            inspection_id="GRD_OVER_002",
                            severity=Severity.WARNING,
                            message=(
                                f"OPM=0 with DeviceCMYK and overprint active "
                                f"on page {event.page_num} "
                                f"(may cause unexpected knockout)"
                            ),
                            page_num=event.page_num,
                            details={
                                "opm": opm,
                                "op_stroking": op_stroking,
                                "op_non_stroking": op_non_stroking,
                                "stroking_cs": stroking_cs,
                                "non_stroking_cs": non_stroking_cs,
                            },
                            iso_clause="ISO 32000-2:2020 8.6.7",
                        )
                    )

                # GRD_OVER_003: Overprint with transparency
                if overprint_active and has_transparency:
                    findings.append(
                        Finding(
                            inspection_id="GRD_OVER_003",
                            severity=Severity.WARNING,
                            message=(
                                f"Overprint active with transparency "
                                f"on page {event.page_num} "
                                f"(rendering results may vary)"
                            ),
                            page_num=event.page_num,
                            details={
                                "op_stroking": op_stroking,
                                "op_non_stroking": op_non_stroking,
                                "has_transparency": has_transparency,
                            },
                            iso_clause="ISO 32000-2:2020 11.7.4.6",
                        )
                    )

            elif isinstance(event, ColorChangedEvent):
                if event.stroking:
                    stroking_cs = event.color_space
                else:
                    non_stroking_cs = event.color_space

                # GRD_OVER_004: White overprint
                if (
                    overprint_active
                    and not event.stroking
                    and op_non_stroking
                    and self._is_white(event.color_space, event.color_values)
                ):
                    findings.append(
                        Finding(
                            inspection_id="GRD_OVER_004",
                            severity=Severity.WARNING,
                            message=(
                                f"White overprint on page {event.page_num} "
                                f"(fill is white with overprint active — "
                                f"content underneath will show through)"
                            ),
                            page_num=event.page_num,
                            details={
                                "color_space": event.color_space,
                                "color_values": list(event.color_values),
                            },
                            iso_clause="ISO 32000-2:2020 8.6.7",
                        )
                    )

                # GRD_OVER_005: Track overprint inventory
                if overprint_active:
                    cs = event.color_space
                    overprint_inventory[cs] = overprint_inventory.get(cs, 0) + 1

                # GRD_OVER_006: RGB overprint
                if overprint_active and event.color_space == "DeviceRGB":
                    is_stroking_overprint = event.stroking and op_stroking
                    is_non_stroking_overprint = not event.stroking and op_non_stroking
                    if is_stroking_overprint or is_non_stroking_overprint:
                        findings.append(
                            Finding(
                                inspection_id="GRD_OVER_006",
                                severity=Severity.ERROR,
                                message=(
                                    f"Overprint active with DeviceRGB "
                                    f"on page {event.page_num} "
                                    f"(undefined behavior on press)"
                                ),
                                page_num=event.page_num,
                                details={
                                    "color_space": "DeviceRGB",
                                    "stroking": event.stroking,
                                    "color_values": list(event.color_values),
                                },
                                iso_clause="ISO 32000-2:2020 8.6.7",
                            )
                        )

                # GRD_OVER_008: Registration color with overprint
                if (
                    overprint_active
                    and event.color_space == "DeviceCMYK"
                    and len(event.color_values) >= 4
                    and all(v >= 0.95 for v in event.color_values[:4])
                ):
                    findings.append(
                        Finding(
                            inspection_id="GRD_OVER_008",
                            severity=Severity.ERROR,
                            message=(
                                f"Registration color with overprint active "
                                f"on page {event.page_num} "
                                f"(registration color outside marks is dangerous)"
                            ),
                            page_num=event.page_num,
                            details={
                                "color_space": event.color_space,
                                "color_values": list(event.color_values[:4]),
                                "stroking": event.stroking,
                            },
                        )
                    )

                # Track non-stroking color values for GRD_OVER_007
                if not event.stroking:
                    non_stroking_color_values = event.color_values

                # GRD_OVER_001: Overprint on non-CMYK
                if overprint_active:
                    cs = event.color_space
                    if cs not in _CMYK_SPACES and cs != "DeviceGray":
                        is_stroking_overprint = event.stroking and op_stroking
                        is_non_stroking_overprint = not event.stroking and op_non_stroking
                        if is_stroking_overprint or is_non_stroking_overprint:
                            findings.append(
                                Finding(
                                    inspection_id="GRD_OVER_001",
                                    severity=Severity.WARNING,
                                    message=(
                                        f"Overprint active on non-CMYK "
                                        f"color space '{cs}' "
                                        f"on page {event.page_num} "
                                        f"(rendering differs between screen and print)"
                                    ),
                                    page_num=event.page_num,
                                    details={
                                        "color_space": cs,
                                        "stroking": event.stroking,
                                    },
                                    iso_clause="ISO 32000-2:2020 8.6.7",
                                )
                            )

            elif isinstance(event, TextRenderedEvent):
                # GRD_OVER_007: Small text knockout detection
                if (
                    not overprint_active
                    and non_stroking_cs == "DeviceCMYK"
                    and len(non_stroking_color_values) >= 4
                    and non_stroking_color_values[3] > 0.9
                    and event.font_size < 12
                    and event.font_size > 0
                ):
                    findings.append(
                        Finding(
                            inspection_id="GRD_OVER_007",
                            severity=Severity.WARNING,
                            message=(
                                f"Small black text ({event.font_size:.1f}pt) "
                                f"in knockout mode on page {event.page_num} "
                                f"(overprint not active — risk of misregistration)"
                            ),
                            page_num=event.page_num,
                            details={
                                "font_size": event.font_size,
                                "k_value": non_stroking_color_values[3],
                                "color_space": non_stroking_cs,
                                "overprint_active": False,
                            },
                            object_type="text",
                        )
                    )

            elif isinstance(event, OpacityChangedEvent):
                if event.stroking_alpha is not None and event.stroking_alpha < 1.0:
                    has_transparency = True
                if event.non_stroking_alpha is not None and event.non_stroking_alpha < 1.0:
                    has_transparency = True
                if event.blend_mode and event.blend_mode != "Normal":
                    has_transparency = True

        # GRD_OVER_005: Overprint inventory (post-loop summary)
        if overprint_inventory:
            total_count = sum(overprint_inventory.values())
            findings.append(
                Finding(
                    inspection_id="GRD_OVER_005",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Overprint inventory: {total_count} object(s) with "
                        f"overprint enabled across {len(overprint_inventory)} "
                        f"color space type(s)"
                    ),
                    details={
                        "total_count": total_count,
                        "by_color_space": overprint_inventory,
                    },
                )
            )

        return findings

    @staticmethod
    def _is_white(color_space: str, color_values: tuple[float, ...]) -> bool:
        """Check if color values represent white in the given color space."""
        if color_space == "DeviceGray" and len(color_values) >= 1:
            return color_values[0] >= 0.99
        if color_space == "DeviceRGB" and len(color_values) >= 3:
            return all(v >= 0.99 for v in color_values[:3])
        if color_space == "DeviceCMYK" and len(color_values) >= 4:
            return all(v <= 0.01 for v in color_values[:4])
        return False
