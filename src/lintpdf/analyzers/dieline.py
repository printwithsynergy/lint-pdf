"""Dieline detection (WS-D).

Two strategies, tried in order:

1. **Name-match heuristic (always runs first).** Scans the PDF for
   Separation / Spot color names, layer (OCG) names, and page-label
   text for the usual suspects — ``CutContour``, ``Dieline``,
   ``Cut``, ``Crease``, ``Perf``, ``Kiss``, ``Score``, etc. When a
   match is found we mark the dieline as ``source="name"`` and
   collect the rendered polylines for the downstream art-size
   inspector (WS-D art_size).

2. **Sonnet 4.6 visual fallback.** If the name scan returns zero
   hits AND the tenant has ``dieline`` in ``ai_features``, call
   ``lintpdf.ai.dieline_claude.ClaudeDielineFallback`` on a rendered
   page. Sonnet is the only spatial-reasoning call in the pipeline
   and is gated behind the ``sonnet_fallback`` feature too.

When both strategies miss, we emit ``LPDF_DIE_MISSING`` (warning)
and the art-size inspector returns ``None`` — strict, no guessing.
"""

from __future__ import annotations

import contextlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from lintpdf.codex_adapter import extract_codex_document_via_codex

logger = logging.getLogger(__name__)


# Canonical names — lowercased for case-insensitive matching. Matches
# an entire token; partial-substring matches are allowed too so
# "CutContour" and "Cut" both hit the same rule.
_DIELINE_TOKENS: tuple[str, ...] = (
    "cutcontour",
    "cut_contour",
    "dieline",
    "die-line",
    "die line",
    "die",
    "cut",
    "cutter",
    "crease",
    "perf",
    "perforation",
    "bleed",
    "score",
    "kiss",
    "fold",
    "through-cut",
    "through_cut",
)


_TOKEN_RE = re.compile(r"[a-z0-9_\-]+", re.IGNORECASE)


def _name_matches(name: str | None) -> bool:
    """Case-insensitive substring + token match."""
    if not name:
        return False
    lowered = name.lower()
    if any(tok in lowered for tok in _DIELINE_TOKENS):
        return True
    tokens = {t.lower() for t in _TOKEN_RE.findall(lowered)}
    return any(tok in tokens for tok in _DIELINE_TOKENS)


@dataclass(frozen=True)
class DielineResult:
    """Effective dieline detection outcome for a job.

    * ``source`` — ``"name"`` when name-match heuristic hit,
      ``"vision"`` when Sonnet fallback confirmed, ``"missing"``
      when no dieline could be established.
    * ``polylines`` — list of closed polygons in PDF user-space
      points. Each polygon is ``[[x, y], [x, y], ...]``. Empty
      when ``source="missing"``.
    * ``spot_name`` — the matching Separation / OCG name when
      ``source="name"``; ``None`` otherwise.
    * ``confidence`` — 1.0 for the name-match path; the Sonnet
      verdict's self-scored confidence for the vision path; 0.0
      for ``missing``.
    * ``regions`` — per-island bboxes derived from clustering
      ``polylines``. One entry per distinct cut area — used by
      the viewer's Art Info overlay to drop one info icon per
      region so multi-artwork files (circle + rectangle in the
      same PDF) show each size separately.
    * ``multi_color`` — True when the dieline layer paints its
      strokes in more than one distinct color. Triggers
      ``LPDF_DIE_MULTI_COLOR`` downstream because a dieline
      should be a single ink; mixed colors on the cut layer
      are usually misplaced artwork.
    """

    source: str
    polylines: list[list[list[float]]] = field(default_factory=list)
    spot_name: str | None = None
    confidence: float = 0.0
    regions: list[dict[str, float]] = field(default_factory=list)
    multi_color: bool = False


def _collect_spot_names(payload: dict[str, Any]) -> list[str]:
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    names: list[str] = []
    if isinstance(analysis.get("spot_names"), list):
        for raw in analysis["spot_names"]:
            if raw is None:
                continue
            val = str(raw).lstrip("/")
            if val and val not in ("All", "None"):
                names.append(val)
    color_spaces = payload.get("color_spaces")
    if isinstance(color_spaces, list):
        for cs in color_spaces:
            if not isinstance(cs, dict):
                continue
            if cs.get("family") not in {"Separation", "DeviceN"}:
                continue
            for colorant in cs.get("spot_colorants") or []:
                if isinstance(colorant, dict) and colorant.get("name"):
                    val = str(colorant["name"]).lstrip("/")
                    if val and val not in ("All", "None"):
                        names.append(val)
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        key = n.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def _collect_layer_names(payload: dict[str, Any]) -> list[str]:
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    out: list[str] = []
    if isinstance(analysis.get("layer_names"), list):
        for raw in analysis["layer_names"]:
            if raw is None:
                continue
            text = str(raw)
            if text:
                out.append(text)
    ocgs = payload.get("ocgs")
    if isinstance(ocgs, list):
        for ocg in ocgs:
            if isinstance(ocg, dict) and ocg.get("name"):
                out.append(str(ocg["name"]))
    deduped: list[str] = []
    seen: set[str] = set()
    for name in out:
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


