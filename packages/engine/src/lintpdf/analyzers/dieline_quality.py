"""Dieline-quality findings (Batches 4+5 — Tier-3 dieline wedge).

Runs against a resolved ``DielineResult`` + the raw PDF bytes and
emits up to six findings per job:

* ``LPDF_DIE_ZORDER`` — dieline drawn below artwork (T3-D02).
* ``LPDF_DIE_KNOCKOUT`` — dieline stroke set to knockout instead
  of overprint (T3-D03).
* ``LPDF_DIE_AS_ART`` — dieline spot used as a fill, so the cutter
  will follow the filled region as a massive closed path (T3-D15).
  Canonical Canva-export bug — unique to lintPDF per the
  competitive audit.
* ``LPDF_DIE_LAYER_CONTENT`` — non-dieline paint ops inside a
  dieline-named OCG marked-content block (T3-D01). Catches the
  Illustrator "dropped an image on the Dieline layer" mistake.
* ``LPDF_DIE_CONTENT_OUTSIDE`` — non-dieline content whose bbox
  extends beyond the dieline polygon envelope (T3-D05). Uses the
  detector's per-region bboxes rather than the trim box so
  non-rectangular products (round labels, shaped packaging) are
  measured tightly.
* ``LPDF_DIE_VARNISH_COLLISION`` — varnish spot paints inside a
  VarnishFree region (T3-D10). Common coating mistake on packaging.

Shares no state with the detector module in ``dieline.py``. The
detector says *where* the dieline is; this module says *what's
wrong with how it's used*. Keeps the 1000-LOC detector focused and
my quality walker self-contained.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from lintpdf.analyzers.finding import Finding, Severity

__all__ = ["check_dieline_quality"]

logger = logging.getLogger(__name__)

# Threshold below which a filled dieline area is emitted as advisory
# rather than error. 50 pt² ≈ 7 x 7 pt ≈ 2.5mm square — below that
# it's almost certainly a tick-mark or trim marker, not actual
# filled artwork in the cutter spot.
_AS_ART_SMALL_AREA_PTS2 = 50.0


def check_dieline_quality(
    pdf_bytes: bytes,
    *,
    spot_name: str | None,
    source: str,
    regions: list[dict[str, float]] | None = None,
    content_outside_tolerance_pts: float = 2.83,
    max_bleed_mm: float | None = None,
    polylines: list[list[list[float]]] | None = None,
    min_dieline_feature_mm: float = 1.0,
    min_dieline_segment_length_mm: float = 1.0,
    white_coverage_min: float = 0.95,
) -> list[Finding]:
    """Emit dieline-quality findings for a resolved dieline.

    Args:
        pdf_bytes: Raw PDF.
        spot_name: ``DielineResult.spot_name`` — Required for the
            spot-based checks (T3-D02/03/15). When ``None`` those
            checks silently skip but the OCG-based T3-D01 and
            varnish T3-D10 can still fire because they rely on
            separate signals.
        source: ``DielineResult.source`` — ``"name"`` / ``"vision"``
            / ``"missing"``. Silent (all findings) when ``"missing"``.
        regions: ``DielineResult.regions`` — per-island bbox list
            used by T3-D05 (content-outside-polygon) to compute the
            dieline envelope. Each dict has ``x0``, ``y0``, ``x1``,
            ``y1`` keys. ``None`` / empty disables T3-D05.
        content_outside_tolerance_pts: how far a paint bbox may
            extend past the dieline envelope before T3-D05 fires
            (default 2.83pt ≈ 1mm).

    Returns:
        Up to six findings. Empty when the preconditions aren't met
        or the content-stream walk fails.
    """
    # T3-D10 (varnish collision) can fire without any dieline detection,
    # so we DON'T early-return on source=="missing" — each sub-check
    # gates on its own preconditions below. We do need pdf_bytes to
    # walk the content stream.
    if not pdf_bytes:
        return []

    try:
        signals = _walk_page_one(pdf_bytes, spot_name)
    except Exception:
        logger.exception("dieline_quality: walker failed")
        return []

    findings: list[Finding] = []

    # T3-D02 — z-order. Fires when dieline was painted AT LEAST once
    # AND non-dieline content was painted AFTER the last dieline
    # paint op. Gated on spot_name because it only makes sense when
    # we have a dieline spot.
    if (
        spot_name
        and signals.last_dieline_paint_idx >= 0
        and signals.last_nondieline_paint_idx > signals.last_dieline_paint_idx
    ):
        findings.append(
            Finding(
                inspection_id="LPDF_DIE_ZORDER",
                severity=Severity.WARNING,
                message=(
                    f"Dieline '{spot_name}' is drawn below artwork "
                    f"(last dieline paint at operator "
                    f"#{signals.last_dieline_paint_idx}, non-dieline paint "
                    f"continued to operator #{signals.last_nondieline_paint_idx})"
                ),
                page_num=1,
                details={
                    "spot_name": spot_name,
                    "last_dieline_paint_idx": signals.last_dieline_paint_idx,
                    "last_nondieline_paint_idx": signals.last_nondieline_paint_idx,
                },
                iso_clause="ISO 19593-1 §5.3",
                object_id=spot_name,
                object_type="spot_color",
            )
        )

    # T3-D03 — knockout. Fires when ANY stroke operator painted the
    # dieline spot while OP=false on the current graphics state.
    if spot_name and signals.knockout_stroke_count > 0:
        findings.append(
            Finding(
                inspection_id="LPDF_DIE_KNOCKOUT",
                severity=Severity.WARNING,
                message=(
                    f"Dieline '{spot_name}' is set to knockout "
                    f"({signals.knockout_stroke_count} stroke(s) with OP=false) "
                    f"— underlying inks will have gaps along cut lines"
                ),
                page_num=1,
                details={
                    "spot_name": spot_name,
                    "knockout_stroke_count": signals.knockout_stroke_count,
                    "first_violation_op_idx": signals.first_knockout_op_idx,
                },
                iso_clause="ISO 32000-2:2020 11.7.4.4",
                object_id=spot_name,
                object_type="spot_color",
            )
        )

    # T3-D15 — used as art. Fires when the dieline spot was the
    # current fill colour at any fill operator. Severity escalates
    # from advisory to error when the total filled area is large
    # enough to indicate real artwork (not a tiny tick mark).
    if spot_name and signals.fill_as_dieline_count > 0:
        area_pts2 = signals.fill_as_dieline_area_pts2
        is_large = area_pts2 >= _AS_ART_SMALL_AREA_PTS2
        severity = Severity.ERROR if is_large else Severity.ADVISORY
        area_cm2 = area_pts2 * (0.352778 / 10) ** 2  # pt² → cm²
        findings.append(
            Finding(
                inspection_id="LPDF_DIE_AS_ART",
                severity=severity,
                message=(
                    f"Dieline spot '{spot_name}' used as fill on page 1 "
                    f"({signals.fill_as_dieline_count} fill op(s), "
                    f"~{area_cm2:.2f} cm² total) — cutter will follow the "
                    f"filled region"
                ),
                page_num=1,
                details={
                    "spot_name": spot_name,
                    "fill_operator_count": signals.fill_as_dieline_count,
                    "fill_area_pts2": round(area_pts2, 2),
                    "fill_area_cm2": round(area_cm2, 4),
                    "first_violation_op_idx": signals.first_fill_as_dieline_idx,
                    "is_large": is_large,
                },
                iso_clause="ISO 19593-1 §5.3",
                object_id=spot_name,
                object_type="spot_color",
            )
        )

    # T3-D01 — content on dieline layer (OCG-based). Fires when the
    # walker saw non-dieline paint ops inside a dieline-named OCG
    # marked-content block.
    if signals.layer_content_count > 0:
        findings.append(
            Finding(
                inspection_id="LPDF_DIE_LAYER_CONTENT",
                severity=Severity.WARNING,
                message=(
                    f"Dieline layer {signals.dieline_ocg_names} contains "
                    f"{signals.layer_content_count} non-dieline paint "
                    f"operation(s) on page 1 — artwork on the cutter plate"
                ),
                page_num=1,
                details={
                    "ocg_names": signals.dieline_ocg_names,
                    "foreign_paint_count": signals.layer_content_count,
                    "first_violation_op_idx": signals.layer_content_first_op_idx,
                },
                iso_clause="ISO 19593-1 §5.3",
                object_type="dieline_layer",
            )
        )

    # T3-D05 — content outside dieline polygon (envelope-based).
    # Uses DielineResult.regions to compute the axis-aligned envelope
    # and flags paint bboxes that extend past it by >tolerance.
    #
    # T3-D04 (LPDF_DIE_EXCESSIVE_BLEED) rides the same envelope
    # computation but measures overhang against ``max_bleed_mm``
    # instead of the smaller `content_outside_tolerance_pts`. Both
    # findings can co-fire when content both crosses the envelope AND
    # exceeds the max-bleed allowance.
    envelope: tuple[float, float, float, float] | None = None
    if regions and signals.foreign_content_bboxes:
        envelope = _envelope_of_regions(regions)
        if envelope is not None:
            outside: list[tuple[float, float, float, float]] = []
            max_overhang = 0.0
            for bbox in signals.foreign_content_bboxes:
                overhang = _bbox_overhang(bbox, envelope)
                if overhang > content_outside_tolerance_pts:
                    outside.append(bbox)
                    max_overhang = max(max_overhang, overhang)
            if outside:
                worst = max(outside, key=lambda b: _bbox_overhang(b, envelope))
                findings.append(
                    Finding(
                        inspection_id="LPDF_DIE_CONTENT_OUTSIDE",
                        severity=Severity.WARNING,
                        message=(
                            f"{len(outside)} content region(s) extend beyond "
                            f"the dieline polygon by >{content_outside_tolerance_pts:.2f}pt "
                            f"on page 1 (max overhang {max_overhang:.2f}pt)"
                        ),
                        page_num=1,
                        details={
                            "foreign_content_count": len(outside),
                            "max_overhang_pts": round(max_overhang, 2),
                            "dieline_envelope_pts": list(envelope),
                            "worst_paint_bbox_pts": list(worst),
                            "tolerance_pts": content_outside_tolerance_pts,
                        },
                        iso_clause="ISO 15930-7:2010 6.2.4",
                        object_type="dieline_polygon",
                    )
                )

    # T3-D04 — excessive bleed past the dieline. Uses the same
    # envelope computed above, measures overhang against max_bleed_mm
    # (1mm ≈ 2.83pt).
    if (
        max_bleed_mm is not None
        and max_bleed_mm > 0
        and envelope is not None
        and signals.foreign_content_bboxes
    ):
        max_bleed_pts = max_bleed_mm / 0.352778
        excessive: list[tuple[float, float, float, float]] = []
        worst_overhang_pts = 0.0
        for bbox in signals.foreign_content_bboxes:
            overhang = _bbox_overhang(bbox, envelope)
            if overhang > max_bleed_pts:
                excessive.append(bbox)
                worst_overhang_pts = max(worst_overhang_pts, overhang)
        if excessive:
            worst_bbox = max(excessive, key=lambda b: _bbox_overhang(b, envelope))
            worst_overhang_mm = worst_overhang_pts * 0.352778
            findings.append(
                Finding(
                    inspection_id="LPDF_DIE_EXCESSIVE_BLEED",
                    severity=Severity.ADVISORY,
                    message=(
                        f"{len(excessive)} content region(s) extend past the "
                        f"dieline by more than {max_bleed_mm:.2f}mm on page 1 "
                        f"(max overhang {worst_overhang_mm:.2f}mm)"
                    ),
                    page_num=1,
                    details={
                        "excessive_count": len(excessive),
                        "max_overhang_mm": round(worst_overhang_mm, 3),
                        "max_overhang_pts": round(worst_overhang_pts, 2),
                        "max_bleed_mm": max_bleed_mm,
                        "dieline_envelope_pts": list(envelope),
                        "worst_paint_bbox_pts": list(worst_bbox),
                    },
                    iso_clause="ISO 15930-7:2010 6.2.4",
                    object_type="dieline_polygon",
                )
            )

    # T3-D10 — varnish / VarnishFree collision.
    if signals.varnish_spots and signals.varnish_free_spots:
        varnish_union = _bbox_union(signals.varnish_spots_bboxes)
        free_union = _bbox_union(signals.varnish_free_spots_bboxes)
        if varnish_union and free_union:
            intersection = _bbox_intersect(varnish_union, free_union)
            if intersection:
                area_pts2 = (intersection[2] - intersection[0]) * (
                    intersection[3] - intersection[1]
                )
                if area_pts2 >= 50.0:
                    area_cm2 = area_pts2 * (0.352778 / 10) ** 2
                    findings.append(
                        Finding(
                            inspection_id="LPDF_DIE_VARNISH_COLLISION",
                            severity=Severity.WARNING,
                            message=(
                                f"Varnish spot '{signals.varnish_spots[0]}' overlaps "
                                f"VarnishFree region by ~{area_cm2:.2f} cm²"
                            ),
                            page_num=1,
                            details={
                                "varnish_spot": signals.varnish_spots[0],
                                "varnish_free_spot": signals.varnish_free_spots[0],
                                "overlap_area_pts2": round(area_pts2, 2),
                                "overlap_area_cm2": round(area_cm2, 4),
                                "intersection_bbox_pts": list(intersection),
                            },
                            iso_clause="ISO 19593-1 §5.3",
                            object_id=signals.varnish_spots[0],
                            object_type="spot_color",
                        )
                    )

    # T3-D08 — small dieline features that won't die-cut cleanly.
    # Walks DielineResult.polylines for any subpath whose perimeter
    # < min_segment_length_mm OR whose bbox is < min_feature_size_mm
    # in either dimension.
    if polylines:
        small_polys = _find_small_polygons(
            polylines,
            min_feature_mm=min_dieline_feature_mm,
            min_perimeter_mm=min_dieline_segment_length_mm,
        )
        if small_polys:
            smallest = min(small_polys, key=lambda p: min(p["width_mm"], p["height_mm"]))
            findings.append(
                Finding(
                    inspection_id="LPDF_DIE_TOO_SMALL",
                    severity=Severity.WARNING,
                    message=(
                        f"{len(small_polys)} dieline feature(s) below "
                        f"{min_dieline_feature_mm:.1f}mm cutting threshold "
                        f"(smallest: {smallest['width_mm']:.2f}x"
                        f"{smallest['height_mm']:.2f}mm)"
                    ),
                    page_num=1,
                    details={
                        "feature_count": len(small_polys),
                        "min_feature_size_mm": min_dieline_feature_mm,
                        "min_segment_length_mm": min_dieline_segment_length_mm,
                        "smallest_width_mm": round(smallest["width_mm"], 3),
                        "smallest_height_mm": round(smallest["height_mm"], 3),
                        "smallest_perimeter_mm": round(smallest["perimeter_mm"], 3),
                    },
                    iso_clause="ISO 19593-1 §5.3 / cutter resolution",
                    object_type="dieline_polygon",
                )
            )

    # T3-D09 — white underprint coverage gap. White-spot bbox area
    # vs dieline envelope area; fires when coverage < threshold.
    if signals.white_spots and signals.white_spots_bboxes and regions and white_coverage_min > 0:
        envelope = _envelope_of_regions(regions)
        if envelope is not None:
            envelope_area = (envelope[2] - envelope[0]) * (envelope[3] - envelope[1])
            if envelope_area > 0:
                white_union = _bbox_union(signals.white_spots_bboxes)
                if white_union is not None:
                    intersection = _bbox_intersect(white_union, envelope)
                    covered_area = (
                        (intersection[2] - intersection[0]) * (intersection[3] - intersection[1])
                        if intersection
                        else 0.0
                    )
                    coverage_pct = (covered_area / envelope_area) * 100.0
                    if coverage_pct < white_coverage_min * 100.0:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_DIE_WHITE_GAP",
                                severity=Severity.WARNING,
                                message=(
                                    f"White underprint covers {coverage_pct:.1f}% "
                                    f"of dieline area — gaps will let substrate "
                                    f"show through colour artwork"
                                ),
                                page_num=1,
                                details={
                                    "white_spot": signals.white_spots[0],
                                    "white_coverage_pct": round(coverage_pct, 2),
                                    "white_coverage_min_pct": white_coverage_min * 100.0,
                                    "dieline_area_pts2": round(envelope_area, 2),
                                    "white_area_pts2": round(covered_area, 2),
                                    "dieline_envelope_pts": list(envelope),
                                },
                                iso_clause="ISO 19593-1 §5.3 / White underprint",
                                object_id=signals.white_spots[0],
                                object_type="spot_color",
                            )
                        )

    return findings


def _find_small_polygons(
    polylines: list[list[list[float]]],
    *,
    min_feature_mm: float,
    min_perimeter_mm: float,
) -> list[dict[str, float]]:
    """Return per-polygon size metrics for polygons below cutter
    resolution thresholds.

    A polygon counts as "too small" when ANY of:
      - bbox width < min_feature_mm
      - bbox height < min_feature_mm
      - perimeter < min_perimeter_mm

    Returns dicts with width_mm, height_mm, perimeter_mm, area_mm2 for
    every too-small polygon (caller picks the worst).
    """
    import math

    out: list[dict[str, float]] = []
    pt_to_mm = 0.352778
    for poly in polylines:
        if not poly or len(poly) < 2:
            continue
        try:
            xs = [float(p[0]) for p in poly]
            ys = [float(p[1]) for p in poly]
        except (IndexError, TypeError, ValueError):
            continue
        width_pts = max(xs) - min(xs)
        height_pts = max(ys) - min(ys)
        perim_pts = 0.0
        for i in range(len(poly) - 1):
            try:
                dx = float(poly[i + 1][0]) - float(poly[i][0])
                dy = float(poly[i + 1][1]) - float(poly[i][1])
                perim_pts += math.hypot(dx, dy)
            except (IndexError, TypeError, ValueError):
                continue
        width_mm = width_pts * pt_to_mm
        height_mm = height_pts * pt_to_mm
        perim_mm = perim_pts * pt_to_mm
        if width_mm < min_feature_mm or height_mm < min_feature_mm or perim_mm < min_perimeter_mm:
            out.append(
                {
                    "width_mm": width_mm,
                    "height_mm": height_mm,
                    "perimeter_mm": perim_mm,
                    "area_mm2": width_mm * height_mm,
                }
            )
    return out


# ────────────────────────────────────────────────────────────────────
# Bbox geometry helpers
# ────────────────────────────────────────────────────────────────────


def _envelope_of_regions(
    regions: list[dict[str, float]],
) -> tuple[float, float, float, float] | None:
    """Axis-aligned union of ``DielineResult.regions`` bboxes."""
    bboxes: list[tuple[float, float, float, float]] = []
    for r in regions:
        try:
            bboxes.append((float(r["x0"]), float(r["y0"]), float(r["x1"]), float(r["y1"])))
        except (KeyError, TypeError, ValueError):
            continue
    return _bbox_union(bboxes)


def _bbox_union(
    bboxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    if not bboxes:
        return None
    x0 = min(b[0] for b in bboxes)
    y0 = min(b[1] for b in bboxes)
    x1 = max(b[2] for b in bboxes)
    y1 = max(b[3] for b in bboxes)
    return (x0, y0, x1, y1)


def _bbox_intersect(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float] | None:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x0 >= x1 or y0 >= y1:
        return None
    return (x0, y0, x1, y1)


def _bbox_overhang(
    paint_bbox: tuple[float, float, float, float],
    envelope: tuple[float, float, float, float],
) -> float:
    """Return the max distance (points) the paint bbox sticks out of
    the envelope on any side. 0 when fully contained."""
    return max(
        0.0,
        envelope[0] - paint_bbox[0],
        envelope[1] - paint_bbox[1],
        paint_bbox[2] - envelope[2],
        paint_bbox[3] - envelope[3],
    )


# ────────────────────────────────────────────────────────────────────
# Internal walker
# ────────────────────────────────────────────────────────────────────


class _QualitySignals:
    """Mutable scratch-pad the walker fills in."""

    __slots__ = (
        "dieline_ocg_names",
        "fill_as_dieline_area_pts2",
        "fill_as_dieline_count",
        "first_fill_as_dieline_idx",
        "first_knockout_op_idx",
        "foreign_content_bboxes",
        "foreign_content_max_overhang_pts",
        "knockout_stroke_count",
        "last_dieline_paint_idx",
        "last_nondieline_paint_idx",
        "layer_content_count",
        "layer_content_first_op_idx",
        "varnish_free_spots",
        "varnish_free_spots_bboxes",
        "varnish_spots",
        "varnish_spots_bboxes",
        "white_spots",
        "white_spots_bboxes",
    )

    def __init__(self) -> None:
        self.last_dieline_paint_idx: int = -1
        self.last_nondieline_paint_idx: int = -1
        self.knockout_stroke_count: int = 0
        self.first_knockout_op_idx: int = -1
        self.fill_as_dieline_count: int = 0
        self.fill_as_dieline_area_pts2: float = 0.0
        self.first_fill_as_dieline_idx: int = -1
        # T3-D01 — OCG-based layer-content detection.
        self.dieline_ocg_names: list[str] = []
        self.layer_content_count: int = 0
        self.layer_content_first_op_idx: int = -1
        # T3-D05 — paint bboxes outside the dieline envelope.
        self.foreign_content_bboxes: list[tuple[float, float, float, float]] = []
        self.foreign_content_max_overhang_pts: float = 0.0
        # T3-D10 — varnish / VarnishFree spot bboxes.
        self.varnish_spots: list[str] = []
        self.varnish_spots_bboxes: list[tuple[float, float, float, float]] = []
        self.varnish_free_spots: list[str] = []
        self.varnish_free_spots_bboxes: list[tuple[float, float, float, float]] = []
        # T3-D09 — white-spot bboxes for white-coverage calc.
        self.white_spots: list[str] = []
        self.white_spots_bboxes: list[tuple[float, float, float, float]] = []


# Paint operators split into stroke-only, fill-only, both.
_STROKE_OPS = {"S", "s"}
_FILL_OPS = {"f", "F", "f*"}
_STROKE_AND_FILL_OPS = {"B", "B*", "b", "b*"}


# T3-D01 — tokens that identify a dieline OCG / layer.
_DIELINE_NAME_TOKENS = frozenset(
    {
        "die",
        "dieline",
        "die line",
        "die-line",
        "cut",
        "cutcontour",
        "cut contour",
        "cut-contour",
        "cutter",
        "crease",
        "perf",
        "perforation",
        "score",
        "fold",
        "kiss",
        "through-cut",
    }
)

# T3-D10 — closed lexicon of varnish / coating spot names.
_VARNISH_NAME_TOKENS = frozenset(
    {
        "varnish",
        "uv",
        "uvvarnish",
        "uv varnish",
        "aq",
        "aqcoat",
        "aquacoat",
        "aqua coat",
        "gloss",
        "matte",
        "spotuv",
        "spot uv",
        "softtouch",
        "soft touch",
        "coating",
    }
)

_VARNISH_FREE_NAME_TOKENS = frozenset(
    {
        "varnishfree",
        "varnish free",
        "varnish-free",
        "novarnish",
        "no varnish",
        "no-varnish",
        "coatingfree",
        "coating free",
        "coating-free",
        "nocoating",
        "no coating",
        "no-coating",
    }
)


def _normalise_spot_name(name: str) -> str:
    """Lowercase + collapse separators for spot-name matching."""
    out = name.strip().lstrip("/").lower()
    out = out.replace("_", " ").replace("-", " ")
    while "  " in out:
        out = out.replace("  ", " ")
    return out


def _is_dieline_name(name: str) -> bool:
    norm = _normalise_spot_name(name)
    return any(tok in norm for tok in _DIELINE_NAME_TOKENS)


def _is_varnish_name(name: str) -> bool:
    norm = _normalise_spot_name(name)
    return any(tok == norm or tok in norm.split() for tok in _VARNISH_NAME_TOKENS)


def _is_varnish_free_name(name: str) -> bool:
    norm = _normalise_spot_name(name)
    # Require "free" or "no" to appear — avoids catching plain "varnish"
    # as a free-marker spot.
    if "free" not in norm and "no " not in norm and norm[:2] != "no":
        return False
    return any(tok in norm for tok in _VARNISH_FREE_NAME_TOKENS)


# T3-D09 — closed lexicon of white / underprint spot names.
_WHITE_NAME_TOKENS = frozenset(
    {
        "white",
        "opaque white",
        "opaquewhite",
        "whiteunder",
        "white under",
        "whiteunderprint",
        "white underprint",
    }
)


def _is_white_name(name: str) -> bool:
    norm = _normalise_spot_name(name)
    return any(tok == norm or tok in norm.split(",") for tok in _WHITE_NAME_TOKENS) or (
        norm in _WHITE_NAME_TOKENS
    )


def _walk_page_one(pdf_bytes: bytes, spot_name: str | None) -> _QualitySignals:
    import io

    import pikepdf

    signals = _QualitySignals()

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        try:
            page = pdf.pages[0]
        except Exception:
            return signals
        resources = page.get("/Resources") if hasattr(page, "get") else None
        cs_dict = resources.get("/ColorSpace") if resources and hasattr(resources, "get") else None
        extgstate_dict = (
            resources.get("/ExtGState") if resources and hasattr(resources, "get") else None
        )
        props_dict = (
            resources.get("/Properties") if resources and hasattr(resources, "get") else None
        )

        # resource name → spot name for Separation colour spaces.
        cs_to_spot = _build_cs_to_spot(cs_dict)
        # T3-D10 — record which resource names resolve to varnish /
        # VarnishFree spots so we can tally their paint bboxes.
        for spot in cs_to_spot.values():
            if _is_varnish_free_name(spot) and spot not in signals.varnish_free_spots:
                signals.varnish_free_spots.append(spot)
            elif _is_varnish_name(spot) and spot not in signals.varnish_spots:
                signals.varnish_spots.append(spot)
            if _is_white_name(spot) and spot not in signals.white_spots:
                signals.white_spots.append(spot)

        # T3-D01 — build resource-name → OCG-name map so BDC /OC
        # /Resource blocks resolve to the actual optional-content
        # group label.
        prop_to_ocg_name = _build_prop_to_ocg_name(props_dict)

        # Current graphics-state tracking.
        current_stroke_cs: str | None = None
        current_fill_cs: str | None = None
        # Stack of open dieline-named OCG marked-content blocks.
        ocg_stack: list[str] = []
        # Stroking / non-stroking overprint flags (ISO 32000-2 §11.7.4.4).
        # Default is `false` per spec. OP governs painting ops other than
        # image/path fill; op (lowercase) governs fill specifically when
        # explicitly set. We track the stroking flag for T3-D03.
        op_stroke: bool = False

        # Compound-path subpath accumulator — we need total bbox area
        # for T3-D15 severity escalation.
        path_subpath_areas_pts2: list[float] = []
        current_subpath_points: list[tuple[float, float]] = []
        # Bbox history for the current compound path — refreshed when
        # a paint op runs. Batch 5 T3-D05 / T3-D10 consume this list.
        current_subpath_points_history: list[tuple[float, float, float, float]] = []

        def finish_subpath() -> None:
            if not current_subpath_points:
                return
            xs = [p[0] for p in current_subpath_points]
            ys = [p[1] for p in current_subpath_points]
            area = max(0.0, max(xs) - min(xs)) * max(0.0, max(ys) - min(ys))
            path_subpath_areas_pts2.append(area)
            current_subpath_points_history.append((min(xs), min(ys), max(xs), max(ys)))
            current_subpath_points.clear()

        try:
            instrs = pikepdf.parse_content_stream(page)
        except Exception:
            return signals

        for op_idx, inst in enumerate(instrs):
            try:
                op = str(inst.operator)
                operands = list(getattr(inst, "operands", []))
            except Exception:
                continue

            # Colour-space setters.
            if op == "CS" and operands:
                current_stroke_cs = str(operands[0]).lstrip("/")
            elif op == "cs" and operands:
                current_fill_cs = str(operands[0]).lstrip("/")

            # Graphics-state parameter dict reference: `gs /GSName` looks
            # up the ExtGState entry and applies its fields. We pull OP
            # from the referenced dict when present.
            elif op == "gs" and operands and extgstate_dict is not None:
                try:
                    gs_name = str(operands[0]).lstrip("/")
                    gs_entry = extgstate_dict.get("/" + gs_name)
                    if gs_entry is not None and hasattr(gs_entry, "get"):
                        op_value = gs_entry.get("/OP")
                        if op_value is not None:
                            op_stroke = bool(op_value)
                except Exception:
                    pass

            # Path-construction operators that contribute to subpath area.
            elif op == "m" and len(operands) >= 2:
                finish_subpath()
                with contextlib.suppress(ValueError, TypeError):
                    current_subpath_points.append((float(operands[0]), float(operands[1])))
            elif op == "l" and len(operands) >= 2:
                with contextlib.suppress(ValueError, TypeError):
                    current_subpath_points.append((float(operands[0]), float(operands[1])))
            elif op == "re" and len(operands) >= 4:
                try:
                    x = float(operands[0])
                    y = float(operands[1])
                    w = float(operands[2])
                    h = float(operands[3])
                    finish_subpath()
                    current_subpath_points.extend([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
                    finish_subpath()
                except (ValueError, TypeError):
                    pass
            elif op in ("c", "v", "y") and len(operands) >= 2:
                with contextlib.suppress(ValueError, TypeError):
                    current_subpath_points.append((float(operands[-2]), float(operands[-1])))

            # Marked-content blocks — BDC /OC /Resource → push the
            # referenced OCG name onto the stack if it's a dieline
            # layer; EMC → pop.
            elif op == "BDC" and len(operands) >= 2:
                # Operand 0 is the tag (/OC, /Layer, /Artifact…);
                # operand 1 is the property name or property dict.
                try:
                    tag = str(operands[0]).lstrip("/")
                    if tag == "OC":
                        prop_name = str(operands[1]).lstrip("/")
                        ocg_label = prop_to_ocg_name.get(prop_name, "")
                        if _is_dieline_name(ocg_label):
                            ocg_stack.append(ocg_label)
                            if ocg_label not in signals.dieline_ocg_names:
                                signals.dieline_ocg_names.append(ocg_label)
                        else:
                            # Push an empty sentinel so the matching
                            # EMC still pops cleanly.
                            ocg_stack.append("")
                    else:
                        ocg_stack.append("")
                except Exception:
                    ocg_stack.append("")
            elif op == "BMC":
                ocg_stack.append("")
            elif op == "EMC":
                if ocg_stack:
                    ocg_stack.pop()

            # Paint operators — drive the signal gathering.
            elif op in _STROKE_OPS or op in _FILL_OPS or op in _STROKE_AND_FILL_OPS:
                finish_subpath()
                area = sum(path_subpath_areas_pts2)

                stroke_is_dieline = (
                    op in _STROKE_OPS or op in _STROKE_AND_FILL_OPS
                ) and _cs_is_dieline(current_stroke_cs, cs_to_spot, spot_name)
                fill_is_dieline = (
                    op in _FILL_OPS or op in _STROKE_AND_FILL_OPS
                ) and _cs_is_dieline(current_fill_cs, cs_to_spot, spot_name)

                # Pre-compute the paint bbox — union of subpath bboxes
                # for the current compound path. Used by T3-D05 and
                # T3-D10.
                paint_bbox = _bbox_union(current_subpath_points_history)

                # T3-D02 z-order signal.
                if stroke_is_dieline or fill_is_dieline:
                    signals.last_dieline_paint_idx = op_idx
                else:
                    signals.last_nondieline_paint_idx = op_idx

                # T3-D03 knockout signal — stroked in dieline spot with
                # OP=false.
                if stroke_is_dieline and not op_stroke:
                    signals.knockout_stroke_count += 1
                    if signals.first_knockout_op_idx < 0:
                        signals.first_knockout_op_idx = op_idx

                # T3-D15 fill-as-dieline signal.
                if fill_is_dieline:
                    signals.fill_as_dieline_count += 1
                    signals.fill_as_dieline_area_pts2 += area
                    if signals.first_fill_as_dieline_idx < 0:
                        signals.first_fill_as_dieline_idx = op_idx

                # T3-D01 — any paint inside a dieline-named OCG that's
                # NOT using the dieline spot is foreign content on the
                # cutter plate.
                in_dieline_ocg = any(n for n in ocg_stack if _is_dieline_name(n))
                if in_dieline_ocg and not (stroke_is_dieline or fill_is_dieline):
                    signals.layer_content_count += 1
                    if signals.layer_content_first_op_idx < 0:
                        signals.layer_content_first_op_idx = op_idx

                # T3-D05 — record all non-dieline paint bboxes so the
                # caller can compare them against the dieline envelope.
                if paint_bbox and not (stroke_is_dieline or fill_is_dieline):
                    signals.foreign_content_bboxes.append(paint_bbox)

                # T3-D10 — record paint bboxes keyed by their spot type.
                if paint_bbox:
                    stroke_spot = _cs_mapped_spot(current_stroke_cs, cs_to_spot)
                    fill_spot = _cs_mapped_spot(current_fill_cs, cs_to_spot)
                    touched_spots = {s for s in (stroke_spot, fill_spot) if s}
                    for s in touched_spots:
                        if s in signals.varnish_spots:
                            signals.varnish_spots_bboxes.append(paint_bbox)
                        if s in signals.varnish_free_spots:
                            signals.varnish_free_spots_bboxes.append(paint_bbox)
                        if s in signals.white_spots:
                            signals.white_spots_bboxes.append(paint_bbox)

                path_subpath_areas_pts2.clear()
                current_subpath_points_history.clear()

            # `n` ends a path without painting — just discard the path.
            elif op == "n":
                finish_subpath()
                path_subpath_areas_pts2.clear()

    return signals


def _cs_is_dieline(
    cs_name: str | None,
    cs_to_spot: dict[str, str],
    spot_name: str | None,
) -> bool:
    """Resolve a colour-space name to its Separation spot and compare.

    Returns False when ``spot_name`` is None (Batch 4 spot-based checks
    rely on knowing which spot counts as dieline; when the caller hasn't
    provided one, no paint op qualifies as dieline).
    """
    if cs_name is None or spot_name is None:
        return False
    mapped = cs_to_spot.get(cs_name)
    return mapped == spot_name


def _cs_mapped_spot(
    cs_name: str | None,
    cs_to_spot: dict[str, str],
) -> str | None:
    """Return the spot colourant name mapped to ``cs_name``, or None."""
    if cs_name is None:
        return None
    return cs_to_spot.get(cs_name)


def _build_prop_to_ocg_name(props_dict: Any) -> dict[str, str]:
    """Map ``/Properties`` resource names to their OCG `/Name`.

    BDC operators tagged ``/OC /SomeProp`` look up the OCG via the
    page's /Resources /Properties dict. Without this map the walker
    can't tell whether a marked-content block is on a dieline layer.
    """
    out: dict[str, str] = {}
    if props_dict is None:
        return out
    try:
        items = props_dict.items() if hasattr(props_dict, "items") else []
    except Exception:
        return out
    for key, value in items:
        try:
            res_name = str(key).lstrip("/")
            if not hasattr(value, "get"):
                continue
            ocg_type = value.get("/Type")
            if ocg_type is not None and str(ocg_type).lstrip("/") != "OCG":
                continue
            ocg_name = value.get("/Name")
            if ocg_name is not None:
                out[res_name] = str(ocg_name)
        except Exception:
            continue
    return out


def _build_cs_to_spot(cs_dict: Any) -> dict[str, str]:
    """Map each Separation resource name to its colourant spot name.

    Walks the page's ``/Resources /ColorSpace`` dict, looks for arrays
    that start with ``/Separation``, and records the second element as
    the colourant name.
    """
    out: dict[str, str] = {}
    if cs_dict is None:
        return out
    try:
        items = cs_dict.items() if hasattr(cs_dict, "items") else []
    except Exception:
        return out
    for key, value in items:
        try:
            name = str(key).lstrip("/")
            if not hasattr(value, "__getitem__"):
                continue
            # Colour-space array: [/Separation  /SpotName  /Alternate  <tintTransform>]
            first = value[0] if len(value) > 0 else None
            if str(first).lstrip("/") != "Separation":
                continue
            spot = value[1] if len(value) > 1 else None
            if spot is not None:
                out[name] = str(spot).lstrip("/")
        except Exception:
            continue
    return out
