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

    # Sonnet fallback — only when the operator has granted it.
    ai_features = frozenset(ai_features or frozenset())
    if "sonnet_fallback" in ai_features:
        try:
            from lintpdf.ai.dieline_claude import detect_dieline_via_claude

            vision = detect_dieline_via_claude(pdf_bytes)
            if vision is not None:
                return vision
        except Exception:
            logger.exception("dieline: vision fallback failed")

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
