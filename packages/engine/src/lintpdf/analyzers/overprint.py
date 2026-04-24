"""OverprintAnalyzer — OP/op/OPM interaction analysis.

Processes OverprintChangedEvent and ColorChangedEvent events to detect
overprint-related preflight issues.

Overprint Mode (OPM) interactions per ISO 32000-2:2020 section 8.6.7:
- OPM=0: Source color replaces destination (black knockout)
- OPM=1: Only non-zero source components replace destination

Check IDs:
    LPDF_OVER_001 — Overprint active on non-CMYK color space
    LPDF_OVER_002 — OPM=0 with DeviceCMYK (potential knockout issues)
    LPDF_OVER_003 — Overprint active with transparency
    LPDF_OVER_004 — White overprint (fill is white + OP active)
    LPDF_OVER_005 — Overprint inventory (informational)
    LPDF_OVER_006 — RGB overprint
    LPDF_OVER_007 — Small text knockout detection
    LPDF_OVER_008 — Registration color outside marks
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

_CMYK_SPACES = frozenset({"DeviceCMYK", "ICCBased"})


class OverprintAnalyzer(BaseAnalyzer):
    """Analyzer for overprint mode interactions."""

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze overprint events for problematic patterns."""
        from lintpdf.semantic.events import (
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

        # LPDF_OVER_005: Overprint inventory tracking
        overprint_inventory: dict[str, int] = {}

        # LPDF_OVER_007: Track current non-stroking color for text knockout check
        non_stroking_color_values: tuple[float, ...] = ()

        # WS-14 per-page aggregation for LPDF_OVER_007. On a 10-up
        # repeat layout the per-glyph knockout warning fires ~940
        # times; collapse into one aggregate per page with count +
        # sample bboxes, matching the LPDF_COLOR_009 / LPDF_COLOR_010
        # pattern from WS-7.
        over007_agg: dict[int, dict[str, object]] = {}

        for event in events:
            if isinstance(event, OverprintChangedEvent):
                if event.overprint_stroking is not None:
                    op_stroking = event.overprint_stroking
                if event.overprint_non_stroking is not None:
                    op_non_stroking = event.overprint_non_stroking
                if event.overprint_mode is not None:
                    opm = event.overprint_mode

                overprint_active = op_stroking or op_non_stroking

                # LPDF_OVER_002: OPM=0 with DeviceCMYK
                if (
                    overprint_active
                    and opm == 0
                    and (stroking_cs == "DeviceCMYK" or non_stroking_cs == "DeviceCMYK")
                ):
                    findings.append(
                        Finding(
                            inspection_id="LPDF_OVER_002",
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

                # LPDF_OVER_003: Overprint with transparency
                if overprint_active and has_transparency:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_OVER_003",
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

                # LPDF_OVER_004: White overprint
                if (
                    overprint_active
                    and not event.stroking
                    and op_non_stroking
                    and self._is_white(event.color_space, event.color_values)
                ):
                    findings.append(
                        Finding(
                            inspection_id="LPDF_OVER_004",
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

                # LPDF_OVER_005: Track overprint inventory
                if overprint_active:
                    cs = event.color_space
                    overprint_inventory[cs] = overprint_inventory.get(cs, 0) + 1

                # LPDF_OVER_006: RGB overprint
                if overprint_active and event.color_space == "DeviceRGB":
                    is_stroking_overprint = event.stroking and op_stroking
                    is_non_stroking_overprint = not event.stroking and op_non_stroking
                    if is_stroking_overprint or is_non_stroking_overprint:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_OVER_006",
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

                # LPDF_OVER_008: Registration color with overprint
                if (
                    overprint_active
                    and event.color_space == "DeviceCMYK"
                    and len(event.color_values) >= 4
                    and all(v >= 0.95 for v in event.color_values[:4])
                ):
                    findings.append(
                        Finding(
                            inspection_id="LPDF_OVER_008",
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

                # Track non-stroking color values for LPDF_OVER_007
                if not event.stroking:
                    non_stroking_color_values = event.color_values

                # LPDF_OVER_001: Overprint on non-CMYK
                if overprint_active:
                    cs = event.color_space
                    if cs not in _CMYK_SPACES and cs != "DeviceGray":
                        is_stroking_overprint = event.stroking and op_stroking
                        is_non_stroking_overprint = not event.stroking and op_non_stroking
                        if is_stroking_overprint or is_non_stroking_overprint:
                            findings.append(
                                Finding(
                                    inspection_id="LPDF_OVER_001",
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
                # LPDF_OVER_007: accumulate small knockout-black text
                # per page; emit one aggregate at the end.
                if (
                    not overprint_active
                    and non_stroking_cs == "DeviceCMYK"
                    and len(non_stroking_color_values) >= 4
                    and non_stroking_color_values[3] > 0.9
                    and event.font_size < 12
                    and event.font_size > 0
                ):
                    bucket = over007_agg.setdefault(
                        event.page_num,
                        {
                            "count": 0,
                            "bboxes": [],
                            "min_font_size": event.font_size,
                            "max_k_value": non_stroking_color_values[3],
                            "color_space": non_stroking_cs,
                        },
                    )
                    bucket["count"] = int(bucket["count"]) + 1  # type: ignore[arg-type]
                    bboxes = bucket["bboxes"]
                    if (
                        isinstance(bboxes, list)
                        and len(bboxes) < 5
                        and getattr(event, "bbox", None)
                    ):
                        bboxes.append(list(event.bbox))
                    if event.font_size < float(bucket["min_font_size"]):  # type: ignore[arg-type]
                        bucket["min_font_size"] = event.font_size
                    if non_stroking_color_values[3] > float(bucket["max_k_value"]):  # type: ignore[arg-type]
                        bucket["max_k_value"] = non_stroking_color_values[3]

            elif isinstance(event, OpacityChangedEvent):
                if event.stroking_alpha is not None and event.stroking_alpha < 1.0:
                    has_transparency = True
                if event.non_stroking_alpha is not None and event.non_stroking_alpha < 1.0:
                    has_transparency = True
                if event.blend_mode and event.blend_mode != "Normal":
                    has_transparency = True

        # LPDF_OVER_007: emit one aggregate per page with count +
        # representative bboxes. Matches the LPDF_COLOR_009 /
        # LPDF_COLOR_010 shape so the viewer's findings panel renders
        # a single row with object_count in details.
        for page_num in sorted(over007_agg):
            bucket = over007_agg[page_num]
            count = int(bucket["count"])  # type: ignore[arg-type]
            if count <= 0:
                continue
            min_size = float(bucket["min_font_size"])  # type: ignore[arg-type]
            findings.append(
                Finding(
                    inspection_id="LPDF_OVER_007",
                    severity=Severity.WARNING,
                    message=(
                        f"{count} small black text instance"
                        f"{'s' if count != 1 else ''} (min {min_size:.1f}pt) "
                        f"in knockout mode on page {page_num} "
                        f"(overprint not active — risk of misregistration)"
                    ),
                    page_num=page_num,
                    details={
                        "object_count": count,
                        "min_font_size": min_size,
                        "max_k_value": float(bucket["max_k_value"]),  # type: ignore[arg-type]
                        "color_space": bucket.get("color_space"),
                        "overprint_active": False,
                        "representative_bboxes": bucket["bboxes"],
                    },
                    object_type="text",
                )
            )

        # LPDF_OVER_005: Overprint inventory (post-loop summary)
        if overprint_inventory:
            total_count = sum(overprint_inventory.values())
            findings.append(
                Finding(
                    inspection_id="LPDF_OVER_005",
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
