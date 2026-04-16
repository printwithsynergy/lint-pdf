"""Tests for the annotated_pdf + annotated_pdf_markup report renderers.

These tests exercise the PDF content-stream overlay generators that the
mint endpoint calls when a caller requests ``annotated_pdf`` or
``annotated_pdf_markup`` — formats that previously failed silently (legend
page's hard-coded em-dash) or as HTTP 500 (uncaught exceptions bubbling
out of the render threads). Regression-style: every case here was a
production report request that didn't come back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# pikepdf is an engine runtime dep but CI may run this module standalone.
# Skip the whole suite cleanly if it's missing rather than ImportError at
# collection time.
pikepdf = pytest.importorskip("pikepdf")

from lintpdf.reports.annotated_pdf_report import generate_annotated_pdf
from lintpdf.reports.markup_pdf_report import generate_markup_pdf


_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    pdf_path = _FIXTURE_DIR / "test-sample.pdf"
    return pdf_path.read_bytes()


# ---------------------------------------------------------------------------
# annotated_pdf regression coverage
# ---------------------------------------------------------------------------


def test_annotated_pdf_renders_with_bbox_findings(sample_pdf_bytes: bytes) -> None:
    """Baseline: findings with bboxes produce a valid PDF."""
    findings = [
        {
            "inspection_id": "LPDF_IMG_001",
            "severity": "warning",
            "page_num": 1,
            "bbox": [50.0, 50.0, 200.0, 200.0],
            "message": "Low resolution",
        },
    ]
    out = generate_annotated_pdf(sample_pdf_bytes, findings, branding_name="LintPDF")
    assert out.startswith(b"%PDF-")
    # Output should be larger than input (we added overlay + legend).
    assert len(out) >= len(sample_pdf_bytes)


def test_annotated_pdf_survives_em_dash_in_branding(sample_pdf_bytes: bytes) -> None:
    """Em-dash in the branding name previously crashed the whole format.

    The legend page's ``latin-1`` content-stream encoding choked on any
    character outside latin-1 (em-dash lives in Windows-1252). Now those
    code points are replaced with ``?`` so the mint never fails.
    """
    findings = [
        {
            "inspection_id": "LPDF_IMG_001",
            "severity": "warning",
            "page_num": 1,
            "bbox": [50.0, 50.0, 200.0, 200.0],
            "message": "Low resolution",
        },
    ]
    out = generate_annotated_pdf(sample_pdf_bytes, findings, branding_name="Acme \u2014 Pro")
    assert out.startswith(b"%PDF-")


def test_annotated_pdf_survives_unicode_message(sample_pdf_bytes: bytes) -> None:
    """AI analyzers emit findings with em-dashes / emoji / CJK text.

    Any of those would have taken down the annotated PDF previously.
    """
    findings = [
        {
            "inspection_id": "AI_WCAG_001",
            "severity": "warning",
            "page_num": 1,
            "bbox": [50.0, 50.0, 200.0, 200.0],
            "message": "Contrast failure \u2014 ratio 1.0:1 \U0001f3a8 \u89c4\u8303",
        },
    ]
    out = generate_annotated_pdf(sample_pdf_bytes, findings, branding_name="LintPDF")
    assert out.startswith(b"%PDF-")


def test_annotated_pdf_summary_page_path_with_unicode(sample_pdf_bytes: bytes) -> None:
    """Doc-level findings (no bbox) go through ``_add_summary_page`` —
    separate code path, same latin-1 hazard."""
    findings = [
        {
            "inspection_id": "AI_SCAN_001",
            "severity": "advisory",
            "page_num": 0,
            "bbox": None,
            "message": "Ran 37 analyzers \u2014 emitted 86 findings",
        },
    ]
    out = generate_annotated_pdf(
        sample_pdf_bytes, findings, branding_name="Acme \u2014 Pro \U0001f3e2"
    )
    assert out.startswith(b"%PDF-")


def test_annotated_pdf_survives_parens_in_inspection_id(sample_pdf_bytes: bytes) -> None:
    """Custom mapping IDs can contain arbitrary characters including parens;
    those must be escaped so the PDF string literal doesn't close early."""
    findings = [
        {
            "inspection_id": "custom(mapping):RULE_1",
            "severity": "error",
            "page_num": 1,
            "bbox": [10.0, 10.0, 100.0, 100.0],
            "message": "Rule (A) failed because (reasons)",
        },
    ]
    out = generate_annotated_pdf(sample_pdf_bytes, findings, branding_name="LintPDF")
    assert out.startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# annotated_pdf_markup regression coverage
# ---------------------------------------------------------------------------


