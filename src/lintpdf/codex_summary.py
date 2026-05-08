"""Normalize/enrich Codex summary payloads for lint consumers."""

from __future__ import annotations

import re
from typing import Any

_DIELINE_PATTERN = re.compile(
    r"(dieline|die ?line|cut ?line|cutcontour|kiss ?cut|crease|fold|trim|perf|knife|cutter|score)",
    re.IGNORECASE,
)


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        number = float(value)
        if number == number and number not in (float("inf"), float("-inf")):
            return number
    return None


def _fallback_hex(name: str) -> str:
    acc = 2166136261
    for byte in name.encode("utf-8", "ignore"):
        acc ^= byte
        acc = (acc * 16777619) & 0xFFFFFFFF
    r = 55 + (acc & 0x7F)
    g = 55 + ((acc >> 8) & 0x7F)
    b = 55 + ((acc >> 16) & 0x7F)
    return f"#{r:02x}{g:02x}{b:02x}"


def _normalize_color_component(value: float) -> float:
    if value <= 1.0:
        return max(0.0, min(1.0, value))
    return max(0.0, min(1.0, value / 100.0))


def _to_u8(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 255))


def _rgb_hex(values: list[Any]) -> str | None:
    if len(values) < 3:
        return None
    r = _as_float(values[0])
    g = _as_float(values[1])
    b = _as_float(values[2])
    if r is None or g is None or b is None:
        return None
    rgb = [_to_u8(_normalize_color_component(v)) for v in (r, g, b)]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _cmyk_hex(values: list[Any]) -> str | None:
    if len(values) < 4:
        return None
    c = _as_float(values[0])
    m = _as_float(values[1])
    y = _as_float(values[2])
    k = _as_float(values[3])
    if c is None or m is None or y is None or k is None:
        return None
    cn, mn, yn, kn = (
        _normalize_color_component(c),
        _normalize_color_component(m),
        _normalize_color_component(y),
        _normalize_color_component(k),
    )
    rgb = (
        _to_u8((1 - cn) * (1 - kn)),
        _to_u8((1 - mn) * (1 - kn)),
        _to_u8((1 - yn) * (1 - kn)),
    )
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _base_summary(payload: dict[str, Any]) -> dict[str, Any]:
    pages = payload.get("pages") if isinstance(payload.get("pages"), list) else []
    images = payload.get("images") if isinstance(payload.get("images"), list) else []
    fonts = payload.get("fonts") if isinstance(payload.get("fonts"), list) else []
    color_spaces = (
        payload.get("color_spaces") if isinstance(payload.get("color_spaces"), list) else []
    )
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}

    embedded_fonts = 0
    referenced_fonts = 0
    fonts_with_missing_glyphs = 0
    for font in fonts:
        if not isinstance(font, dict):
            continue
        embedded = font.get("embedded")
        if embedded in {"full", "subset"}:
            embedded_fonts += 1
        elif embedded == "referenced":
            referenced_fonts += 1
        if font.get("missing_glyphs_detected") is True:
            fonts_with_missing_glyphs += 1

    first_page = None
    total_area_sq_in = 0.0
    for idx, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        boxes = page.get("boxes") if isinstance(page.get("boxes"), dict) else {}
        media = boxes.get("media") if isinstance(boxes.get("media"), dict) else None
        if media is None:
            continue
        x0 = _as_float(media.get("x0"))
        y0 = _as_float(media.get("y0"))
        x1 = _as_float(media.get("x1"))
        y1 = _as_float(media.get("y1"))
        if x0 is None or y0 is None or x1 is None or y1 is None:
            continue
        width_in = max(0.0, (x1 - x0) / 72.0)
        height_in = max(0.0, (y1 - y0) / 72.0)
        total_area_sq_in += width_in * height_in
        if idx == 0 and first_page is None:
            first_page = {
                "width_in": round(width_in, 4),
                "height_in": round(height_in, 4),
                "width_mm": round(width_in * 25.4, 3),
                "height_mm": round(height_in * 25.4, 3),
            }

    dpi_values: list[float] = []
    below_300 = 0
    largest: tuple[int, int, int] | None = None
    for image in images:
        if not isinstance(image, dict):
            continue
        width_px = int(_as_float(image.get("width_px")) or 0)
        height_px = int(_as_float(image.get("height_px")) or 0)
        if width_px > 0 and height_px > 0:
            area = width_px * height_px
            if largest is None or area > largest[2]:
                largest = (width_px, height_px, area)

        resolution = (
            image.get("effective_resolution_dpi")
            if isinstance(image.get("effective_resolution_dpi"), dict)
            else None
        )
        if resolution is None:
            continue
        x_dpi = _as_float(resolution.get("x_dpi"))
        y_dpi = _as_float(resolution.get("y_dpi"))
        if x_dpi is None or y_dpi is None:
            continue
        avg_dpi = (x_dpi + y_dpi) / 2.0
        dpi_values.append(avg_dpi)
        if avg_dpi < 300:
            below_300 += 1

    spot_by_name: dict[str, dict[str, Any]] = {}
    color_space_by_id: dict[str, dict[str, Any]] = {}
    for cs in color_spaces:
        if not isinstance(cs, dict):
            continue
        cs_id = str(cs.get("id") or "").strip()
        if cs_id:
            color_space_by_id[cs_id] = cs
    for cs in color_spaces:
        if not isinstance(cs, dict):
            continue
        spots = cs.get("spot_colorants") if isinstance(cs.get("spot_colorants"), list) else []
        for spot in spots:
            if not isinstance(spot, dict):
                continue
            name = str(spot.get("name") or "").strip()
            if not name or name in spot_by_name:
                continue
            swatch_hex = _fallback_hex(name)
            swatch_source = "fallback"
            swatch_note = "Fallback hash"
            rgb = spot.get("rgb") if isinstance(spot.get("rgb"), list) else []
            cmyk = spot.get("cmyk") if isinstance(spot.get("cmyk"), list) else []
            lab = spot.get("lab") if isinstance(spot.get("lab"), list) else []
            alt_id = (
                str(spot.get("alternate_space_id") or cs.get("alternate_space_id") or "").strip()
            )
            alt_cs = color_space_by_id.get(alt_id) if alt_id else None
            rgb_hex = _rgb_hex(rgb)
            cmyk_hex = _cmyk_hex(cmyk)
            if (cs.get("family") == "ICCBased" or (alt_cs and alt_cs.get("family") == "ICCBased")) and (
                rgb_hex or cmyk_hex
            ):
                swatch_hex = rgb_hex or cmyk_hex or swatch_hex
                swatch_source = "icc_alternate"
                swatch_note = f"ICCBased alternate via {alt_id or 'unknown'}"
            elif rgb_hex:
                swatch_hex = rgb_hex
                swatch_source = "rgb"
                swatch_note = "RGB from extractor"
            elif cmyk_hex:
                swatch_hex = cmyk_hex
                swatch_source = "cmyk"
                swatch_note = "Projected from CMYK"
            elif len(lab) >= 3 and all(_as_float(v) is not None for v in lab[:3]):
                swatch_source = "lab"
                swatch_note = "LAB from extractor"
            spot_by_name[name] = {
                "name": name,
                "swatch_hex": swatch_hex,
                "swatch_source": swatch_source,
                "swatch_note": swatch_note,
                "rgb": rgb[:3] if rgb else None,
                "cmyk": cmyk[:4] if cmyk else None,
                "lab": lab[:3] if lab else None,
                "pantone_name": spot.get("pantone_name"),
            }

    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    analysis_names: set[str] = set()
    top_spots = analysis.get("spot_names")
    if isinstance(top_spots, list):
        for raw in top_spots:
            if isinstance(raw, str) and raw.strip():
                analysis_names.add(raw.strip())
    for key, page_signal in analysis.items():
        if not key.startswith("page_") or not isinstance(page_signal, dict):
            continue
        cs_to_spot = page_signal.get("cs_to_spot")
        if isinstance(cs_to_spot, dict):
            for raw in cs_to_spot.values():
                if isinstance(raw, str) and raw.strip():
                    analysis_names.add(raw.strip())
    for name in sorted(analysis_names, key=lambda value: value.lower()):
        if name in spot_by_name:
            continue
        spot_by_name[name] = {
            "name": name,
            "swatch_hex": _fallback_hex(name),
            "swatch_source": "hash",
            "swatch_note": "Analysis-only deterministic fallback",
            "rgb": None,
            "cmyk": None,
            "lab": None,
            "pantone_name": None,
        }

    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None]] = set()

    def add_candidate(
        name: str, source_name: str, ocg_id: str | None = None, processing_step: str | None = None
    ) -> None:
        clean = name.strip()
        if not clean:
            return
        key = (clean.lower(), source_name, ocg_id)
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            {
                "name": clean,
                "source": source_name,
                "ocg_id": ocg_id,
                "processing_step": processing_step,
            }
        )

    ocgs = payload.get("ocgs") if isinstance(payload.get("ocgs"), list) else []
    for ocg in ocgs:
        if not isinstance(ocg, dict):
            continue
        name = str(ocg.get("name") or "")
        if _DIELINE_PATTERN.search(name):
            add_candidate(name, "ocg_name", str(ocg.get("ocg_id") or "") or None, None)
        step = str(ocg.get("iso19593_processing_step") or "")
        if _DIELINE_PATTERN.search(step):
            add_candidate(step, "ocg_processing_step", str(ocg.get("ocg_id") or "") or None, step)

    trap = payload.get("trap_evidence") if isinstance(payload.get("trap_evidence"), dict) else {}
    trap_layers = trap.get("trap_layers") if isinstance(trap.get("trap_layers"), list) else []
    for layer in trap_layers:
        if not isinstance(layer, dict):
            continue
        layer_name = str(layer.get("name") or layer.get("processing_step") or "")
        if layer_name and _DIELINE_PATTERN.search(layer_name):
            add_candidate(
                layer_name,
                "trap_layer",
                str(layer.get("ocg_id") or "") or None,
                str(layer.get("processing_step") or "") or None,
            )

    size_bytes = int(_as_float(source.get("size_bytes")) or 0) if source else None
    if size_bytes == 0:
        size_bytes = None

    return {
        "version": "1.0",
        "counts": {
            "pages": len(pages),
            "images": len(images),
            "fonts": len(fonts),
            "embedded_fonts": embedded_fonts,
            "referenced_fonts": referenced_fonts,
            "fonts_with_missing_glyphs": fonts_with_missing_glyphs,
        },
        "images": {
            "dpi_avg": round(sum(dpi_values) / len(dpi_values), 3) if dpi_values else None,
            "dpi_min": round(min(dpi_values), 3) if dpi_values else None,
            "below_300_dpi": below_300,
            "largest_width_px": largest[0] if largest else None,
            "largest_height_px": largest[1] if largest else None,
            "largest_area_px2": largest[2] if largest else None,
        },
        "pages": {
            "first_page": first_page,
            "total_area_sq_in": round(total_area_sq_in, 4),
            "total_area_sq_ft": round(total_area_sq_in / 144.0, 4),
            "total_area_sq_mm": round(total_area_sq_in * 645.16, 3),
        },
        "source": {
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 6) if size_bytes is not None else None,
        },
        "spot_colors": {
            "count": len(spot_by_name),
            "colors": sorted(spot_by_name.values(), key=lambda item: str(item.get("name", "")).lower()),
        },
        "dieline": {
            "count": len(candidates),
            "candidates": candidates,
            "trapped_flag": trap.get("trapped_flag"),
        },
    }


