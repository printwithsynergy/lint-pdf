"""PDF/VT structural validation (T5-N01).

PDF/VT-1/2/3 (ISO 16612-2) is a variable-data printing extension
of PDF/X-4. Conformance requires:

- PDF/X-4 base conformance (delegated to veraPDF via the existing
  ``run_verapdf_checks`` for ``conformance="pdfx4"``).
- ``/Catalog /DPartRoot`` reference describing the document-part
  hierarchy.
- ``/DPart`` nodes with the appropriate ``/DPM`` (Document Part
  Metadata) for each variable record.
- XMP ``pdfvtid:GTS_PDFVTVersion`` set to one of
  ``PDF/VT-1`` / ``PDF/VT-2`` / ``PDF/VT-3``.

This module emits ``LPDF_PDFVT_STRUCTURE`` (warning) when the
document declares PDF/VT in its XMP metadata but the structural
expectations are missing. Silent on documents that don't declare
PDF/VT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.conformance.xmp import XmpMetadata

if TYPE_CHECKING:
    from lintpdf.semantic.model import SemanticDocument


__all__ = ["check_pdfvt_structure"]


def _detect_pdfvt_version(xmp: XmpMetadata, raw_xmp: bytes) -> str:
    """Return the declared PDF/VT version (e.g. ``PDF/VT-1``) or
    empty string when not declared."""
    for key, value in xmp.raw_properties.items():
        lower_key = key.lower()
        if "pdfvt" in lower_key or "pdf/vt" in lower_key:
            return str(value)
    if raw_xmp:
        try:
            text = raw_xmp.decode("utf-8", errors="replace").lower()
        except Exception:
            text = ""
        if "pdf/vt-1" in text:
            return "PDF/VT-1"
        if "pdf/vt-2" in text:
            return "PDF/VT-2"
        if "pdf/vt-3" in text:
            return "PDF/VT-3"
    return ""


def check_pdfvt_structure(document: SemanticDocument) -> list[Finding]:
    """T5-N01 — emit ``LPDF_PDFVT_STRUCTURE`` when the document
    declares PDF/VT but lacks the required structural elements."""
    raw_xmp = document.metadata_stream or b""
    if not raw_xmp:
        return []

    xmp = XmpMetadata.from_bytes(raw_xmp)
    version = _detect_pdfvt_version(xmp, raw_xmp)
    if not version:
        # No PDF/VT declaration → check is silent on non-VT files.
        return []

    catalog = document.catalog or {}
    has_dpart_root = "/DPartRoot" in catalog
    issues: list[str] = []
    if not has_dpart_root:
        issues.append("missing_dpart_root")

    if not issues:
        return []

    return [
        Finding(
            inspection_id="LPDF_PDFVT_STRUCTURE",
            severity=Severity.WARNING,
            message=(
                f"Document declares {version} but lacks required structural "
                f"elements: {', '.join(issues)}"
            ),
            details={
                "declared_version": version,
                "issues": issues,
                "validator": "lintpdf-pdfvt-structural",
            },
            iso_clause="ISO 16612-2 (PDF/VT)",
        )
    ]