# WS-19 geometry fallback — tuning constants.
#
# Corner-mark tolerance: distance in PDF points from each MediaBox
# corner within which a stroked path's bbox counts as a "corner
# mark". Real cut-mark sets usually sit 6–18 pt inside the media
# edge; 30 pt catches slightly offset marks without picking up
# decorative corner glyphs.
_CORNER_TOLERANCE_PT = 30.0

# Rectangle-candidate threshold: how large a stroke-only rectangular
# path must be (as a fraction of MediaBox area) to count as the
# dieline's bounding rectangle. Textbook trim boxes span 60–95 % of
# the MediaBox (the remainder being bleed + marks).
_RECT_AREA_RATIO_MIN = 0.60

# How many of the 4 corners must show a clustered stroke before we
# accept a geometry match. 4 is strict; 3 keeps us honest on files
# where one corner's mark sits just outside the tolerance.
_MIN_CORNERS_FOR_MATCH = 3


def _detect_by_geometry(page_signals: dict[str, Any]) -> tuple[int, float] | None:
    """Return ``(corners_hit, rect_area_ratio)`` when page 1 shows
    the textbook "4 corner trim marks + bounding rectangle" pattern,
    or ``None`` when the heuristic doesn't fire.

    Parses the page-1 content stream, tracks stroke-only path
    bounding boxes, and tests two conditions simultaneously:

    1. At least ``_MIN_CORNERS_FOR_MATCH`` of the 4 MediaBox corners
       have a small stroked path within ``_CORNER_TOLERANCE_PT`` of
       the corner.
    2. At least one stroked rectangle covers ≥ ``_RECT_AREA_RATIO_MIN``
       of the MediaBox area.

    Both must hold for a match. Returns early on the first page —
    dieline geometry lives on page 1 by convention in the corpora
    this heuristic targets.

    CTM transformations are NOT composed (the walker reads raw
    coordinates from ``m / l / re`` operands); axis-aligned page-1
    artwork is handled correctly, rotated or heavily transformed
    dielines will miss and fall through to Sonnet.
    """
    media = page_signals.get("media_box")
    if not isinstance(media, list) or len(media) != 4:
        return None
    try:
        mb_x0, mb_y0, mb_x1, mb_y1 = (float(media[0]), float(media[1]), float(media[2]), float(media[3]))
    except Exception:
        return None
    mb_w = mb_x1 - mb_x0
    mb_h = mb_y1 - mb_y0
    if mb_w <= 0 or mb_h <= 0:
        return None
    mb_area = mb_w * mb_h

    instructions = page_signals.get("content_ops")
    if not isinstance(instructions, list):
        return None

    # Per-path point accumulator — reset on m/re operators that
    # start a new subpath. We don't need perfect path granularity,
    # just a bbox around the current subpath.
    path_points: list[tuple[float, float]] = []
    stroked_bboxes: list[tuple[float, float, float, float]] = []

    def _flush_stroked() -> None:
        if not path_points:
            return
        xs = [p[0] for p in path_points]
        ys = [p[1] for p in path_points]
        stroked_bboxes.append((min(xs), min(ys), max(xs), max(ys)))

    for inst in instructions:
        if not isinstance(inst, dict):
            continue
        op = str(inst.get("op") or "")
        operands = inst.get("operands") if isinstance(inst.get("operands"), list) else []

        # New subpath — m x y
        if op == "m":
            if len(operands) >= 2:
                try:
                    path_points = [(float(operands[0]), float(operands[1]))]
                except Exception:
                    path_points = []
            continue
        # Line to — l x y
        if op == "l":
            if len(operands) >= 2:
                with contextlib.suppress(Exception):
                    path_points.append((float(operands[0]), float(operands[1])))
            continue
        # Curve to (approximated by endpoints for bbox purposes)
        if op in ("c", "v", "y"):
            try:
                x = float(operands[-2])
                y = float(operands[-1])
                path_points.append((x, y))
            except Exception:
                pass
            continue
        # Rectangle — re x y w h (single-shot rectangle path)
        if op == "re":
            if len(operands) >= 4:
                try:
                    x, y, w, h = (float(v) for v in operands[:4])
                    path_points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                except Exception:
                    path_points = []
            continue
        # Close subpath
        if op == "h":
            continue
        # Stroke-only finishers
        if op in ("S", "s"):
            _flush_stroked()
            path_points = []
            continue
        # Anything with a fill (f, F, f*, B, B*, b, b*) — flush without
        # recording as stroked; filled shapes aren't what we want for
        # corner marks / trim rectangles.
        if op in ("f", "F", "f*", "B", "B*", "b", "b*", "n"):
            path_points = []
            continue

    # Evaluate corner coverage.
    corners = [
        (mb_x0, mb_y0),
        (mb_x1, mb_y0),
        (mb_x0, mb_y1),
        (mb_x1, mb_y1),
    ]
    hits = 0
    for cx, cy in corners:
        for bx0, by0, bx1, by1 in stroked_bboxes:
            # Small stroked bbox sitting near the corner (any edge
            # within tolerance). Reject shapes that also span more
            # than ~10 % of the MediaBox dimension — those are rect
            # candidates, not corner marks.
            bw = bx1 - bx0
            bh = by1 - by0
            if bw > mb_w * 0.1 or bh > mb_h * 0.1:
                continue
            close = (
                abs(bx0 - cx) <= _CORNER_TOLERANCE_PT or abs(bx1 - cx) <= _CORNER_TOLERANCE_PT
            ) and (abs(by0 - cy) <= _CORNER_TOLERANCE_PT or abs(by1 - cy) <= _CORNER_TOLERANCE_PT)
            if close:
                hits += 1
                break  # don't double-count a corner

    # Evaluate rectangle coverage.
    best_ratio = 0.0
    for bx0, by0, bx1, by1 in stroked_bboxes:
        area = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
        ratio = area / mb_area if mb_area > 0 else 0.0
        if ratio > best_ratio:
            best_ratio = ratio

    if hits >= _MIN_CORNERS_FOR_MATCH and best_ratio >= _RECT_AREA_RATIO_MIN:
        return hits, best_ratio
    return None


