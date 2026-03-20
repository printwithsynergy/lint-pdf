"""SemanticModel — Enriched PDF document representation.

These dataclasses represent the normalized, inheritance-resolved view of a
PDF document. The SemanticModel builder populates them from the raw parser
output (PdfDocument/PdfPage from the parser layer).

Key differences from parser-layer types:
- PdfBox: validated coordinates with geometric methods
- PdfFont: includes embedding/subsetting detection
- PdfColorSpace: normalized color space with ICC profile reference
- PdfImage: includes DPI-relevant properties
- SemanticPage/SemanticDocument: enriched with fonts, images, color spaces

Reference: grounded-research/implementation-plan.md Module 2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from grounded.exceptions import InvalidBoxError

# --- Standard 14 Fonts (ISO 32000-2 §9.6.2.2) ---

STANDARD_14_FONTS: frozenset[str] = frozenset(
    {
        "Times-Roman",
        "Times-Bold",
        "Times-Italic",
        "Times-BoldItalic",
        "Helvetica",
        "Helvetica-Bold",
        "Helvetica-Oblique",
        "Helvetica-BoldOblique",
        "Courier",
        "Courier-Bold",
        "Courier-Oblique",
        "Courier-BoldOblique",
        "Symbol",
        "ZapfDingbats",
    }
)


@dataclass(frozen=True)
class PdfBox:
    """Page box representation with validation and geometry.

    Coordinates are in default user space (points, 1/72 inch).
    Origin is lower-left corner of the page.

    Attributes:
        x0: Left edge.
        y0: Bottom edge.
        x1: Right edge.
        y1: Top edge.
    """

    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x0 >= self.x1:
            raise InvalidBoxError(f"Box x0 ({self.x0}) must be less than x1 ({self.x1})")
        if self.y0 >= self.y1:
            raise InvalidBoxError(f"Box y0 ({self.y0}) must be less than y1 ({self.y1})")

    @property
    def width(self) -> float:
        """Box width in points."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Box height in points."""
        return self.y1 - self.y0

    def area(self) -> float:
        """Area in square points."""
        return self.width * self.height

    def contains_point(self, x: float, y: float) -> bool:
        """Check if point (x, y) is inside or on the box boundary."""
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def contains_box(self, other: PdfBox) -> bool:
        """Check if this box fully contains another box."""
        return (
            self.x0 <= other.x0
            and self.y0 <= other.y0
            and self.x1 >= other.x1
            and self.y1 >= other.y1
        )

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return box as (x0, y0, x1, y1) tuple."""
        return (self.x0, self.y0, self.x1, self.y1)

    @classmethod
    def from_tuple(cls, t: tuple[float, float, float, float]) -> PdfBox:
        """Create PdfBox from (x0, y0, x1, y1) tuple."""
        return cls(x0=t[0], y0=t[1], x1=t[2], y1=t[3])


@dataclass(frozen=True)
class PdfFont:
    """Font object with embedding and encoding information.

    Attributes:
        name: Font resource name (e.g., "F1").
        base_font: PostScript name (e.g., "ABCDEF+Helvetica").
        font_type: PDF font type (Type1, TrueType, Type0, Type3, CIDFontType0, CIDFontType2).
        embedded: Whether the font program is embedded.
        subset: Whether the font is subsetted (6-char prefix + "+").
        encoding: Encoding name (WinAnsiEncoding, Identity-H, etc.).
        font_descriptor: FontDescriptor dictionary, or None.
        has_to_unicode: Whether a ToUnicode CMap exists.
        cid_system_info: CIDSystemInfo dictionary for CID fonts, or None.
    """

    name: str
    base_font: str
    font_type: str
    embedded: bool
    subset: bool
    encoding: str | None = None
    font_descriptor: dict[str, Any] | None = None
    has_to_unicode: bool = False
    cid_system_info: dict[str, Any] | None = None

    def is_standard_14(self) -> bool:
        """Check if font is one of PDF's Standard 14 fonts (ISO 32000-2 §9.6.2.2)."""
        # Strip subset prefix if present (e.g., "ABCDEF+Helvetica" → "Helvetica")
        clean_name = self.base_font
        if len(clean_name) > 7 and clean_name[6] == "+":
            clean_name = clean_name[7:]
        return clean_name in STANDARD_14_FONTS

    def is_type3(self) -> bool:
        """Check if this is a Type 3 (user-drawn) font."""
        return self.font_type == "Type3"

    def is_cid_font(self) -> bool:
        """Check if this is a CID font (CIDFontType0 or CIDFontType2)."""
        return self.font_type in ("CIDFontType0", "CIDFontType2")


@dataclass(frozen=True)
class PdfColorSpace:
    """Color space definition.

    Attributes:
        name: Resource name (e.g., "CS1") or None for device spaces.
        cs_type: Color space type (DeviceRGB, DeviceCMYK, DeviceGray,
                 ICCBased, CalRGB, CalGray, Lab, Indexed,
                 Separation, DeviceN, Pattern).
        components: Number of color components.
        icc_profile_ref: Reference to ICC profile stream, or None.
        alternate: Alternate color space for ICCBased/Separation/DeviceN.
        base_space: Base color space for Indexed.
    """

    name: str | None
    cs_type: str
    components: int
    icc_profile_ref: str | None = None
    alternate: PdfColorSpace | None = None
    base_space: PdfColorSpace | None = None
    colorant_names: tuple[str, ...] = ()  # Spot color names for Separation/DeviceN

    def is_device_space(self) -> bool:
        """Check if this is a device-dependent color space."""
        return self.cs_type in ("DeviceRGB", "DeviceCMYK", "DeviceGray")

    def is_cie_based(self) -> bool:
        """Check if this is a CIE-based color space."""
        return self.cs_type in ("CalRGB", "CalGray", "Lab", "ICCBased")

    def is_cmyk(self) -> bool:
        """Check if this is a CMYK color space (device or ICC)."""
        if self.cs_type == "DeviceCMYK":
            return True
        return self.cs_type == "ICCBased" and self.components == 4


