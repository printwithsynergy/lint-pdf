"""PikePDFAdapter — Concrete PDF parser implementation using pikepdf (QPDF).

This is the only file in Grounded that imports pikepdf directly. All other
modules depend on the ParserAdapter interface.

pikepdf provides:
- Battle-tested QPDF C++ engine (15+ years in production)
- All PDF variants: linearized, incremental updates, xref streams, object streams
- Reliable content stream extraction with filter decoding
- Excellent error recovery for malformed PDFs

Reference: ADR-001 in grounded-research/adr/ARCHITECTURE_DECISIONS.md
"""

from __future__ import annotations

import io
import logging
from typing import Any, cast

import pikepdf
from pikepdf import Array, Dictionary, Name, Object, Page, Pdf, Stream

from grounded.exceptions import (
    PDFObjectNotFoundError,
    PDFParseError,
    PDFStreamEncodingError,
    PDFStructureError,
)
from grounded.parser.adapter import (
    ParserAdapter,
    PdfDocument,
    PdfObject,
    PdfPage,
    PdfStream,
)

logger = logging.getLogger(__name__)


def _pikepdf_to_python(
    obj: Object, *, _depth: int = 0, _seen: set[int] | None = None
) -> Any:  # skipcq: PY-R1000
    """Convert a pikepdf object to a native Python type.

    pikepdf uses its own object types that wrap C++ objects.
    This function recursively converts them to standard Python types
    for use in our adapter interface.

    Includes depth limiting and cycle detection to handle circular
    references in PDF object graphs (e.g., trailer → catalog → pages → parent).

    Args:
        obj: Any pikepdf object.
        _depth: Current recursion depth (internal).
        _seen: Set of seen object ids for cycle detection (internal).

    Returns:
        Python-native equivalent (dict, list, str, int, float, bytes, bool, None).
    """
    if _depth > 20:
        return str(obj)

    if _seen is None:
        _seen = set()

    obj_id = id(obj)
    if obj_id in _seen:
        return f"<circular ref: {obj!r}>"
    _seen.add(obj_id)

    try:
        if isinstance(obj, Dictionary):
            return {
                str(k): _pikepdf_to_python(v, _depth=_depth + 1, _seen=_seen)
                for k, v in obj.items()
            }
        if isinstance(obj, Array):
            return [_pikepdf_to_python(item, _depth=_depth + 1, _seen=_seen) for item in iter(obj)]
        if isinstance(obj, Name):
            return str(obj)
        if isinstance(obj, Stream):
            # Return dict representation for stream dictionaries
            return {
                str(k): _pikepdf_to_python(v, _depth=_depth + 1, _seen=_seen)
                for k, v in obj.items()
            }
        if isinstance(obj, pikepdf.String):
            try:
                return str(obj)
            except UnicodeDecodeError:
                return bytes(obj)
        if isinstance(obj, (int, float)):
            return obj
        if isinstance(obj, bool):
            return obj

        # Attempt numeric conversion for pikepdf numeric wrappers
        try:
            int_val = int(obj)
            float_val = float(obj)
            return int_val if int_val == float_val else float_val
        except (TypeError, ValueError):
            pass

        # Fallback: string representation
        try:
            return str(obj)
        except Exception:
            return repr(obj)
    finally:
        _seen.discard(obj_id)


def _extract_box(page_dict: dict[str, Any], key: str) -> tuple[float, float, float, float] | None:
    """Extract a page box as a tuple of 4 floats.

    Args:
        page_dict: Converted page dictionary.
        key: Box key (e.g., "/MediaBox", "/CropBox").

    Returns:
        Tuple of (x0, y0, x1, y1) or None if not present.
    """
    box = page_dict.get(key)
    if box is None:
        return None
    if isinstance(box, list) and len(box) == 4:
        try:
            return (float(box[0]), float(box[1]), float(box[2]), float(box[3]))
        except (TypeError, ValueError):
            return None
    return None