# ── Dieline geometry + multi-color extractor ────────────────────


def _merge_overlapping(
    bboxes: list[tuple[float, float, float, float]],
    *,
    fuzz: float = 0.0,
    min_area: float = 100.0,
) -> list[tuple[float, float, float, float]]:
    """Cluster axis-aligned bboxes that overlap (with a ``fuzz`` pt
    expansion) into their union bounding boxes. Used by the dieline
    extractor to turn per-subpath bboxes into per-region "islands"
    so a multi-artwork file (circle + rectangle on one sheet) ends
    up with one region per artwork rather than one big enveloping
    rectangle.

    ``fuzz`` is deliberately small (5 pt ≈ 1.8 mm) — tightly-spaced
    multi-artwork files (Pavette's circle-over-rectangle layout sits
    ~10 mm apart) need to stay separated. The previous 20 pt default
    merged them into a single 169x186 mm bbox. Individual bezier
    segments of a circle still cluster because they *touch* at
    shared endpoints (0 pt gap).

    ``min_area`` drops noise from stray short subpaths — a single
    curve control-point pickup or a ``m...m`` with no painted
    operators. 100 pt² (~10x10 pt ≈ 3.5x3.5 mm) keeps the cluster
    list honest without silently dropping thin dielines; a
    real cut contour is always far larger.
    """
    if not bboxes:
        return []
    remaining = list(bboxes)
    merged: list[tuple[float, float, float, float]] = []
    while remaining:
        cur = list(remaining.pop())
        changed = True
        while changed:
            changed = False
            still: list[tuple[float, float, float, float]] = []
            for b in remaining:
                overlaps = (
                    cur[0] - fuzz <= b[2]
                    and b[0] - fuzz <= cur[2]
                    and cur[1] - fuzz <= b[3]
                    and b[1] - fuzz <= cur[3]
                )
                if overlaps:
                    cur[0] = min(cur[0], b[0])
                    cur[1] = min(cur[1], b[1])
                    cur[2] = max(cur[2], b[2])
                    cur[3] = max(cur[3], b[3])
                    changed = True
                else:
                    still.append(b)
            remaining = still
        merged.append(tuple(cur))  # type: ignore[arg-type]
    # Drop regions below the min-area floor.
    return [b for b in merged if max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1]) >= min_area]


