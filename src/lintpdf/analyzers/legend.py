"""Legend-vs-art swatch classifier (WS-D).

Two strategies, combined:

1. **Position-based.** When the dieline is known, any swatch whose
   bbox lies entirely outside the dieline polygon is ``legend``;
   entirely inside → ``art``. Straddling swatches fall through to
   strategy 2.
2. **Sonnet 4.6 fallback.** For ambiguous swatches we send a
   cropped image to Sonnet and take its verdict. Only fires when
   the tenant has ``sonnet_fallback`` in ``ai_features``.

No dieline → every swatch falls through to Sonnet; no
``sonnet_fallback`` grant → every swatch gets classified as
``unknown`` rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SwatchClassification:
    """One swatch + its legend/art verdict."""

    spot_name: str
    bbox: list[float]  # [x0, y0, x1, y1]
    kind: str  # "legend" | "art" | "unknown"
    source: str  # "position" | "vision" | "position_only"
    confidence: float


def _bbox_inside(inner: list[float], outer: tuple[float, float, float, float]) -> bool:
    ix0, iy0, ix1, iy1 = inner
    ox0, oy0, ox1, oy1 = outer
    return ix0 >= ox0 and iy0 >= oy0 and ix1 <= ox1 and iy1 <= oy1


def _bbox_outside(inner: list[float], outer: tuple[float, float, float, float]) -> bool:
    ix0, iy0, ix1, iy1 = inner
    ox0, oy0, ox1, oy1 = outer
    return ix1 < ox0 or ix0 > ox1 or iy1 < oy0 or iy0 > oy1


def _outer_bbox_of(polylines: list[list[list[float]]]) -> tuple[float, float, float, float] | None:
    if not polylines:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for poly in polylines:
        for pt in poly:
            if len(pt) >= 2:
                xs.append(float(pt[0]))
                ys.append(float(pt[1]))
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def classify_swatches(
    swatches: list[dict[str, Any]],
    dieline: Any,
    *,
    ai_features: set[str] | frozenset[str] | None = None,
    pdf_bytes: bytes | None = None,
) -> list[SwatchClassification]:
    """Classify every input swatch as legend / art / unknown.

    ``swatches`` is the shape the separations analyzer already
    produces: ``[{"spot_name": str, "bbox": [x0,y0,x1,y1]}, ...]``.

    The dieline is used as the outer art footprint; any swatch
    strictly outside it is a legend block. Straddling or
    dieline-missing cases fall through to Sonnet only when the
    tenant has ``sonnet_fallback``.
    """
    ai_features = frozenset(ai_features or frozenset())
    outer = _outer_bbox_of(list(getattr(dieline, "polylines", []) or []))

    out: list[SwatchClassification] = []
    ambiguous: list[tuple[int, dict[str, Any]]] = []

    for i, sw in enumerate(swatches):
        bbox = sw.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        spot = str(sw.get("spot_name", ""))
        if outer is None:
            ambiguous.append((i, sw))
            out.append(
                SwatchClassification(
                    spot_name=spot,
                    bbox=[float(x) for x in bbox],
                    kind="unknown",
                    source="position_only",
                    confidence=0.0,
                )
            )
            continue
        if _bbox_outside(bbox, outer):
            out.append(
                SwatchClassification(
                    spot_name=spot,
                    bbox=[float(x) for x in bbox],
                    kind="legend",
                    source="position",
                    confidence=1.0,
                )
            )
        elif _bbox_inside(bbox, outer):
            out.append(
                SwatchClassification(
                    spot_name=spot,
                    bbox=[float(x) for x in bbox],
                    kind="art",
                    source="position",
                    confidence=1.0,
                )
            )
        else:
            ambiguous.append((i, sw))
            out.append(
                SwatchClassification(
                    spot_name=spot,
                    bbox=[float(x) for x in bbox],
                    kind="unknown",
                    source="position_only",
                    confidence=0.0,
                )
            )

    # Sonnet fallback for ambiguous swatches.
    if ambiguous and pdf_bytes is not None and "sonnet_fallback" in ai_features:
        try:
            from lintpdf.ai.legend_claude import classify_swatches_via_claude

            verdicts = classify_swatches_via_claude(pdf_bytes, [sw for _i, sw in ambiguous])
            for (slot_idx, _sw), verdict in zip(ambiguous, verdicts, strict=False):
                if verdict is None:
                    continue
                out[slot_idx] = verdict
        except Exception:
            pass

    return out


def result_to_json(items: list[SwatchClassification]) -> list[dict[str, Any]]:
    return [
        {
            "spot_name": c.spot_name,
            "bbox": c.bbox,
            "kind": c.kind,
            "source": c.source,
            "confidence": c.confidence,
        }
        for c in items
    ]
