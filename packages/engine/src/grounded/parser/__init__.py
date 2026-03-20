"""Grounded parser layer — PDF parsing abstraction.

This package provides an abstract interface for PDF parsing (ParserAdapter)
and a concrete implementation using pikepdf (PikePDFAdapter). All inspection
code depends on the adapter interface, never on pikepdf directly.
"""

from grounded.parser.adapter import (
    ParserAdapter,
    PdfDocument,
    PdfObject,
    PdfPage,
    PdfStream,
)

__all__ = [
    "ParserAdapter",
    "PdfDocument",
    "PdfObject",
    "PdfPage",
    "PdfStream",
]