def _extract_dieline_paths(
    page_signals: dict[str, Any],
    spot_name: str | None,
) -> tuple[list[tuple[float, float, float, float]], int]:
    """Walk page-``page_num`` content stream and return the dieline
    sub-path bboxes plus the count of distinct stroke colors seen
    inside a dieline OCG.

    A path counts as dieline when EITHER:

    * its current stroking color-space resolves to a Separation
      whose colorant name matches ``spot_name``, OR
    * it is painted inside a Marked-Content block whose OCG name
      matches one of the dieline tokens (``dieline``, ``cut``,
      ``crease``, ``perf``, …).

    The second outcome — distinct-color count inside a dieline OCG
    — lets the caller decide whether to emit
    ``LPDF_DIE_MULTI_COLOR``. A clean dieline layer has exactly one
    stroke color; multi-color layers signal misplaced artwork.

    Co-ordinates come from raw operator operands (no CTM
    composition) — axis-aligned layouts work; rotated or
    heavily-transformed art may miss. That's a known scope limit
    called out in the WS-19 geometry fallback.
    """
    cs_to_spot_raw = page_signals.get("cs_to_spot")
    mc_to_ocg_raw = page_signals.get("prop_to_ocg_name")
    instrs = page_signals.get("content_ops")
    if not isinstance(instrs, list):
        return [], 0
    cs_to_spot = (
        {str(k): str(v) for k, v in cs_to_spot_raw.items()}
        if isinstance(cs_to_spot_raw, dict)
        else {}
    )
    mc_to_ocg = (
        {str(k): str(v) for k, v in mc_to_ocg_raw.items()}
        if isinstance(mc_to_ocg_raw, dict)
        else {}
    )

    current_stroke_cs: str | None = None
    current_stroke_color: tuple[float, ...] = ()
    ocg_stack: list[str] = []
    path_points: list[tuple[float, float]] = []
    # ``subpath_bboxes`` holds one bbox per completed subpath within
    # the current compound path. A new ``m`` flushes the in-progress
    # subpath into this list; the stroke finisher consumes every
    # entry so compound paths (``m ... m ... S``) register each
    # artwork separately instead of collapsing onto the last subpath.
    subpath_bboxes: list[tuple[float, float, float, float]] = []
    # CTM composition — Pavette places its circle and rectangle
    # dielines via ``cm`` operators, so raw operand coordinates
    # land at ``(0, 0)`` / ``(0, -144)`` etc. instead of the actual
    # page positions. Without composing the CTM, the circle and
    # rectangle's raw bboxes overlap and merge into one region.
    # Matrix layout: ``[a, b, c, d, e, f]`` where point (x, y)
    # transforms to ``(x*a + y*c + e, x*b + y*d + f)``.
    ctm_stack: list[tuple[float, float, float, float, float, float]] = []
    ctm: tuple[float, float, float, float, float, float] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    def apply_ctm(x: float, y: float) -> tuple[float, float]:
        a, b, c, d, e, f = ctm
        return (x * a + y * c + e, x * b + y * d + f)

    def compose(
        m1: tuple[float, float, float, float, float, float],
        m2: tuple[float, float, float, float, float, float],
    ) -> tuple[float, float, float, float, float, float]:
        """Post-multiply ``m2`` onto ``m1``. PDF ``cm`` semantics:
        the new matrix is applied as ``m2 x m1``."""
        a1, b1, c1, d1, e1, f1 = m1
        a2, b2, c2, d2, e2, f2 = m2
        return (
            a2 * a1 + b2 * c1,
            a2 * b1 + b2 * d1,
            c2 * a1 + d2 * c1,
            c2 * b1 + d2 * d1,
            e2 * a1 + f2 * c1 + e1,
            e2 * b1 + f2 * d1 + f1,
        )

    dieline_bboxes: list[tuple[float, float, float, float]] = []
    dieline_colors: set[tuple[str | None, tuple[float, ...]]] = set()

    def in_dieline_layer() -> bool:
        return any(_name_matches(n) for n in ocg_stack)

    def cur_is_dieline_spot() -> bool:
        if spot_name is None:
            return False
        if current_stroke_cs is None:
            return False
        cs_spot = cs_to_spot.get(current_stroke_cs)
        return cs_spot == spot_name

    def seal_subpath() -> None:
        """Freeze the current subpath's bbox into ``subpath_bboxes``.
        Called when the compound path continues with a new ``m`` /
        ``re`` or when a paint operator finishes the whole path."""
        nonlocal path_points
        if not path_points:
            return
        xs = [p[0] for p in path_points]
        ys = [p[1] for p in path_points]
        subpath_bboxes.append((min(xs), min(ys), max(xs), max(ys)))
        path_points = []

    def flush_stroked() -> None:
        """Paint operator hit — seal the current subpath and commit
        every subpath of this compound path as dieline if the stroke
        conditions apply."""
        nonlocal subpath_bboxes
        seal_subpath()
        if not subpath_bboxes:
            return
        hit_layer = in_dieline_layer()
        hit_spot = cur_is_dieline_spot()
        if hit_layer or hit_spot:
            dieline_bboxes.extend(subpath_bboxes)
            if hit_layer:
                dieline_colors.add((current_stroke_cs, current_stroke_color))
        subpath_bboxes = []

    for inst in instrs:
        if not isinstance(inst, dict):
            continue
        op = str(inst.get("op") or "")
        operands = inst.get("operands")
        if not isinstance(operands, list):
            operands = []

        if op == "q":
            ctm_stack.append(ctm)
        elif op == "Q":
            if ctm_stack:
                ctm = ctm_stack.pop()
        elif op == "cm":
            if len(operands) >= 6:
                try:
                    m2 = (
                        float(operands[0]),
                        float(operands[1]),
                        float(operands[2]),
                        float(operands[3]),
                        float(operands[4]),
                        float(operands[5]),
                    )
                    ctm = compose(ctm, m2)
                except Exception:
                    pass
        elif op == "BDC":
            if len(operands) >= 2:
                prop = operands[1]
                prop_name = str(prop).lstrip("/")
                ocg_stack.append(mc_to_ocg.get(prop_name, ""))
        elif op == "BMC":
            ocg_stack.append("")
        elif op == "EMC":
            if ocg_stack:
                ocg_stack.pop()
        elif op == "CS":
            if operands:
                current_stroke_cs = str(operands[0]).lstrip("/")
        elif op in ("SC", "SCN"):
            floats: list[float] = []
            for v in operands:
                with contextlib.suppress(Exception):
                    # Ignore pattern names etc.
                    floats.append(float(v))
            current_stroke_color = tuple(floats)
        elif op == "m":
            # New subpath — freeze the previous one if any.
            seal_subpath()
            if len(operands) >= 2:
                try:
                    path_points = [apply_ctm(float(operands[0]), float(operands[1]))]
                except Exception:
                    path_points = []
        elif op == "l":
            if len(operands) >= 2:
                with contextlib.suppress(Exception):
                    path_points.append(apply_ctm(float(operands[0]), float(operands[1])))
        elif op in ("c", "v", "y"):
            with contextlib.suppress(Exception):
                path_points.append(apply_ctm(float(operands[-2]), float(operands[-1])))
        elif op == "re":
            # ``re`` is a complete, self-contained rectangular
            # subpath. Treat like ``m ... l ... l ... l ... h``.
            seal_subpath()
            if len(operands) >= 4:
                try:
                    x, y, w, h = (float(v) for v in operands[:4])
                    path_points = [
                        apply_ctm(x, y),
                        apply_ctm(x + w, y),
                        apply_ctm(x + w, y + h),
                        apply_ctm(x, y + h),
                    ]
                    seal_subpath()
                except Exception:
                    path_points = []
        elif op in ("S", "s", "B", "B*", "b", "b*"):
            flush_stroked()
        elif op in ("f", "F", "f*", "n"):
            # Fill / no-op — discard any accumulated subpaths; they
            # weren't stroked by the dieline ink.
            path_points = []
            subpath_bboxes = []

    return dieline_bboxes, len(dieline_colors)


