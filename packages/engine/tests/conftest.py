"""Shared test fixtures for LintPDF test suite."""

from pathlib import Path

import pytest

# Paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CORPUS_DIR = Path(__file__).parent / "corpus"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def corpus_dir() -> Path:
    """Path to downloaded test corpus directory."""
    return CORPUS_DIR


@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    """Minimal valid PDF (1 page, no content).

    This is a hand-crafted minimal PDF that passes basic structure
    validation. It has a single blank page with a MediaBox.
    """
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n206\n%%EOF\n"
    )


@pytest.fixture
def sample_pdf_path(tmp_path: Path, minimal_pdf_bytes: bytes) -> Path:
    """Write minimal PDF to a temporary file and return its path."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(minimal_pdf_bytes)
    return pdf_path
