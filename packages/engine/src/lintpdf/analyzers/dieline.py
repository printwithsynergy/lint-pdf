"""Dieline detection (WS-D).

Two strategies, tried in order:

1. **Name-match heuristic (always runs first).** Scans the PDF for
   Separation / Spot colour names, layer (OCG) names, and page-label
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

import logging
import re
from dataclasses import dataclass, field
from typing import Any

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
    """

    source: str
    polylines: list[list[list[float]]] = field(default_factory=list)
    spot_name: str | None = None
    confidence: float = 0.0


def _collect_spot_names(pdf: Any) -> list[str]:
    """Collect every Separation / DeviceN spot name in the PDF.

    Walks the **entire** indirect-object graph, not just direct page
    ``/Resources/ColorSpace`` entries. Press-ready packaging PDFs
    routinely declare spot colours inside Form XObjects, patterns,
    or nested resource dictionaries, and the old direct-page walk
    missed all of them — so a PDF containing a ``Dieline`` spot
    colour would still report ``source='missing'``.
    """
    try:
        import pikepdf
    except ImportError:
        return []

    names: list[str] = []
    seen_ids: set[int] = set()

    def _is_array(obj: Any) -> bool:
        # Treat Python lists and pikepdf.Array as arrays. Strings,
        # Names, and Dictionaries must NOT land here (pikepdf.Array
        # exposes both ``__iter__`` and ``items``, which made the
        # earlier hasattr check ambiguous).
        return isinstance(obj, list) or isinstance(obj, pikepdf.Array)

    def _is_dictlike(obj: Any) -> bool:
        return isinstance(obj, (pikepdf.Dictionary, pikepdf.Stream)) or (
            hasattr(obj, "items") and not _is_array(obj)
        )

    def _collect(obj: Any, depth: int) -> None:
        if depth > 10:
            return
        try:
            obj_id = id(obj)
        except Exception:
            obj_id = 0
        if obj_id in seen_ids:
            return
        seen_ids.add(obj_id)

        # Separation / DeviceN arrays:
        #   [/Separation  <name>  <alternate>  <tintTransform>]
        #   [/DeviceN    [<name> <name> ...]  <alternate>  <tintTransform>]
        if _is_array(obj):
            try:
                arr = [obj[i] for i in range(len(obj))]
            except Exception:
                arr = list(obj)
            if len(arr) >= 2:
                subtype = str(arr[0])
                if subtype in ("/Separation", "Separation"):
                    try:
                        names.append(str(arr[1]).lstrip("/"))
                    except Exception:
                        pass
                elif subtype in ("/DeviceN", "DeviceN"):
                    comp = arr[1]
                    if _is_array(comp):
                        for n in comp:
                            try:
                                names.append(str(n).lstrip("/"))
                            except Exception:
                                continue
            for item in arr:
                _collect(item, depth + 1)
            return

        if _is_dictlike(obj):
            try:
                for _k, v in obj.items():
                    _collect(v, depth + 1)
            except Exception:
                pass
            return

    def _walk_resources(res: Any, depth: int) -> None:
        """Walk a /Resources dict: its /ColorSpace, then recurse into
        /XObject /Form and /Pattern entries (which each have their
        own /Resources where a spot colour can live)."""
        if res is None or not _is_dictlike(res):
            return
        try:
            cs = res.get("/ColorSpace")
        except Exception:
            cs = None
        if cs is not None:
            _collect(cs, depth)

        for child_key in ("/XObject", "/Pattern"):
            try:
                child = res.get(child_key)
            except Exception:
                continue
            if child is None or not _is_dictlike(child):
                continue
            try:
                for _k, ref in child.items():
                    if not _is_dictlike(ref):
                        continue
                    try:
                        inner = ref.get("/Resources")
                    except Exception:
                        inner = None
                    if inner is not None and depth < 10:
                        _walk_resources(inner, depth + 1)
            except Exception:
                continue

    try:
        # Every page's /Resources, recursively through Form XObjects
        # and Patterns. This is the path that matters in real PDFs —
        # a spot colour defined once inside a shared Form XObject is
        # reachable from the page via /Resources/XObject/<name>.
        for page in pdf.pages:
            try:
                _walk_resources(page.get("/Resources"), 0)
            except Exception:
                continue

        # Belt + braces: iterate every indirect object in the xref so
        # we also catch spot colours that live in orphaned or
        # unusual object graphs (patterns referenced from resource
        # dictionaries we haven't traversed yet, etc.).
        try:
            for obj in pdf.objects:
                _collect(obj, 0)
        except Exception:
            logger.debug("dieline: pdf.objects iteration unavailable")
    except Exception:
        logger.exception("dieline: spot-name walk failed")

    # Dedupe case-insensitively, preserve first-seen casing for display.
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        key = n.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(n)
    if out:
        logger.info("dieline: collected %d spot name(s): %s", len(out), out)
    return out


