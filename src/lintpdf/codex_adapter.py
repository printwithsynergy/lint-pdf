"""Optional codexPDF adapter for lint-pdf.

This module intentionally uses subprocess shell-out so lint-pdf can consume
codex output as an external contract while preserving a clean migration path.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lintpdf.codex_summary import ensure_codex_summary
from lintpdf.semantic.model import (
    PdfAnnotation,
    PdfBox,
    PdfColorSpace,
    PdfFont,
    PdfImage,
    SemanticDocument,
    SemanticPage,
)


@dataclass(frozen=True)
class CodexViewerPayload:
    pdf_version: str
    page_count: int
    is_encrypted: bool
    pages: list[dict[str, Any]]
    info_dict: dict[str, Any]


def extract_viewer_payload_via_codex(pdf_bytes: bytes) -> CodexViewerPayload:
    payload = _extract_codex_payload(pdf_bytes)
    pages = []
    for page in payload.get("pages", []):
        boxes = page.get("boxes") or {}
        media = boxes.get("media")
        crop = boxes.get("crop")
        bleed = boxes.get("bleed")
        trim = boxes.get("trim")
        art = boxes.get("art")
        pages.append(
            {
                "page_num": page.get("page_num"),
                "rotate": page.get("rotation", 0),
                "user_unit": 1.0,
                "media_box": _box_to_list(media),
                "crop_box": _box_to_list(crop),
                "bleed_box": _box_to_list(bleed),
                "trim_box": _box_to_list(trim),
                "art_box": _box_to_list(art),
                "width_pts": _dim(media, "x1") - _dim(media, "x0"),
                "height_pts": _dim(media, "y1") - _dim(media, "y0"),
            }
        )

    return CodexViewerPayload(
        pdf_version=str(payload.get("pdf_version") or "unknown"),
        page_count=int(len(pages)),
        is_encrypted=bool(payload.get("is_encrypted", False)),
        pages=pages,
        info_dict=(payload.get("info") or {}) if isinstance(payload.get("info"), dict) else {},
    )


def extract_semantic_document_via_codex(pdf_bytes: bytes) -> tuple[SemanticDocument, list[Any]]:
    """Build lint-pdf SemanticDocument from codex contract JSON."""
    payload = _extract_codex_payload(pdf_bytes)
    pages_payload = payload.get("pages") or []
    color_spaces_payload = payload.get("color_spaces") or []
    fonts_payload = payload.get("fonts") or []
    images_payload = payload.get("images") or []
    annotations_payload = payload.get("annotations") or []

    color_space_by_id = _build_color_space_index(color_spaces_payload)
    fonts_by_page = _group_fonts_by_page(fonts_payload)
    images_by_page = _group_images_by_page(images_payload, color_space_by_id)
    annotations_by_page = _group_annotations_by_page(annotations_payload)

    pages: list[SemanticPage] = []
    analysis_payload = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    page_analysis = (
        analysis_payload.get("page_1")
        if isinstance(analysis_payload.get("page_1"), dict)
        else {}
    )
    for page in pages_payload:
        boxes = page.get("boxes") if isinstance(page, dict) else {}
        media = _box_or_fallback(boxes, "media")
        crop = _box_or_none(boxes, "crop")
        bleed = _box_or_none(boxes, "bleed")
        trim = _box_or_none(boxes, "trim")
        art = _box_or_none(boxes, "art")
        if crop is None:
            crop = media
        if bleed is None:
            bleed = crop
        if trim is None:
            trim = crop
        if art is None:
            art = crop

        page_num = _as_int(page.get("page_num"), 1)
        page_color_spaces = _page_color_spaces(page, color_space_by_id)
        pages.append(
            SemanticPage(
                page_num=page_num,
                media_box=media,
                crop_box=crop,
                bleed_box=bleed,
                trim_box=trim,
                art_box=art,
                rotate=_as_int(page.get("rotation"), 0),
                user_unit=1.0,
                fonts=fonts_by_page.get(page_num, {}),
                images=images_by_page.get(page_num, []),
                color_spaces=page_color_spaces,
                resources={"codex_analysis": page_analysis},
                content_stream=b"",
                annotations=annotations_by_page.get(page_num, []),
                transparency_group=None,
            )
        )

    output_intents = []
    for intent in payload.get("output_intents") or []:
        if not isinstance(intent, dict):
            continue
        output_intents.append(
            {
                "/S": intent.get("subtype"),
                "/OutputConditionIdentifier": intent.get("output_condition_identifier"),
                "/DestOutputProfile": {"/ColorSpace": intent.get("profile_id")}
                if intent.get("profile_id")
                else None,
            }
        )

    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    info_custom = info.get("custom") if isinstance(info, dict) else {}
    info_dict = {
        "Title": info.get("title"),
        "Author": info.get("author"),
        "Subject": info.get("subject"),
        "Creator": info.get("creator"),
        "Producer": info.get("producer"),
        "CreationDate": info.get("creation_date"),
        "ModDate": info.get("mod_date"),
    }
    if isinstance(info_custom, dict):
        for key, value in info_custom.items():
            info_dict[str(key)] = str(value)
    info_dict = {k: v for k, v in info_dict.items() if v is not None}

    xmp = payload.get("xmp") if isinstance(payload.get("xmp"), dict) else {}
    metadata_stream = b"<xmp-present/>" if bool(xmp.get("present")) else None

    document = SemanticDocument(
        version=str(payload.get("pdf_version") or "unknown"),
        page_count=len(pages),
        is_encrypted=bool(payload.get("is_encrypted", False)),
        info_dict=info_dict,
        catalog={"codex_analysis": analysis_payload},
        output_intents=[oi for oi in output_intents if oi.get("/S") or oi.get("/DestOutputProfile")],
        metadata_stream=metadata_stream,
        trailer={},
        pages=pages,
    )
    return document, []


def extract_codex_document_via_codex(pdf_bytes: bytes) -> dict[str, Any]:
    """Return the raw codex document payload as a dict."""
    return _extract_codex_payload(pdf_bytes)


def extract_analysis_signals_via_codex(pdf_bytes: bytes) -> dict[str, Any]:
    """Return codex additive analysis signals used by lint analyzers."""
    payload = _extract_codex_payload(pdf_bytes)
    analysis = payload.get("analysis")
    if isinstance(analysis, dict):
        return analysis
    return {}


def _extract_codex_payload(pdf_bytes: bytes) -> dict[str, Any]:
    """Extract a CodexDocument JSON for ``pdf_bytes``.

    Prefers the in-process :class:`codex_pdf.client.HttpClient` (which
    falls back to direct calls into :mod:`codex_pdf.render` when no
    HTTP base is configured). The legacy subprocess path is retained
    as a fallback when the codex package isn't importable from the
    current process — that situation only arises during transition
    from a pre-1.2.0 lint-pdf install.
    """
    try:
        from codex_pdf.client import HttpClient

        payload = HttpClient(
            route_mode=os.getenv("CODEX_ROUTE_MODE"),
            plant=os.getenv("CODEX_PLANT"),
            affinity_key=os.getenv("CODEX_AFFINITY_KEY"),
        ).extract(pdf_bytes)
        if not isinstance(payload, dict):
            raise RuntimeError("codex extract returned non-object JSON payload")
        return ensure_codex_summary(payload)
    except ImportError:
        pass

    codex_project = os.getenv("CODEX_PDF_PROJECT")
    cmd = ["codex-pdf", "extract"]
    if codex_project:
        cmd = ["uv", "run", "--project", codex_project, "codex-pdf", "extract"]
    else:
        sibling = Path(__file__).resolve().parents[3] / "codex-pdf"
        if sibling.exists():
            cmd = ["uv", "run", "--project", str(sibling), "codex-pdf", "extract"]

    with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
        handle.write(pdf_bytes)
        handle.flush()
        proc = subprocess.run(
            [*cmd, handle.name],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"codex-pdf extract failed: {proc.stderr.strip()}")

    payload = json.loads(proc.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("codex-pdf extract returned non-object JSON payload")
    return ensure_codex_summary(payload)


def _box_to_pdfbox(box: Any) -> PdfBox | None:
    if not isinstance(box, dict):
        return None
    try:
        return PdfBox(
            float(box["x0"]),
            float(box["y0"]),
            float(box["x1"]),
            float(box["y1"]),
        )
    except (TypeError, ValueError, KeyError):
        return None


def _box_or_none(boxes: Any, key: str) -> PdfBox | None:
    if not isinstance(boxes, dict):
        return None
    return _box_to_pdfbox(boxes.get(key))


def _box_or_fallback(boxes: Any, key: str) -> PdfBox:
    box = _box_or_none(boxes, key)
    if box is not None:
        return box
    return PdfBox(0.0, 0.0, 612.0, 792.0)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_color_space_index(color_spaces: list[Any]) -> dict[str, PdfColorSpace]:
    out: dict[str, PdfColorSpace] = {}
    for cs in color_spaces:
        if not isinstance(cs, dict):
            continue
        cs_id = str(cs.get("id") or "").strip()
        if not cs_id:
            continue
        family = str(cs.get("family") or "DeviceRGB")
        canonical = cs.get("canonical") if isinstance(cs.get("canonical"), dict) else {}
        components = _as_int(canonical.get("components"), 0)
        if components <= 0:
            components = {"DeviceGray": 1, "DeviceRGB": 3, "DeviceCMYK": 4}.get(family, 0)
        colorants = cs.get("spot_colorants") if isinstance(cs.get("spot_colorants"), list) else []
        colorant_names: list[str] = []
        for colorant in colorants:
            if isinstance(colorant, dict) and colorant.get("name"):
                colorant_names.append(str(colorant["name"]))

        out[cs_id] = PdfColorSpace(
            name=cs_id,
            cs_type=family,
            components=components,
            icc_profile_ref=cs.get("icc_profile_id"),
            alternate=None,
            base_space=None,
            colorant_names=tuple(colorant_names),
        )
    return out


def _group_fonts_by_page(fonts: list[Any]) -> dict[int, dict[str, PdfFont]]:
    out: dict[int, dict[str, PdfFont]] = {}
    for font in fonts:
        if not isinstance(font, dict):
            continue
        font_id = str(font.get("font_id") or "unknown")
        base_name = str(font.get("base_name") or font_id)
        subtype = str(font.get("subtype") or "unknown")
        embedding = str(font.get("embedded") or "unknown")
        page_refs = font.get("page_refs") if isinstance(font.get("page_refs"), list) else []
        if not page_refs:
            page_refs = [1]
        pdf_font = PdfFont(
            name=font_id,
            base_font=base_name,
            font_type=subtype,
            embedded=embedding in {"full", "subset"},
            subset=embedding == "subset",
            encoding=font.get("encoding"),
            font_descriptor=None,
            has_to_unicode=False,
            cid_system_info=None,
        )
        for page_num in page_refs:
            page_idx = _as_int(page_num, 1)
            page_fonts = out.setdefault(page_idx, {})
            page_fonts[font_id] = pdf_font
    return out


def _group_images_by_page(
    images: list[Any], color_space_by_id: dict[str, PdfColorSpace]
) -> dict[int, list[PdfImage]]:
    out: dict[int, list[PdfImage]] = {}
    for image in images:
        if not isinstance(image, dict):
            continue
        page_num = _as_int(image.get("page_num"), 1)
        color_space_id = image.get("color_space_id")
        color_space = (
            color_space_by_id.get(str(color_space_id))
            if color_space_id is not None
            else None
        )
        compression = image.get("compression")
        filters = tuple([str(compression)]) if compression else ()
        out.setdefault(page_num, []).append(
            PdfImage(
                name=str(image.get("image_id") or "image"),
                width=_as_int(image.get("width_px"), 0),
                height=_as_int(image.get("height_px"), 0),
                bits_per_component=_as_int(image.get("bits_per_component"), 0),
                color_space=color_space,
                filters=filters,
                has_soft_mask=bool(image.get("soft_mask", False)),
                has_hard_mask=False,
                interpolate=False,
                intent=None,
                inline=False,
                page_num=page_num,
            )
        )
    return out


def _group_annotations_by_page(annotations: list[Any]) -> dict[int, list[PdfAnnotation]]:
    out: dict[int, list[PdfAnnotation]] = {}
    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        page_num = _as_int(annotation.get("page_num"), 1)
        out.setdefault(page_num, []).append(
            PdfAnnotation(
                subtype=str(annotation.get("subtype") or ""),
                rect=_box_to_pdfbox(annotation.get("rect")),
                flags=0,
                contents=str(annotation.get("contents") or ""),
                page_num=page_num,
            )
        )
    return out


def _page_color_spaces(
    page: Any, color_space_by_id: dict[str, PdfColorSpace]
) -> dict[str, PdfColorSpace]:
    if not isinstance(page, dict):
        return {}
    resources = page.get("resources")
    if not isinstance(resources, dict):
        return {}
    ids = resources.get("color_space_ids")
    if not isinstance(ids, list):
        return {}
    out: dict[str, PdfColorSpace] = {}
    for cs_id in ids:
        key = str(cs_id)
        cs = color_space_by_id.get(key)
        if cs is not None:
            out[key] = cs
    return out


def _box_to_list(box: Any) -> list[float] | None:
    if not isinstance(box, dict):
        return None
    try:
        return [
            float(box["x0"]),
            float(box["y0"]),
            float(box["x1"]),
            float(box["y1"]),
        ]
    except (KeyError, TypeError, ValueError):
        return None


def _dim(box: Any, key: str) -> float:
    if not isinstance(box, dict):
        return 0.0
    try:
        return float(box.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0