def detect_dieline(
    pdf_bytes: bytes,
    *,
    ai_features: set[str] | frozenset[str] | None = None,
    llm_client: Any | None = None,
) -> DielineResult:
    """Run the dieline detection pipeline.

    When the name-match heuristic fires, returns immediately — no
    Sonnet call. When it misses AND the tenant has the
    ``sonnet_fallback`` grant, Sonnet runs on page 1 and the
    verdict lands as ``source="vision"``. Otherwise ``source="missing"``.

    Phase 3d: ``llm_client`` is the LLMClient service instance from
    ``ctx.services.llm_client``. The orchestrator passes it through;
    the helper falls back to direct Anthropic SDK instantiation when
    ``llm_client`` is ``None`` so existing callers don't break.
    """
    try:
        payload = extract_codex_document_via_codex(pdf_bytes)
    except Exception:
        logger.exception("dieline: codex extraction failed")
        return DielineResult(source="missing")

    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    page_signals = analysis.get("page_1") if isinstance(analysis.get("page_1"), dict) else {}
    spot_names = _collect_spot_names(payload)
    layer_names = _collect_layer_names(payload)

    for name in (*spot_names, *layer_names):
        if _name_matches(name):
            logger.info("dieline: name-match hit on '%s'", name)
            # Walk the page-1 content stream to pick up the actual
            # stroked subpaths painted with this spot / on this OCG,
            # cluster them into region bboxes, and flag multi-color
            # dielines. Anything the walker / clusterer raises falls
            # back to the old "name-match only, empty polylines"
            # behaviour so a single corrupt content stream can't
            # wipe a valid name-match detection.
            try:
                bboxes, distinct_color_count = _extract_dieline_paths(page_signals, spot_name=name)
                region_bboxes = _merge_overlapping(bboxes)
                polylines: list[list[list[float]]] = [
                    [
                        [float(b[0]), float(b[1])],
                        [float(b[2]), float(b[1])],
                        [float(b[2]), float(b[3])],
                        [float(b[0]), float(b[3])],
                        [float(b[0]), float(b[1])],
                    ]
                    for b in region_bboxes
                ]
                regions = [
                    {
                        "x0": float(b[0]),
                        "y0": float(b[1]),
                        "x1": float(b[2]),
                        "y1": float(b[3]),
                        "width_mm": round((b[2] - b[0]) * 25.4 / 72, 3),
                        "height_mm": round((b[3] - b[1]) * 25.4 / 72, 3),
                    }
                    for b in region_bboxes
                ]
                multi = distinct_color_count > 1
            except Exception:
                logger.exception(
                    "dieline: content-stream walker raised on '%s' — "
                    "falling back to name-match only",
                    name,
                )
                polylines = []
                regions = []
                multi = False
            return DielineResult(
                source="name",
                spot_name=name,
                polylines=polylines,
                confidence=1.0,
                regions=regions,
                multi_color=multi,
            )

    # WS-19 geometry fallback — detect the textbook
    # "4 corner trim marks + bounding rectangle" pattern without
    # relying on spot / layer naming conventions. Runs before
    # Sonnet so we avoid the API round-trip when the shape
    # heuristic is confident. Confidence 0.9 beats typical Sonnet
    # output (0.8–0.85) so this path wins on canonical dielines;
    # Sonnet still takes over on stylised / broken-frame layouts
    # because geometry returns None there.
    try:
        geometry = _detect_by_geometry(page_signals)
    except Exception:
        logger.exception("dieline: geometry fallback crashed")
        geometry = None
    if geometry is not None:
        logger.info(
            "dieline: geometry-match hit (corners=%d rect_area_ratio=%.2f)",
            geometry[0],
            geometry[1],
        )
        return DielineResult(
            source="geometry",
            spot_name=None,
            polylines=[],
            confidence=0.9,
        )

    # Sonnet fallback — only when the operator has granted it.
    ai_features = frozenset(ai_features or frozenset())
    if "sonnet_fallback" in ai_features:
        try:
            from lintpdf.ai.dieline_claude import detect_dieline_via_claude

            logger.info("dieline: name + geometry missed, calling Sonnet fallback")
            vision = detect_dieline_via_claude(pdf_bytes, llm_client=llm_client)
            if vision is not None:
                logger.info(
                    "dieline: Sonnet verdict source=%s confidence=%.2f polylines=%d",
                    vision.source,
                    vision.confidence,
                    len(vision.polylines),
                )
                return vision
            logger.info("dieline: Sonnet returned no dieline (empty polylines / parse miss)")
        except Exception:
            logger.exception("dieline: vision fallback failed")
    else:
        logger.info("dieline: name + geometry missed and sonnet_fallback not granted")

    return DielineResult(source="missing")


def result_to_json(result: DielineResult) -> dict[str, Any]:
    """JSON-friendly projection for ``JobResponse.dieline``."""
    return {
        "source": result.source,
        "polylines": result.polylines,
        "spot_name": result.spot_name,
        "confidence": result.confidence,
        "regions": result.regions,
        "multi_color": result.multi_color,
    }
