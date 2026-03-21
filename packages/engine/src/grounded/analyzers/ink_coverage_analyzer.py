"""InkCoverageAnalyzer — ink coverage analysis for heatmaps and separation tracking.

Processes PathPaintingEvent and ColorChangedEvent events plus
SemanticDocument color space data to collect ink coverage statistics.

Check IDs:
    GRD_INK_001 — TAC heatmap data (per-page CMYK TAC statistics)
    GRD_INK_002 — Per-separation ink coverage
    GRD_INK_003 — Ink channel count validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument


class InkCoverageAnalyzer(BaseAnalyzer):
    """Analyzer for ink coverage statistics and separation tracking.

    Collects per-page TAC data for heatmap generation, tracks ink usage
    per separation channel, and validates total ink channel counts.

    Args:
        tac_limit: Maximum expected TAC percentage (default 300).
    """

    def __init__(self, tac_limit: float = 300.0) -> None:
        self.tac_limit = tac_limit

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze ink coverage across the document."""
        from grounded.semantic.events import (
            ColorChangedEvent,
            PathPaintingEvent,
        )

        findings: list[Finding] = []

        # Per-page TAC heatmap data: page_num -> list of (color_values, tac)
        page_tac_data: dict[int, list[dict]] = {}

        # Per-separation tracking: separation_name -> {pages, max_value, count}
        separation_stats: dict[str, dict] = {}

        # Track all unique ink channels
        process_channels_used: set[str] = set()
        spot_colors_used: set[str] = set()

        for event in events:
            if isinstance(event, PathPaintingEvent):
                # Collect CMYK fill data for TAC heatmap (GRD_INK_001)
                if event.fill and event.fill_color_space == "DeviceCMYK":
                    vals = event.fill_color_values
                    if len(vals) == 4:
                        tac = sum(vals) * 100.0
                        page_num = event.page_num

                        if page_num not in page_tac_data:
                            page_tac_data[page_num] = []
                        page_tac_data[page_num].append(
                            {
                                "color_values": list(vals),
                                "tac": tac,
                                "bbox": list(event.bbox) if event.bbox else None,
                            }
                        )

                        # Track process color channels (GRD_INK_002 / GRD_INK_003)
                        channel_names = ("C", "M", "Y", "K")
                        for i, ch_name in enumerate(channel_names):
                            if vals[i] > 0.0:
                                process_channels_used.add(ch_name)
                                self._update_separation_stats(
                                    separation_stats,
                                    ch_name,
                                    page_num,
                                    vals[i],
                                )

                # Also track CMYK stroke colors for separation stats
                if event.stroke and event.stroke_color_space == "DeviceCMYK":
                    vals = event.stroke_color_values
                    if len(vals) == 4:
                        channel_names = ("C", "M", "Y", "K")
                        for i, ch_name in enumerate(channel_names):
                            if vals[i] > 0.0:
                                process_channels_used.add(ch_name)
                                self._update_separation_stats(
                                    separation_stats,
                                    ch_name,
                                    event.page_num,
                                    vals[i],
                                )

                # Track Separation color space usage on fill
                if event.fill and event.fill_color_space == "Separation":
                    if event.fill_color_values:
                        spot_name = self._resolve_spot_name(
                            document,
                            event.page_num,
                            event.fill_color_space,
                        )
                        if spot_name:
                            spot_colors_used.add(spot_name)
                            self._update_separation_stats(
                                separation_stats,
                                spot_name,
                                event.page_num,
                                event.fill_color_values[0] if event.fill_color_values else 0.0,
                            )

                # Track Separation color space usage on stroke
                if event.stroke and event.stroke_color_space == "Separation":
                    if event.stroke_color_values:
                        spot_name = self._resolve_spot_name(
                            document,
                            event.page_num,
                            event.stroke_color_space,
                        )
                        if spot_name:
                            spot_colors_used.add(spot_name)
                            self._update_separation_stats(
                                separation_stats,
                                spot_name,
                                event.page_num,
                                event.stroke_color_values[0] if event.stroke_color_values else 0.0,
                            )

            elif isinstance(event, ColorChangedEvent):
                # Track CMYK channel usage from color change events
                if event.color_space == "DeviceCMYK" and len(event.color_values) == 4:
                    channel_names = ("C", "M", "Y", "K")
                    for i, ch_name in enumerate(channel_names):
                        if event.color_values[i] > 0.0:
                            process_channels_used.add(ch_name)
                            self._update_separation_stats(
                                separation_stats,
                                ch_name,
                                event.page_num,
                                event.color_values[i],
                            )

                # Track Separation color space from color change events
                if event.color_space == "Separation":
                    spot_name = self._resolve_spot_name(
                        document,
                        event.page_num,
                        event.color_space,
                    )
                    if spot_name:
                        spot_colors_used.add(spot_name)
                        self._update_separation_stats(
                            separation_stats,
                            spot_name,
                            event.page_num,
                            event.color_values[0] if event.color_values else 0.0,
                        )

        # Also discover spot colors from document color space definitions
        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type in ("Separation", "DeviceN") and cs.colorant_names:
                    for colorant in cs.colorant_names:
                        if colorant and colorant not in ("All", "None"):
                            spot_colors_used.add(colorant)

        # GRD_INK_001: TAC heatmap data per page
        for page_num in sorted(page_tac_data):
            entries = page_tac_data[page_num]
            tac_values = [e["tac"] for e in entries]
            max_tac = max(tac_values)
            max_entry = max(entries, key=lambda e: e["tac"])

            findings.append(
                Finding(
                    inspection_id="GRD_INK_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"TAC heatmap data for page {page_num}: "
                        f"max TAC {max_tac:.0f}%, {len(entries)} sample(s)"
                    ),
                    page_num=page_num,
                    details={
                        "max_tac": max_tac,
                        "max_tac_color_values": max_entry["color_values"],
                        "max_tac_bbox": max_entry["bbox"],
                        "sample_count": len(entries),
                        "tac_limit": self.tac_limit,
                        "samples": entries,
                    },
                    object_type="path",
                )
            )

        # GRD_INK_002: Per-separation ink coverage
        for sep_name in sorted(separation_stats):
            stats = separation_stats[sep_name]
            findings.append(
                Finding(
                    inspection_id="GRD_INK_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Separation '{sep_name}': used on "
                        f"{len(stats['pages'])} page(s), "
                        f"max value {stats['max_value'] * 100.0:.0f}%, "
                        f"{stats['event_count']} event(s)"
                    ),
                    details={
                        "separation_name": sep_name,
                        "pages_used": sorted(stats["pages"]),
                        "max_value": stats["max_value"],
                        "event_count": stats["event_count"],
                    },
                )
            )

        # GRD_INK_003: Ink channel count validation
        total_channels = len(process_channels_used) + len(spot_colors_used)

        channel_inventory = {
            "process_channels": sorted(process_channels_used),
            "spot_colors": sorted(spot_colors_used),
            "total_channel_count": total_channels,
        }

        # Always report channel inventory
        findings.append(
            Finding(
                inspection_id="GRD_INK_003",
                severity=Severity.ADVISORY,
                message=(
                    f"Ink channel inventory: {total_channels} channel(s) "
                    f"({len(process_channels_used)} process, "
                    f"{len(spot_colors_used)} spot)"
                ),
                details=channel_inventory,
            )
        )

        # Flag unusual channel counts
        if total_channels > 7:
            findings.append(
                Finding(
                    inspection_id="GRD_INK_003",
                    severity=Severity.SQUALL,
                    message=(
                        f"Unusually high ink channel count: {total_channels} channels "
                        f"(>7 is unusual for any workflow)"
                    ),
                    details={
                        **channel_inventory,
                        "threshold": 7,
                    },
                )
            )
        elif total_channels > 4:
            # Check if this is a standard CMYK workflow
            is_cmyk_workflow = self._is_cmyk_workflow(document)
            if is_cmyk_workflow:
                findings.append(
                    Finding(
                        inspection_id="GRD_INK_003",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Document uses {total_channels} ink channels "
                            f"in a CMYK workflow (>4 due to spot colors)"
                        ),
                        details={
                            **channel_inventory,
                            "workflow": "CMYK",
                        },
                    )
                )

        return findings

    @staticmethod
    def _update_separation_stats(
        stats: dict[str, dict],
        name: str,
        page_num: int,
        value: float,
    ) -> None:
        """Update running statistics for a separation channel."""
        if name not in stats:
            stats[name] = {
                "pages": set(),
                "max_value": 0.0,
                "event_count": 0,
            }
        stats[name]["pages"].add(page_num)
        if value > stats[name]["max_value"]:
            stats[name]["max_value"] = value
        stats[name]["event_count"] += 1

    @staticmethod
    def _resolve_spot_name(
        document: SemanticDocument,
        page_num: int,
        color_space: str,
    ) -> str | None:
        """Resolve the spot color name from page color space definitions.

        Looks through the page's color spaces for Separation entries
        and returns the first colorant name found.
        """
        for page in document.pages:
            if page.page_num != page_num:
                continue
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type == color_space and cs.colorant_names:
                    colorant = cs.colorant_names[0]
                    if colorant not in ("All", "None"):
                        return colorant
        return None

    @staticmethod
    def _is_cmyk_workflow(document: SemanticDocument) -> bool:
        """Determine if the document uses a CMYK workflow from output intents."""
        for oi in document.output_intents:
            for val in (
                str(oi.get("/DestOutputProfileRef", "")),
                str(oi.get("/Info", "")),
                str(oi.get("/OutputConditionIdentifier", "")),
                str(oi.get("/S", "")),
            ):
                if "CMYK" in val.upper() or "FOGRA" in val.upper() or "SWOP" in val.upper():
                    return True
        return False