def _collect_layer_names(pdf: Any) -> list[str]:
    """Collect OCG (optional content group) names from the catalog."""
    out: list[str] = []
    try:
        root = pdf.Root
        ocprops = root.get("/OCProperties")
        if ocprops is None:
            return out
        ocgs = ocprops.get("/OCGs") or []
        for ocg in ocgs:
            try:
                name = ocg.get("/Name")
                if name is not None:
                    out.append(str(name))
            except Exception:
                continue
    except Exception:
        logger.exception("dieline: OCG walk failed")
    return out


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


def _detect_by_geometry(pdf: Any) -> tuple[int, float] | None:
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
    try:
        import pikepdf
    except ImportError:
        return None

    try:
        page = pdf.pages[0]
    except (IndexError, Exception):
        return None

    try:
        mb = page.mediabox
        mb_x0, mb_y0, mb_x1, mb_y1 = (
            float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3])
        )
    except Exception:
        return None
    mb_w = mb_x1 - mb_x0
    mb_h = mb_y1 - mb_y0
    if mb_w <= 0 or mb_h <= 0:
        return None
    mb_area = mb_w * mb_h

    try:
        instructions = pikepdf.parse_content_stream(page)
    except Exception:
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
        op = str(getattr(inst, "operator", inst[1] if isinstance(inst, tuple) else ""))
        operands = getattr(inst, "operands", inst[0] if isinstance(inst, tuple) else [])

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
                try:
                    path_points.append((float(operands[0]), float(operands[1])))
                except Exception:
                    pass
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
                abs(bx0 - cx) <= _CORNER_TOLERANCE_PT
                or abs(bx1 - cx) <= _CORNER_TOLERANCE_PT
            ) and (
                abs(by0 - cy) <= _CORNER_TOLERANCE_PT
                or abs(by1 - cy) <= _CORNER_TOLERANCE_PT
            )
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


def detect_dieline(pdf_bytes: bytes, *, ai_features: set[str] | frozenset[str] | None = None) -> DielineResult:
    """Run the dieline detection pipeline.

    When the name-match heuristic fires, returns immediately — no
    Sonnet call. When it misses AND the tenant has the
    ``sonnet_fallback`` grant, Sonnet runs on page 1 and the
    verdict lands as ``source="vision"``. Otherwise ``source="missing"``.
    """
    try:
        import pikepdf
    except ImportError:
        logger.warning("dieline: pikepdf unavailable; skipping detection")
        return DielineResult(source="missing")

    try:
        pdf = pikepdf.open(_as_bytes_stream(pdf_bytes))
    except Exception:
        logger.exception("dieline: pikepdf.open failed")
        return DielineResult(source="missing")

    spot_names = _collect_spot_names(pdf)
    layer_names = _collect_layer_names(pdf)

    for name in (*spot_names, *layer_names):
        if _name_matches(name):
            logger.info("dieline: name-match hit on '%s'", name)
            return DielineResult(
                source="name",
                spot_name=name,
                # Polylines from the name-match path are computed
                # downstream (art_size needs them). For the base
                # detection result we just flag the hit.
                polylines=[],
                confidence=1.0,
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
        geometry = _detect_by_geometry(pdf)
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
            vision = detect_dieline_via_claude(pdf_bytes)
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
        logger.info(
            "dieline: name + geometry missed and sonnet_fallback not granted"
        )

    return DielineResult(source="missing")


def _as_bytes_stream(data: bytes) -> Any:
    import io

    return io.BytesIO(data)


def result_to_json(result: DielineResult) -> dict[str, Any]:
    """JSON-friendly projection for ``JobResponse.dieline``."""
    return {
        "source": result.source,
        "polylines": result.polylines,
        "spot_name": result.spot_name,
        "confidence": result.confidence,
    }