def test_markup_pdf_renders_rect_and_note(sample_pdf_bytes: bytes) -> None:
    """Baseline: a rectangle markup + a sticky-note with the canonical
    viewer geometry keys (``x0/y0/x1/y1`` for rect, ``x/y`` for note)."""
    annotations = [
        {
            "id": "aa1",
            "page_num": 1,
            "kind": "rect",
            "geometry": {"x0": 100, "y0": 100, "x1": 300, "y1": 180},
            "color": "#dc2626",
            "text": "rect body",
            "author_email": "reviewer@example.com",
        },
        {
            "id": "aa2",
            "page_num": 1,
            "kind": "note",
            "geometry": {"x": 300, "y": 400},
            "color": "#f59e0b",
            "text": "sticky body",
            "author_email": "reviewer@example.com",
        },
    ]
    out = generate_markup_pdf(sample_pdf_bytes, annotations, {}, branding_name="LintPDF")
    assert out.startswith(b"%PDF-")


def test_markup_pdf_survives_malformed_rect_geometry(sample_pdf_bytes: bytes) -> None:
    """The public annotations CRUD accepts any dict for ``geometry`` —
    older dashboard builds sent ``{x, y, width, height}`` instead of the
    bbox form. The renderer must not KeyError on that shape; the shape is
    just skipped (no overlay drawn) and the rest of the overlays still go
    out."""
    annotations = [
        {
            "id": "aa1",
            "page_num": 1,
            "kind": "rect",
            "geometry": {"x": 100, "y": 100, "width": 200, "height": 80},
            "color": "#dc2626",
            "text": "legacy rect",
            "author_email": "reviewer@example.com",
        },
        {
            "id": "aa2",
            "page_num": 1,
            "kind": "note",
            "geometry": {"x": 300, "y": 400},
            "color": "#f59e0b",
            "text": "canonical note",
            "author_email": "reviewer@example.com",
        },
    ]
    out = generate_markup_pdf(sample_pdf_bytes, annotations, {}, branding_name="LintPDF")
    assert out.startswith(b"%PDF-")


def test_markup_pdf_survives_unicode_everywhere(sample_pdf_bytes: bytes) -> None:
    """Note bodies, author emails, and comment threads can contain
    anything. Everything must survive the latin-1 content-stream pinch."""
    annotations = [
        {
            "id": "aa1",
            "page_num": 1,
            "kind": "note",
            "geometry": {"x": 300, "y": 400},
            "color": "#f59e0b",
            "text": "Em-dash \u2014 smart quotes \u201chello\u201d \U0001f3a8",
            "author_email": "r\u00e9viewer@example.com",
        },
    ]
    comments = {
        "aa1": [
            {
                "author_email": "\u89c4\u8303@example.com",
                "body": "Reply with CJK \u89c4\u8303 and emoji \U0001f4c4",
            }
        ]
    }
    out = generate_markup_pdf(
        sample_pdf_bytes, annotations, comments, branding_name="Acme \u2014 Pro"
    )
    assert out.startswith(b"%PDF-")


def test_markup_pdf_handles_all_kinds(sample_pdf_bytes: bytes) -> None:
    """Cover every supported ``kind`` in one call so future changes that
    touch the shape dispatcher have to keep the whole set working."""
    annotations = [
        {
            "id": "a-rect",
            "page_num": 1,
            "kind": "rect",
            "geometry": {"x0": 10, "y0": 10, "x1": 80, "y1": 80},
            "color": "#dc2626",
            "text": None,
            "author_email": "r@example.com",
        },
        {
            "id": "a-circle",
            "page_num": 1,
            "kind": "circle",
            "geometry": {"cx": 150, "cy": 150, "rx": 40, "ry": 30},
            "color": "#16a34a",
            "text": None,
            "author_email": "r@example.com",
        },
        {
            "id": "a-arrow",
            "page_num": 1,
            "kind": "arrow",
            "geometry": {"x0": 200, "y0": 200, "x1": 320, "y1": 240},
            "color": "#2563eb",
            "text": None,
            "author_email": "r@example.com",
        },
        {
            "id": "a-freehand",
            "page_num": 1,
            "kind": "freehand",
            "geometry": {"points": [{"x": 10, "y": 10}, {"x": 20, "y": 30}, {"x": 40, "y": 20}]},
            "color": "#7c3aed",
            "text": None,
            "author_email": "r@example.com",
        },
        {
            "id": "a-note",
            "page_num": 1,
            "kind": "note",
            "geometry": {"x": 400, "y": 400},
            "color": "#f59e0b",
            "text": "the one with an appendix entry",
            "author_email": "r@example.com",
        },
    ]
    out = generate_markup_pdf(sample_pdf_bytes, annotations, {}, branding_name="LintPDF")
    assert out.startswith(b"%PDF-")
