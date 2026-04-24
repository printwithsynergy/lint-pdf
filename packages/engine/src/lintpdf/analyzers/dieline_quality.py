"""Dieline-quality findings (Batch 4 — T3-D02 / T3-D03 / T3-D15).

Runs against a resolved ``DielineResult`` + the raw PDF bytes and
emits up to three findings per job:

* ``LPDF_DIE_ZORDER`` — dieline drawn below artwork (T3-D02).
* ``LPDF_DIE_KNOCKOUT`` — dieline stroke set to knockout instead
  of overprint (T3-D03).
* ``LPDF_DIE_AS_ART`` — dieline spot used as a fill, so the cutter
  will follow the filled region as a massive closed path (T3-D15).
  Canonical Canva-export bug — unique to lintPDF per the
  competitive audit.

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
# rather than error. 50 pt² ≈ 7 × 7 pt ≈ 2.5mm square — below that
# it's almost certainly a tick-mark or trim marker, not actual
# filled artwork in the cutter spot.
_AS_ART_SMALL_AREA_PTS2 = 50.0


def check_dieline_quality(
    pdf_bytes: bytes,
    *,
    spot_name: str | None,
    source: str,
) -> list[Finding]:
    """Emit dieline-quality findings for a resolved dieline.

    Args:
        pdf_bytes: Raw PDF.
        spot_name: ``DielineResult.spot_name`` (the Separation / OCG
            name the detector matched). Required — when ``None`` no
            findings fire.
        source: ``DielineResult.source`` — ``"name"`` / ``"vision"``
            / ``"missing"``. Silent when ``"missing"``.

    Returns:
        Up to three findings. Empty when the preconditions aren't met
        or the content-stream walk fails.
    """
    if source == "missing" or not spot_name:
        return []
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
    # paint op.
    if (
        signals.last_dieline_paint_idx >= 0
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
    if signals.knockout_stroke_count > 0:
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
    if signals.fill_as_dieline_count > 0:
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

    return findings


# ────────────────────────────────────────────────────────────────────
# Internal walker
# ────────────────────────────────────────────────────────────────────


class _QualitySignals:
    """Mutable scratch-pad the walker fills in."""

    __slots__ = (
        "fill_as_dieline_area_pts2",
        "fill_as_dieline_count",
        "first_fill_as_dieline_idx",
        "first_knockout_op_idx",
        "knockout_stroke_count",
        "last_dieline_paint_idx",
        "last_nondieline_paint_idx",
    )

    def __init__(self) -> None:
        self.last_dieline_paint_idx: int = -1
        self.last_nondieline_paint_idx: int = -1
        self.knockout_stroke_count: int = 0
        self.first_knockout_op_idx: int = -1
        self.fill_as_dieline_count: int = 0
        self.fill_as_dieline_area_pts2: float = 0.0
        self.first_fill_as_dieline_idx: int = -1


# Paint operators split into stroke-only, fill-only, both.
_STROKE_OPS = {"S", "s"}
_FILL_OPS = {"f", "F", "f*"}
_STROKE_AND_FILL_OPS = {"B", "B*", "b", "b*"}


def _walk_page_one(pdf_bytes: bytes, spot_name: str) -> _QualitySignals:
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

        # resource name → spot name for Separation colour spaces.
        cs_to_spot = _build_cs_to_spot(cs_dict)

        # Current graphics-state tracking.
        current_stroke_cs: str | None = None
        current_fill_cs: str | None = None
        # Stroking / non-stroking overprint flags (ISO 32000-2 §11.7.4.4).
        # Default is `false` per spec. OP governs painting ops other than
        # image/path fill; op (lowercase) governs fill specifically when
        # explicitly set. We track the stroking flag for T3-D03.
        op_stroke: bool = False

        # Compound-path subpath accumulator — we need total bbox area
        # for T3-D15 severity escalation.
        path_subpath_areas_pts2: list[float] = []
        current_subpath_points: list[tuple[float, float]] = []

        def finish_subpath() -> None:
            if not current_subpath_points:
                return
            xs = [p[0] for p in current_subpath_points]
            ys = [p[1] for p in current_subpath_points]
            area = max(0.0, max(xs) - min(xs)) * max(0.0, max(ys) - min(ys))
            path_subpath_areas_pts2.append(area)
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

                path_subpath_areas_pts2.clear()

            # `n` ends a path without painting — just discard the path.
            elif op == "n":
                finish_subpath()
                path_subpath_areas_pts2.clear()

    return signals


def _cs_is_dieline(
    cs_name: str | None,
    cs_to_spot: dict[str, str],
    spot_name: str,
) -> bool:
    """Resolve a colour-space name to its Separation spot and compare."""
    if cs_name is None:
        return False
    mapped = cs_to_spot.get(cs_name)
    return mapped == spot_name


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
