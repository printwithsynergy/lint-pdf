"""SemanticModel builder — enriches parsed PDF with resolved properties.

The builder takes raw PdfDocument/PdfPage from the parser layer and produces
enriched SemanticDocument/SemanticPage with:
- Resource inheritance resolved (ISO 32000-2 section 7.7.3.4)
- Fonts extracted and normalized
- Color spaces extracted
- Box hierarchy validated
- Rotation and UserUnit resolved

Reference: grounded-research/implementation-plan.md Module 2
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

from grounded.exceptions import InvalidBoxError, InvalidPageError
from grounded.semantic.model import (
    PdfAnnotation,
    PdfBox,
    PdfColorSpace,
    PdfFont,
    SemanticDocument,
    SemanticPage,
)

if TYPE_CHECKING:
    from grounded.parser.adapter import ParserAdapter, PdfDocument, PdfPage

logger = logging.getLogger(__name__)

# Properties that inherit through the page tree (ISO 32000-2 section 7.7.3.4)
_INHERITABLE_PROPERTIES = frozenset({"/Resources", "/MediaBox", "/CropBox", "/Rotate"})


class SemanticModelBuilder:
    """Builds enriched SemanticDocument from parsed PdfDocument.

    Usage:
        adapter = PikePDFAdapter()
        doc = adapter.open(pdf_bytes)
        builder = SemanticModelBuilder(adapter)
        semantic_doc = builder.build(doc)
    """

    def __init__(self, adapter: ParserAdapter) -> None:
        self._adapter = adapter

    def build(self, document: PdfDocument) -> SemanticDocument:
        """Enrich parsed PDF document with semantic information.

        Args:
            document: Raw PdfDocument from the parser.

        Returns:
            SemanticDocument with all properties resolved.
        """
        pages: list[SemanticPage] = []
        for raw_page in document.pages:
            page = self._build_page(document, raw_page)
            pages.append(page)

        return SemanticDocument(
            version=document.version,
            page_count=document.page_count,
            is_encrypted=document.is_encrypted,
            info_dict=document.info_dict,
            catalog=document.catalog,
            output_intents=document.output_intents,
            metadata_stream=document.metadata_stream,
            trailer=document.trailer,
            pages=pages,
        )

    def _build_page(self, document: PdfDocument, raw_page: PdfPage) -> SemanticPage:
        """Build an enriched page from a raw parser page.

        Resolves inheritance, extracts fonts/colors, validates boxes.
        """
        # Resolve inherited properties
        resolved = self._resolve_inheritance(document, raw_page)

        # Build boxes
        media_box = self._resolve_media_box(resolved, raw_page)
        crop_box = self._build_box(resolved.get("crop_box"))
        bleed_box = self._build_box(resolved.get("bleed_box"))
        trim_box = self._build_box(resolved.get("trim_box"))
        art_box = self._build_box(resolved.get("art_box"))

        # Apply box defaults per spec
        if crop_box is None:
            crop_box = media_box
        if bleed_box is None:
            bleed_box = crop_box
        if trim_box is None:
            trim_box = crop_box
        if art_box is None:
            art_box = crop_box

        # Resolve rotation and user_unit
        rotate = resolved.get("rotate", 0)
        if rotate not in (0, 90, 180, 270):
            logger.warning(
                "Invalid rotation %d on page %d, defaulting to 0", rotate, raw_page.page_num
            )
            rotate = 0
        user_unit = resolved.get("user_unit", 1.0)

        # Extract resources
        resources = self._adapter.get_resources(raw_page)

        # Extract fonts from resources
        fonts = self._extract_fonts(resources)

        # Extract color spaces from resources
        color_spaces = self._extract_color_spaces(resources)

        # Get content stream
        try:
            content_stream = self._adapter.get_content_stream(raw_page)
        except Exception:
            logger.warning("Could not extract content stream for page %d", raw_page.page_num)
            content_stream = b""

        # Extract annotations from page dict (not resources)
        annotations = self._extract_annotations(raw_page.page_dict, raw_page.page_num)

        # Extract transparency group
        transparency_group = self._extract_transparency_group(raw_page)

        return SemanticPage(
            page_num=raw_page.page_num,
            media_box=media_box,
            crop_box=crop_box,
            bleed_box=bleed_box,
            trim_box=trim_box,
            art_box=art_box,
            rotate=rotate,
            user_unit=user_unit,
            fonts=fonts,
            color_spaces=color_spaces,
            resources=resources,
            content_stream=content_stream,
            annotations=annotations,
            transparency_group=transparency_group,
        )

    def _resolve_inheritance(
        self, document: PdfDocument, raw_page: PdfPage
    ) -> dict[str, Any]:  # skipcq: PY-R1000
        """Resolve inherited properties by walking the page tree.

        Inheritable properties (ISO 32000-2 section 7.7.3.4):
        - /Resources, /MediaBox, /CropBox, /Rotate

        Walk from page up through /Parent chain. The first value found
        for each property wins (nearest ancestor takes precedence).

        Returns dict with resolved values for: media_box, crop_box,
        bleed_box, trim_box, art_box, rotate, user_unit, resources.
        """
        result: dict[str, Any] = {}

        # Start with page's own values
        result["media_box"] = raw_page.media_box
        result["crop_box"] = raw_page.crop_box
        result["bleed_box"] = raw_page.bleed_box
        result["trim_box"] = raw_page.trim_box
        result["art_box"] = raw_page.art_box
        result["rotate"] = raw_page.rotate
        result["user_unit"] = raw_page.user_unit

        # Walk parent chain for inheritable properties
        if result["media_box"] is None or result["rotate"] == 0:
            try:
                ancestors = self._adapter.get_page_parent_chain(raw_page)
            except Exception:
                ancestors = []

            for ancestor in ancestors:
                # MediaBox
                if result["media_box"] is None:
                    ancestor_media = self._extract_box_from_dict(ancestor, "/MediaBox")
                    if ancestor_media is not None:
                        result["media_box"] = ancestor_media

                # CropBox
                if result["crop_box"] is None:
                    ancestor_crop = self._extract_box_from_dict(ancestor, "/CropBox")
                    if ancestor_crop is not None:
                        result["crop_box"] = ancestor_crop

                # Rotate
                if result["rotate"] == 0:
                    ancestor_rotate = ancestor.get("/Rotate")
                    if ancestor_rotate is not None:
                        with contextlib.suppress(TypeError, ValueError):
                            result["rotate"] = int(ancestor_rotate)

        return result

    @staticmethod
    def _extract_box_from_dict(
        d: dict[str, Any], key: str
    ) -> tuple[float, float, float, float] | None:
        """Extract a box tuple from a dictionary."""
        box = d.get(key)
        if box is None:
            return None
        if isinstance(box, (list, tuple)) and len(box) == 4:
            try:
                return (float(box[0]), float(box[1]), float(box[2]), float(box[3]))
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _resolve_media_box(resolved: dict[str, Any], raw_page: PdfPage) -> PdfBox:
        """Resolve and validate MediaBox (required).

        Raises:
            InvalidPageError: If MediaBox cannot be found.
            InvalidBoxError: If MediaBox has invalid coordinates.
        """
        media_box_tuple = resolved.get("media_box")
        if media_box_tuple is None:
            raise InvalidPageError(
                f"Page {raw_page.page_num}: MediaBox is missing and not inherited"
            )
        return PdfBox.from_tuple(media_box_tuple)

    @staticmethod
    def _build_box(box_tuple: tuple[float, float, float, float] | None) -> PdfBox | None:
        """Build a PdfBox from a tuple, returning None for missing boxes."""
        if box_tuple is None:
            return None
        try:
            return PdfBox.from_tuple(box_tuple)
        except InvalidBoxError:
            logger.warning("Invalid box coordinates: %s", box_tuple)
            return None

    @staticmethod
    def _extract_annotations(
        page_dict: dict[str, Any], page_num: int
    ) -> list[PdfAnnotation]:  # skipcq: PY-R1000
        """Extract annotations from page /Annots array."""
        annots_raw = page_dict.get("/Annots", [])
        if not isinstance(annots_raw, list):
            return []

        annotations: list[PdfAnnotation] = []
        for annot in annots_raw:
            if not isinstance(annot, dict):
                continue
            subtype = str(annot.get("/Subtype", "")).lstrip("/")
            if not subtype:
                continue

            # Parse annotation rectangle
            rect: PdfBox | None = None
            rect_val = annot.get("/Rect")
            if isinstance(rect_val, (list, tuple)) and len(rect_val) == 4:
                with contextlib.suppress(Exception):
                    x0, y0, x1, y1 = (float(v) for v in rect_val)
                    # Normalize: ensure x0 < x1 and y0 < y1
                    if x0 > x1:
                        x0, x1 = x1, x0
                    if y0 > y1:
                        y0, y1 = y1, y0
                    if x0 < x1 and y0 < y1:
                        rect = PdfBox(x0=x0, y0=y0, x1=x1, y1=y1)

            # Parse flags
            flags = 0
            flags_val = annot.get("/F")
            if flags_val is not None:
                with contextlib.suppress(TypeError, ValueError):
                    flags = int(flags_val)

            # Parse contents
            contents = ""
            contents_val = annot.get("/Contents")
            if contents_val is not None:
                contents = str(contents_val)

            annotations.append(
                PdfAnnotation(
                    subtype=subtype,
                    rect=rect,
                    flags=flags,
                    contents=contents,
                    page_num=page_num,
                )
            )

        return annotations

    @staticmethod
    def _extract_transparency_group(raw_page: PdfPage) -> dict[str, Any] | None:
        """Extract transparency group dict from page /Group entry."""
        group = raw_page.page_dict.get("/Group")
        if not isinstance(group, dict):
            return None

        # Only return if it's a Transparency group
        group_subtype = str(group.get("/S", "")).lstrip("/")
        if group_subtype == "Transparency":
            return dict(group)

        return None

    def _extract_fonts(self, resources: dict[str, Any]) -> dict[str, PdfFont]:
        """Extract font information from page resources.

        Reads /Font dictionary from resources and builds PdfFont objects.
        """
        fonts: dict[str, PdfFont] = {}
        font_dict = resources.get("/Font", {})
        if not isinstance(font_dict, dict):
            return fonts

        for font_name, font_info in font_dict.items():
            if not isinstance(font_info, dict):
                continue
            try:
                font = self._build_font(font_name, font_info)
                fonts[font_name] = font
            except Exception:
                logger.debug("Could not extract font %s", font_name)

        return fonts

    @staticmethod
    def _build_font(name: str, font_dict: dict[str, Any]) -> PdfFont:  # skipcq: PY-R1000
        """Build a PdfFont from a font dictionary."""
        base_font = str(font_dict.get("/BaseFont", "Unknown"))
        # Strip leading /
        if base_font.startswith("/"):
            base_font = base_font[1:]

        font_type = str(font_dict.get("/Subtype", "Unknown"))
        if font_type.startswith("/"):
            font_type = font_type[1:]

        encoding = font_dict.get("/Encoding")
        if isinstance(encoding, str) and encoding.startswith("/"):
            encoding = encoding[1:]
        elif isinstance(encoding, dict):
            encoding = encoding.get("/BaseEncoding", "Custom")
            if isinstance(encoding, str) and encoding.startswith("/"):
                encoding = encoding[1:]

        # Font descriptor
        font_descriptor = font_dict.get("/FontDescriptor")
        if not isinstance(font_descriptor, dict):
            font_descriptor = None

        # Embedding detection
        embedded = False
        if font_descriptor:
            for key in ("/FontFile", "/FontFile2", "/FontFile3"):
                if font_descriptor.get(key) is not None:
                    embedded = True
                    break

        # Subset detection: 6 uppercase letters + "+"
        subset = False
        if len(base_font) > 7 and base_font[6] == "+":
            prefix = base_font[:6]
            if prefix.isalpha() and prefix.isupper():
                subset = True

        # ToUnicode
        has_to_unicode = font_dict.get("/ToUnicode") is not None

        # CIDSystemInfo (for CID fonts)
        cid_system_info = None
        descendant_fonts = font_dict.get("/DescendantFonts")
        if isinstance(descendant_fonts, list) and len(descendant_fonts) > 0:
            descendant = descendant_fonts[0]
            if isinstance(descendant, dict):
                cid_system_info = descendant.get("/CIDSystemInfo")
                if not isinstance(cid_system_info, dict):
                    cid_system_info = None
                # Also get the actual CID font type
                cid_subtype = descendant.get("/Subtype")
                if isinstance(cid_subtype, str) and cid_subtype.startswith("/"):
                    font_type = cid_subtype[1:]

        return PdfFont(
            name=name,
            base_font=base_font,
            font_type=font_type,
            embedded=embedded,
            subset=subset,
            encoding=encoding if isinstance(encoding, str) else None,
            font_descriptor=font_descriptor,
            has_to_unicode=has_to_unicode,
            cid_system_info=cid_system_info,
        )

    def _extract_color_spaces(self, resources: dict[str, Any]) -> dict[str, PdfColorSpace]:
        """Extract color space definitions from page resources."""
        color_spaces: dict[str, PdfColorSpace] = {}
        cs_dict = resources.get("/ColorSpace", {})
        if not isinstance(cs_dict, dict):
            return color_spaces

        for cs_name, cs_info in cs_dict.items():
            try:
                cs = self._build_color_space(cs_name, cs_info)
                if cs is not None:
                    color_spaces[cs_name] = cs
            except Exception:
                logger.debug("Could not extract color space %s", cs_name)

        return color_spaces

    @staticmethod
    def _build_color_space(name: str, cs_info: Any) -> PdfColorSpace | None:  # skipcq: PY-R1000
        """Build a PdfColorSpace from a color space definition."""
        if isinstance(cs_info, str):
            # Simple device color space name
            cs_type = cs_info.lstrip("/")
            components = _DEVICE_COMPONENTS.get(cs_type, 0)
            if components > 0:
                return PdfColorSpace(name=name, cs_type=cs_type, components=components)
            return None

        if isinstance(cs_info, list) and len(cs_info) >= 1:
            cs_type_raw = cs_info[0]
            cs_type = str(cs_type_raw).lstrip("/")

            if cs_type == "ICCBased" and len(cs_info) >= 2:
                icc_ref = str(cs_info[1]) if len(cs_info) > 1 else None
                # ICC component count comes from the profile stream /N entry
                components = 3  # default assumption
                if isinstance(cs_info[1], dict):
                    components = int(cs_info[1].get("/N", 3))
                return PdfColorSpace(
                    name=name,
                    cs_type="ICCBased",
                    components=components,
                    icc_profile_ref=icc_ref,
                )

            if cs_type == "Separation" and len(cs_info) >= 3:
                # cs_info[1] is the colorant name (e.g., "PANTONE 485 C")
                colorant_name = str(cs_info[1]) if cs_info[1] else ""
                return PdfColorSpace(
                    name=name,
                    cs_type="Separation",
                    components=1,
                    colorant_names=(colorant_name,) if colorant_name else (),
                )

            if cs_type == "DeviceN" and len(cs_info) >= 3:
                colorants = cs_info[1] if isinstance(cs_info[1], list) else []
                colorant_names = tuple(str(c) for c in colorants)
                return PdfColorSpace(
                    name=name,
                    cs_type="DeviceN",
                    components=len(colorants) if colorants else 1,
                    colorant_names=colorant_names,
                )

            if cs_type == "Indexed" and len(cs_info) >= 3:
                return PdfColorSpace(
                    name=name,
                    cs_type="Indexed",
                    components=1,
                )

            if cs_type in ("CalRGB", "CalGray", "Lab"):
                components = _DEVICE_COMPONENTS.get(cs_type, 3)
                return PdfColorSpace(
                    name=name,
                    cs_type=cs_type,
                    components=components,
                )

            if cs_type == "Pattern":
                return PdfColorSpace(
                    name=name,
                    cs_type="Pattern",
                    components=0,
                )

        return None


# Component counts for known color space types
_DEVICE_COMPONENTS: dict[str, int] = {
    "DeviceRGB": 3,
    "DeviceCMYK": 4,
    "DeviceGray": 1,
    "CalRGB": 3,
    "CalGray": 1,
    "Lab": 3,
}
