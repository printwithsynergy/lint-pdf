"""ParserAdapter — Abstract base class for PDF parsers.

All analyzer and inspection modules depend on this interface, never on
a concrete parser implementation (pikepdf, PyPDF2, etc.) directly.

The adapter pattern enables:
- Swapping parser implementations without touching analyzer code
- Mocking the parser for isolated rule/analyzer testing
- Future parser upgrades isolated to adapter tests

Reference: ADR-001 in grounded-research/adr/ARCHITECTURE_DECISIONS.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PdfStream:
    """Represents a PDF stream object (e.g., content stream, font program).

    Streams are objects with both a dictionary and binary data. The data
    is always stored decompressed — the adapter handles filter decoding.

    Attributes:
        dictionary: Stream dictionary entries (/Type, /Length, /Filter, etc.)
        data: Decompressed stream content as bytes.
        is_compressed: Whether the original stream was compressed.
        compression_filter: Primary compression filter name, or None.
        object_number: PDF object number (for indirect references).
        generation_number: PDF generation number.
    """

    dictionary: dict[str, Any]
    data: bytes
    is_compressed: bool
    compression_filter: str | None = None
    object_number: int = 0
    generation_number: int = 0


@dataclass(frozen=True)
class PdfObject:
    """Represents any PDF object (dict, array, stream, name, etc.).

    Used for generic object graph traversal when the caller doesn't
    know the object type in advance.

    Attributes:
        object_number: PDF object number.
        generation_number: PDF generation number.
        is_indirect: Whether this is an indirect object (has obj/endobj).
        value: Actual object content (dict, list, str, int, float, bytes, etc.).
        obj_type: Type discriminator for the value field.
    """

    object_number: int
    generation_number: int
    is_indirect: bool
    value: Any
    obj_type: str  # 'dict', 'array', 'stream', 'name', 'string', 'number', 'boolean', 'null'


@dataclass
class PdfPage:
    """Represents a single PDF page with raw properties.

    Box values are tuples of (x0, y0, x1, y1) in default user space units
    (points, 1/72 inch). The SemanticModel builder resolves inheritance
    and validates box hierarchy.

    Attributes:
        page_num: 1-indexed page number.
        page_dict: Raw page dictionary from the PDF.
        media_box: MediaBox coordinates, or None if inherited.
        crop_box: CropBox coordinates, or None.
        bleed_box: BleedBox coordinates, or None.
        trim_box: TrimBox coordinates, or None.
        art_box: ArtBox coordinates, or None.
        rotate: Page rotation in degrees (0, 90, 180, 270).
        user_unit: UserUnit scaling factor (default 1.0 = 1/72 inch).
        parent_ref: Reference to parent Pages node (for inheritance resolution).
    """

    page_num: int
    page_dict: dict[str, Any]
    media_box: tuple[float, float, float, float] | None = None
    crop_box: tuple[float, float, float, float] | None = None
    bleed_box: tuple[float, float, float, float] | None = None
    trim_box: tuple[float, float, float, float] | None = None
    art_box: tuple[float, float, float, float] | None = None
    rotate: int = 0
    user_unit: float = 1.0
    parent_ref: str | None = None


@dataclass
class PdfDocument:
    """Represents a complete PDF document with top-level metadata.

    This is the raw parsed representation. The SemanticModel builder
    enriches this with resolved inheritance, extracted fonts/images, etc.

    Attributes:
        version: PDF version string (e.g., "1.7", "2.0").
        page_count: Total number of pages.
        is_encrypted: Whether the PDF uses encryption.
        info_dict: Document Information dictionary (/Title, /Author, etc.).
        trailer: Trailer dictionary.
        catalog: Document catalog (/Root object).
        pages: List of PdfPage objects (1-indexed in page_num, 0-indexed in list).
        output_intents: List of Output Intent dictionaries.
        metadata_stream: Raw XMP metadata stream bytes, or None.
    """

    version: str
    page_count: int
    is_encrypted: bool
    info_dict: dict[str, Any] = field(default_factory=dict)
    trailer: dict[str, Any] = field(default_factory=dict)
    catalog: dict[str, Any] = field(default_factory=dict)
    pages: list[PdfPage] = field(default_factory=list)
    output_intents: list[dict[str, Any]] = field(default_factory=list)
    metadata_stream: bytes | None = None


class ParserAdapter(ABC):
    """Abstract base class for PDF parsers.

    All analyzer and inspection code depends on this interface.
    Implementations must handle:
    - All PDF versions (1.0 through 2.0)
    - Linearized PDFs
    - Incremental updates
    - Cross-reference streams and tables
    - Object streams
    - Encrypted PDFs (password = empty string)

    Implementations raise LintPDF-specific exceptions:
    - PDFStructureError: File cannot be opened at all
    - PDFParseError: Specific object parsing fails
    - PDFStreamEncodingError: Stream decompression fails
    - PDFObjectNotFoundError: Referenced object doesn't exist
    """

    @abstractmethod
    def open(self, pdf_bytes: bytes) -> PdfDocument:
        """Load and parse a PDF document from bytes.

        Args:
            pdf_bytes: Complete PDF file content as bytes.

        Returns:
            PdfDocument with pages populated.

        Raises:
            PDFStructureError: If the PDF is fundamentally malformed.
            PDFParseError: If parsing fails for recoverable reasons.
        """

    @abstractmethod
    def get_page(self, document: PdfDocument, page_num: int) -> PdfPage:
        """Retrieve a specific page by number (1-indexed).

        Args:
            document: Previously opened PdfDocument.
            page_num: Page number (1-indexed).

        Returns:
            PdfPage with raw properties extracted.

        Raises:
            PDFParseError: If page cannot be extracted.
            IndexError: If page_num is out of range.
        """

    @abstractmethod
    def get_catalog(self, document: PdfDocument) -> dict[str, Any]:
        """Get the document catalog (root object).

        The catalog contains top-level document structure:
        /Pages, /Outlines, /Names, /Dests, /ViewerPreferences,
        /PageLayout, /PageMode, /OpenAction, /Metadata, etc.

        Args:
            document: Previously opened PdfDocument.

        Returns:
            Dictionary representing the catalog object.
        """

    @abstractmethod
    def get_content_stream(self, page: PdfPage) -> bytes:
        """Extract and decompress page content stream.

        Handles both single stream and array of streams (concatenated).
        All filters are decoded — returns raw operator bytes.

        Args:
            page: PdfPage to extract content from.

        Returns:
            Decompressed content stream bytes.

        Raises:
            PDFStreamEncodingError: If decompression fails.
        """

    @abstractmethod
    def get_resources(self, page: PdfPage) -> dict[str, Any]:
        """Get page resource dictionary.

        Resources include: /Font, /XObject, /ExtGState, /ColorSpace,
        /Pattern, /Shading, /Properties.

        Note: This returns the page's own /Resources entry. Inheritance
        from parent Pages nodes is handled by the SemanticModel builder.

        Args:
            page: PdfPage to get resources from.

        Returns:
            Resource dictionary, or empty dict if no resources defined.
        """

    @abstractmethod
    def resolve_reference(self, document: PdfDocument, ref: str) -> PdfObject:
        """Resolve an indirect reference to its target object.

        Args:
            document: Previously opened PdfDocument.
            ref: Reference string in format "N G R" (e.g., "5 0 R").

        Returns:
            Resolved PdfObject.

        Raises:
            PDFObjectNotFoundError: If the reference target doesn't exist.
        """

    @abstractmethod
    def get_page_tree(self, document: PdfDocument) -> dict[str, Any]:
        """Get the page tree root (/Pages object).

        Used by the SemanticModel builder to resolve inherited properties
        by walking the page tree hierarchy.

        Args:
            document: Previously opened PdfDocument.

        Returns:
            Dictionary representing the /Pages root node.
        """

    @abstractmethod
    def get_object_by_number(
        self, document: PdfDocument, obj_num: int, gen_num: int = 0
    ) -> PdfObject:
        """Retrieve a PDF object by its object and generation numbers.

        Args:
            document: Previously opened PdfDocument.
            obj_num: Object number.
            gen_num: Generation number (default 0).

        Returns:
            PdfObject wrapping the resolved value.

        Raises:
            PDFObjectNotFoundError: If no object exists with these numbers.
        """

    @abstractmethod
    def get_page_parent_chain(self, page: PdfPage) -> list[dict[str, Any]]:
        """Walk the page tree from page to root, returning ancestor nodes.

        Used for resource inheritance resolution. Returns a list starting
        with the page's immediate parent and ending with the Pages root.

        Args:
            page: PdfPage to trace ancestry for.

        Returns:
            List of ancestor dictionaries, nearest parent first.
        """