def _lint_dieline_signals(payload: dict[str, Any]) -> dict[str, Any]:
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    names: list[str] = []
    for key in ("spot_names", "layer_names"):
        values = analysis.get(key)
        if isinstance(values, list):
            for raw in values:
                if raw is None:
                    continue
                name = str(raw).strip().lstrip("/")
                if name:
                    names.append(name)
    page_1 = analysis.get("page_1") if isinstance(analysis.get("page_1"), dict) else {}
    prop_to_ocg = (
        page_1.get("prop_to_ocg_name")
        if isinstance(page_1.get("prop_to_ocg_name"), dict)
        else {}
    )
    for raw in prop_to_ocg.values():
        name = str(raw).strip()
        if name:
            names.append(name)

    matches: list[str] = []
    seen: set[str] = set()
    for name in names:
        if not _DIELINE_PATTERN.search(name):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        matches.append(name)

    return {
        "version": "1.0",
        "dieline_signals": {
            "name_token_matches": matches,
            "match_count": len(matches),
            "derived_from": ["analysis.spot_names", "analysis.layer_names", "analysis.page_1.prop_to_ocg_name"],
        },
    }


def ensure_codex_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure codex payload has a stable summary + lint enrichment."""
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        summary = _base_summary(payload)

    # Enrich with lint-specific deterministic signals (additive only).
    summary["lint"] = _lint_dieline_signals(payload)
    payload["summary"] = summary
    return payload