class PikePDFAdapter(ParserAdapter):
    """Concrete ParserAdapter implementation using pikepdf (QPDF).

    This adapter wraps pikepdf operations and translates all objects
    to Grounded's normalized data structures. It is the only module
    that directly imports pikepdf.

    Usage:
        adapter = PikePDFAdapter()
        doc = adapter.open(pdf_bytes)
        for page in doc.pages:
            content = adapter.get_content_stream(page)
            resources = adapter.get_resources(page)
    """

    def __init__(self) -> None:
        """Initialize the adapter.

        The internal _pdf reference is set when open() is called
        and used by subsequent method calls.
        """
        self._pdf: Pdf | None = None
        self._pdf_bytes: bytes | None = None

    def _ensure_open(self) -> Pdf:
        """Ensure a PDF is currently open.

        Returns:
            The open pikepdf.Pdf instance.

        Raises:
            PDFParseError: If no PDF is currently open.
        """
        if self._pdf is None:
            raise PDFParseError("No PDF is currently open. Call open() first.")
        return self._pdf

    def open(self, pdf_bytes: bytes) -> PdfDocument:  # skipcq: PY-R1000
        """Load and parse a PDF document from bytes.

        Args:
            pdf_bytes: Complete PDF file content.

        Returns:
            PdfDocument with all pages extracted.

        Raises:
            PDFStructureError: If the PDF cannot be opened.
        """
        try:
            self._pdf_bytes = pdf_bytes
            self._pdf = Pdf.open(io.BytesIO(pdf_bytes))
        except pikepdf.PasswordError as e:
            raise PDFStructureError(f"PDF is encrypted and requires a password: {e}") from e
        except pikepdf.PdfError as e:
            raise PDFStructureError(f"Failed to open PDF: {e}") from e
        except Exception as e:
            raise PDFStructureError(f"Unexpected error opening PDF: {e}") from e

        pdf = self._pdf

        # Extract document-level metadata
        version = str(pdf.pdf_version)
        page_count = len(pdf.pages)
        is_encrypted = pdf.is_encrypted

        # Info dictionary
        info_dict: dict[str, Any] = {}
        if pdf.docinfo:
            info_dict = {str(k): _pikepdf_to_python(v) for k, v in pdf.docinfo.items()}

        # Trailer
        trailer = _pikepdf_to_python(pdf.trailer) if pdf.trailer else {}
        if not isinstance(trailer, dict):
            trailer = {}

        # Catalog
        catalog = _pikepdf_to_python(pdf.Root) if pdf.Root else {}
        if not isinstance(catalog, dict):
            catalog = {}

        # Output Intents
        output_intents: list[dict[str, Any]] = []
        raw_intents = catalog.get("/OutputIntents")
        if isinstance(raw_intents, list):
            for intent in raw_intents:
                if isinstance(intent, dict):
                    output_intents.append(intent)

        # XMP Metadata
        metadata_stream: bytes | None = None
        try:
            if pdf.Root.get("/Metadata"):
                metadata_obj = pdf.Root["/Metadata"]
                if isinstance(metadata_obj, Stream):
                    metadata_stream = bytes(metadata_obj.read_bytes())
        except Exception:
            logger.debug("Could not extract XMP metadata stream")

        # Extract pages
        pages: list[PdfPage] = []
        for i, pike_page in enumerate(pdf.pages):
            page = self._extract_page(pike_page, page_num=i + 1)
            pages.append(page)

        return PdfDocument(
            version=version,
            page_count=page_count,
            is_encrypted=is_encrypted,
            info_dict=info_dict,
            trailer=trailer,
            catalog=catalog,
            pages=pages,
            output_intents=output_intents,
            metadata_stream=metadata_stream,
        )

    @staticmethod
    def _extract_page(pike_page: Page, page_num: int) -> PdfPage:
        """Extract a PdfPage from a pikepdf Page object.

        Args:
            pike_page: pikepdf Page object.
            page_num: 1-indexed page number.

        Returns:
            PdfPage with raw properties.
        """
        page_dict = _pikepdf_to_python(pike_page.obj)
        if not isinstance(page_dict, dict):
            page_dict = {}

        # Store the raw pikepdf page reference for later use
        page_dict["_pike_page_ref"] = pike_page

        media_box = _extract_box(page_dict, "/MediaBox")
        crop_box = _extract_box(page_dict, "/CropBox")
        bleed_box = _extract_box(page_dict, "/BleedBox")
        trim_box = _extract_box(page_dict, "/TrimBox")
        art_box = _extract_box(page_dict, "/ArtBox")

        rotate_raw = page_dict.get("/Rotate", 0)
        try:
            rotate = int(rotate_raw) if rotate_raw else 0
        except (TypeError, ValueError):
            rotate = 0

        user_unit_raw = page_dict.get("/UserUnit", 1.0)
        try:
            user_unit = float(user_unit_raw) if user_unit_raw else 1.0
        except (TypeError, ValueError):
            user_unit = 1.0

        # Parent reference for inheritance resolution
        parent_ref = page_dict.get("/Parent")
        parent_ref_str = str(parent_ref) if parent_ref else None

        return PdfPage(
            page_num=page_num,
            page_dict=page_dict,
            media_box=media_box,
            crop_box=crop_box,
            bleed_box=bleed_box,
            trim_box=trim_box,
            art_box=art_box,
            rotate=rotate,
            user_unit=user_unit,
            parent_ref=parent_ref_str,
        )

    def get_page(self, document: PdfDocument, page_num: int) -> PdfPage:
        """Retrieve a specific page by number (1-indexed).

        Args:
            document: Previously opened PdfDocument.
            page_num: Page number (1-indexed).

        Returns:
            PdfPage from the document's page list.

        Raises:
            IndexError: If page_num is out of range.
        """
        if page_num < 1 or page_num > document.page_count:
            raise IndexError(f"Page {page_num} out of range (1-{document.page_count})")
        return document.pages[page_num - 1]

    def get_catalog(self, document: PdfDocument) -> dict[str, Any]:
        """Get the document catalog (root object).

        Args:
            document: Previously opened PdfDocument.

        Returns:
            Catalog dictionary.
        """
        return document.catalog

    def get_content_stream(self, page: PdfPage) -> bytes:  # skipcq: PY-R1000
        """Extract and decompress page content stream.

        Handles single stream and array of streams (concatenated with
        newline separator per ISO 32000-2 §7.8.2).

        Args:
            page: PdfPage to extract content from.

        Returns:
            Decompressed content stream bytes.

        Raises:
            PDFStreamEncodingError: If decompression fails.
        """
        pdf = self._ensure_open()
        pike_page = page.page_dict.get("_pike_page_ref")

        if pike_page is None:
            # Fallback: access page from pdf.pages
            try:
                pike_page = pdf.pages[page.page_num - 1]
            except IndexError as e:
                raise PDFParseError(f"Page {page.page_num} not found in PDF") from e

        try:
            contents = pike_page.obj.get("/Contents")
            if contents is None:
                # Page with no content stream (blank page)
                return b""

            if isinstance(contents, Array):
                # Multiple content streams — concatenate with newline
                parts: list[bytes] = []
                for stream_ref in iter(contents):
                    if isinstance(stream_ref, Stream):
                        parts.append(bytes(stream_ref.read_bytes()))
                    else:
                        # Resolve indirect reference
                        resolved = pdf.get_object(stream_ref.objgen)
                        if isinstance(resolved, Stream):
                            parts.append(bytes(resolved.read_bytes()))
                return b"\n".join(parts)

            if isinstance(contents, Stream):
                return bytes(contents.read_bytes())

            # Try to resolve as indirect reference
            resolved = pdf.get_object(cast("tuple[int, int]", contents.objgen))
            if isinstance(resolved, Stream):
                return bytes(resolved.read_bytes())

            return b""

        except pikepdf.PdfError as e:
            raise PDFStreamEncodingError(
                f"Failed to decode content stream on page {page.page_num}: {e}"
            ) from e
        except Exception as e:
            raise PDFStreamEncodingError(f"Unexpected error extracting content stream: {e}") from e

    def get_resources(self, page: PdfPage) -> dict[str, Any]:
        """Get page resource dictionary.

        Args:
            page: PdfPage to get resources from.

        Returns:
            Resource dictionary, or empty dict if none defined.
        """
        pdf = self._ensure_open()
        pike_page = page.page_dict.get("_pike_page_ref")

        if pike_page is None:
            try:
                pike_page = pdf.pages[page.page_num - 1]
            except IndexError:
                return {}

        try:
            resources = pike_page.obj.get("/Resources")
            if resources is None:
                return {}
            return _pikepdf_to_python(resources)  # type: ignore[no-any-return]
        except Exception:
            logger.debug("Could not extract resources for page %d", page.page_num)
            return {}

    def resolve_reference(self, document: PdfDocument, ref: str) -> PdfObject:
        """Resolve an indirect reference string.

        Args:
            document: Previously opened PdfDocument.
            ref: Reference string (e.g., "5 0 R").

        Returns:
            Resolved PdfObject.

        Raises:
            PDFObjectNotFoundError: If reference cannot be resolved.
        """
        self._ensure_open()

        try:
            parts = ref.strip().split()
            if len(parts) >= 2:
                obj_num = int(parts[0])
                gen_num = int(parts[1])
            else:
                raise ValueError(f"Invalid reference format: {ref}")

            return self.get_object_by_number(document, obj_num, gen_num)

        except (ValueError, TypeError) as e:
            raise PDFObjectNotFoundError(f"Cannot parse reference '{ref}': {e}") from e
        except PDFObjectNotFoundError:
            raise
        except Exception as e:
            raise PDFObjectNotFoundError(f"Failed to resolve reference '{ref}': {e}") from e

    def get_page_tree(self, document: PdfDocument) -> dict[str, Any]:
        """Get the page tree root (/Pages object).

        Args:
            document: Previously opened PdfDocument.

        Returns:
            Dictionary representing the /Pages root node.
        """
        pdf = self._ensure_open()

        try:
            pages_root = pdf.Root.get("/Pages")
            if pages_root is None:
                return {}
            return _pikepdf_to_python(pages_root)  # type: ignore[no-any-return]
        except Exception:
            return {}

    def get_object_by_number(  # skipcq: PY-R1000
        self, document: PdfDocument, obj_num: int, gen_num: int = 0
    ) -> PdfObject:
        """Retrieve a PDF object by number.

        Args:
            document: Previously opened PdfDocument.
            obj_num: Object number.
            gen_num: Generation number (default 0).

        Returns:
            PdfObject wrapping the resolved value.

        Raises:
            PDFObjectNotFoundError: If object doesn't exist.
        """
        pdf = self._ensure_open()

        try:
            raw_obj = pdf.get_object((obj_num, gen_num))
            value = _pikepdf_to_python(raw_obj)

            # Determine type
            if isinstance(raw_obj, Dictionary):
                obj_type = "dict"
            elif isinstance(raw_obj, Array):
                obj_type = "array"
            elif isinstance(raw_obj, Stream):
                obj_type = "stream"
            elif isinstance(raw_obj, Name):
                obj_type = "name"
            elif isinstance(raw_obj, pikepdf.String):
                obj_type = "string"
            elif isinstance(raw_obj, (int, float)):
                obj_type = "number"
            elif isinstance(raw_obj, bool):
                obj_type = "boolean"
            else:
                obj_type = "unknown"

            return PdfObject(
                object_number=obj_num,
                generation_number=gen_num,
                is_indirect=True,
                value=value,
                obj_type=obj_type,
            )

        except pikepdf.PdfError as e:
            raise PDFObjectNotFoundError(f"Object {obj_num} {gen_num} not found: {e}") from e
        except Exception as e:
            raise PDFObjectNotFoundError(
                f"Failed to retrieve object {obj_num} {gen_num}: {e}"
            ) from e

    def get_page_parent_chain(self, page: PdfPage) -> list[dict[str, Any]]:
        """Walk from page to root, collecting ancestor node dictionaries.

        Args:
            page: PdfPage to trace ancestry for.

        Returns:
            List of ancestor dicts, nearest parent first.
        """
        pdf = self._ensure_open()
        pike_page = page.page_dict.get("_pike_page_ref")

        if pike_page is None:
            try:
                pike_page = pdf.pages[page.page_num - 1]
            except IndexError:
                return []

        chain: list[dict[str, Any]] = []
        current = pike_page.obj

        # Walk up /Parent chain, max 100 levels to prevent infinite loops
        for _ in range(100):
            parent = current.get("/Parent")
            if parent is None:
                break
            try:
                parent_dict = _pikepdf_to_python(parent)
                if isinstance(parent_dict, dict):
                    chain.append(parent_dict)
                current = parent
            except Exception:
                break

        return chain

    def get_stream_data(self, page: PdfPage, stream_ref: str) -> PdfStream:
        """Extract a specific stream object from the PDF.

        Useful for extracting font programs, ICC profiles, etc.

        Args:
            page: PdfPage context (for resource lookup).
            stream_ref: Reference to stream object.

        Returns:
            PdfStream with decompressed data.

        Raises:
            PDFStreamEncodingError: If decompression fails.
            PDFObjectNotFoundError: If stream doesn't exist.
        """
        pdf = self._ensure_open()

        try:
            parts = stream_ref.strip().split()
            obj_num = int(parts[0])
            gen_num = int(parts[1]) if len(parts) > 1 else 0
            raw_obj = pdf.get_object((obj_num, gen_num))

            if not isinstance(raw_obj, Stream):
                raise PDFObjectNotFoundError(f"Object {stream_ref} is not a stream")

            stream_dict = {str(k): _pikepdf_to_python(v) for k, v in raw_obj.items()}
            data = bytes(raw_obj.read_bytes())
            filter_name = stream_dict.get("/Filter")
            is_compressed = filter_name is not None

            return PdfStream(
                dictionary=stream_dict,
                data=data,
                is_compressed=is_compressed,
                compression_filter=str(filter_name) if filter_name else None,
                object_number=obj_num,
                generation_number=gen_num,
            )

        except PDFObjectNotFoundError:
            raise
        except pikepdf.PdfError as e:
            raise PDFStreamEncodingError(f"Failed to decode stream {stream_ref}: {e}") from e
        except Exception as e:
            raise PDFObjectNotFoundError(f"Failed to access stream {stream_ref}: {e}") from e

    def parse_content_stream(self, page: PdfPage) -> list[tuple[list[Any], str]]:
        """Parse content stream into operator/operand pairs using pikepdf.

        This is the MVP approach — uses pikepdf's built-in parser instead
        of a custom tokenizer. Returns list of (operands, operator_name) tuples.

        Args:
            page: PdfPage to parse.

        Returns:
            List of (operands, operator_name) tuples.

        Raises:
            PDFStreamEncodingError: If content stream parsing fails.
        """
        pdf = self._ensure_open()
        pike_page = page.page_dict.get("_pike_page_ref")

        if pike_page is None:
            try:
                pike_page = pdf.pages[page.page_num - 1]
            except IndexError as e:
                raise PDFParseError(f"Page {page.page_num} not found") from e

        try:
            instructions = pikepdf.parse_content_stream(pike_page)
            result: list[tuple[list[Any], str]] = []
            for instruction in instructions:
                if isinstance(instruction, pikepdf.ContentStreamInlineImage):
                    # Inline image — wrap as special instruction
                    result.append(([], "BI_ID_EI"))
                    continue
                # ContentStreamInstruction has .operands and .operator
                operands = instruction.operands
                operator = instruction.operator
                converted_operands = [_pikepdf_to_python(op) for op in operands]
                operator_name = str(operator)
                result.append((converted_operands, operator_name))
            return result

        except pikepdf.PdfError as e:
            raise PDFStreamEncodingError(
                f"Failed to parse content stream on page {page.page_num}: {e}"
            ) from e
        except Exception as e:
            raise PDFStreamEncodingError(f"Unexpected error parsing content stream: {e}") from e

    def close(self) -> None:
        """Close the currently open PDF and release resources."""
        if self._pdf is not None:
            self._pdf.close()
            self._pdf = None
            self._pdf_bytes = None