@dataclass(frozen=True)
class PdfImage:
    """Image XObject or inline image properties.

    Attributes:
        name: XObject name (e.g., "Im1") or "inline_N" for inline images.
        width: Pixel width.
        height: Pixel height.
        bits_per_component: Bits per color component.
        color_space: Color space of the image.
        filters: Compression filters applied (e.g., ["/FlateDecode"]).
        has_soft_mask: Whether image uses a soft mask (/SMask).
        has_hard_mask: Whether image uses a hard mask (/Mask as stream).
        interpolate: Whether bilinear interpolation is enabled.
        intent: Rendering intent, or None.
        inline: Whether this is an inline image (BI/ID/EI).
        page_num: Page where the image appears.
    """

    name: str
    width: int
    height: int
    bits_per_component: int
    color_space: PdfColorSpace | None
    filters: tuple[str, ...] = ()
    has_soft_mask: bool = False
    has_hard_mask: bool = False
    interpolate: bool = False
    intent: str | None = None
    inline: bool = False
    page_num: int = 0


@dataclass(frozen=True)
class PdfAnnotation:
    """PDF annotation extracted from page /Annots array.

    Attributes:
        subtype: Annotation subtype (/Text, /Link, /FreeText, /Stamp, /Sound, /Movie, /Widget, /3D, etc.).
        rect: Annotation rectangle in default user space, or None if malformed.
        flags: Annotation flags bit field (ISO 32000-2 §12.5.3).
        contents: /Contents text value.
        page_num: 1-indexed page number.
    """

    subtype: str
    rect: PdfBox | None = None
    flags: int = 0
    contents: str = ""
    page_num: int = 0

    @property
    def is_printable(self) -> bool:
        """Check Print flag (bit 3, value 0x04)."""
        return bool(self.flags & 0x04)

    @property
    def is_hidden(self) -> bool:
        """Check Hidden flag (bit 2, value 0x02)."""
        return bool(self.flags & 0x02)


@dataclass
class SemanticPage:
    """Enriched page representation with inheritance resolved.

    All box values are resolved (inherited or defaulted per spec).
    Fonts, images, and color spaces are extracted from resources.

    Attributes:
        page_num: 1-indexed page number.
        media_box: MediaBox (required — always present after resolution).
        crop_box: CropBox (defaults to MediaBox per spec).
        bleed_box: BleedBox (defaults to CropBox per spec).
        trim_box: TrimBox (defaults to CropBox per spec).
        art_box: ArtBox (defaults to CropBox per spec).
        rotate: Rotation in degrees (0, 90, 180, 270).
        user_unit: UserUnit scaling factor (default 1.0).
        fonts: Font name → PdfFont mapping.
        images: Images found on this page.
        color_spaces: Color space name → PdfColorSpace mapping.
        resources: Raw /Resources dictionary.
        content_stream: Decompressed content stream bytes.
    """

    page_num: int
    media_box: PdfBox
    crop_box: PdfBox | None = None
    bleed_box: PdfBox | None = None
    trim_box: PdfBox | None = None
    art_box: PdfBox | None = None
    rotate: int = 0
    user_unit: float = 1.0
    fonts: dict[str, PdfFont] = field(default_factory=dict)
    images: list[PdfImage] = field(default_factory=list)
    color_spaces: dict[str, PdfColorSpace] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)
    content_stream: bytes = b""
    annotations: list[PdfAnnotation] = field(default_factory=list)
    transparency_group: dict[str, Any] | None = None

    @property
    def effective_width(self) -> float:
        """Page width in points, accounting for rotation.

        Uses CropBox if available, otherwise MediaBox.
        For 90/270 degree rotation, width and height are swapped.
        """
        box = self.crop_box or self.media_box
        if self.rotate in (90, 270):
            return box.height
        return box.width

    @property
    def effective_height(self) -> float:
        """Page height in points, accounting for rotation.

        Uses CropBox if available, otherwise MediaBox.
        For 90/270 degree rotation, width and height are swapped.
        """
        box = self.crop_box or self.media_box
        if self.rotate in (90, 270):
            return box.width
        return box.height

    @property
    def effective_width_mm(self) -> float:
        """Page width in millimeters (1 point = 0.352778 mm)."""
        return self.effective_width * self.user_unit * 0.352778

    @property
    def effective_height_mm(self) -> float:
        """Page height in millimeters (1 point = 0.352778 mm)."""
        return self.effective_height * self.user_unit * 0.352778


@dataclass
class SemanticDocument:
    """Enriched document representation with all properties resolved.

    Attributes:
        version: PDF version string.
        page_count: Total number of pages.
        is_encrypted: Whether the PDF uses encryption.
        info_dict: Document Information dictionary.
        catalog: Document catalog.
        output_intents: OutputIntent dictionaries.
        metadata_stream: Raw XMP metadata bytes, or None.
        pages: Enriched pages with resolved inheritance.
    """

    version: str
    page_count: int
    is_encrypted: bool
    info_dict: dict[str, Any] = field(default_factory=dict)
    catalog: dict[str, Any] = field(default_factory=dict)
    output_intents: list[dict[str, Any]] = field(default_factory=list)
    metadata_stream: bytes | None = None
    trailer: dict[str, Any] = field(default_factory=dict)
    pages: list[SemanticPage] = field(default_factory=list)
