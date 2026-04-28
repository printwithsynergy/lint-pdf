"""Tests for Batch 9a Tier-4 A11y trio (T4-A06, T4-A07, T4-A09)."""

from __future__ import annotations

from lintpdf.analyzers.accessibility import AccessibilityAnalyzer
from lintpdf.analyzers.finding import Severity
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc_with_struct(struct_root: dict, **kwargs) -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=kwargs.get("is_encrypted", False),
        catalog={"/StructTreeRoot": struct_root, "/Lang": "en"},
        trailer=kwargs.get("trailer", {}),
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


# ────────────────────────────────────────────────────────────────────
# T4-A06 — table structure
# ────────────────────────────────────────────────────────────────────


class TestTableStructure:
    @staticmethod
    def test_th_without_scope_fires() -> None:
        struct_root = {
            "/K": [
                {
                    "/S": "/Table",
                    "/K": [
                        {
                            "/S": "/TR",
                            "/K": [
                                {"/S": "/TH"},  # No /A /Scope
                                {"/S": "/TH"},  # No /A /Scope
                            ],
                        }
                    ],
                }
            ]
        }
        doc = _doc_with_struct(struct_root)
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        ts = [f for f in findings if f.inspection_id == "LPDF_ACCESS_TABLE_STRUCTURE"]
        assert len(ts) == 1
        assert ts[0].severity == Severity.WARNING
        assert ts[0].details["missing_scope_count"] == 2
        assert ts[0].details["table_count"] == 1

    @staticmethod
    def test_th_with_scope_silent() -> None:
        struct_root = {
            "/K": [
                {
                    "/S": "/Table",
                    "/K": [
                        {
                            "/S": "/TR",
                            "/K": [
                                {"/S": "/TH", "/A": {"/Scope": "/Col"}},
                                {"/S": "/TH", "/A": {"/Scope": "/Col"}},
                            ],
                        }
                    ],
                }
            ]
        }
        doc = _doc_with_struct(struct_root)
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        ts = [f for f in findings if f.inspection_id == "LPDF_ACCESS_TABLE_STRUCTURE"]
        assert ts == []

    @staticmethod
    def test_th_with_headers_silent() -> None:
        """/Headers attribute is acceptable in lieu of /Scope."""
        struct_root = {
            "/K": {
                "/S": "/Table",
                "/K": {"/S": "/TH", "/A": {"/Headers": ["/h1"]}},
            }
        }
        doc = _doc_with_struct(struct_root)
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        ts = [f for f in findings if f.inspection_id == "LPDF_ACCESS_TABLE_STRUCTURE"]
        assert ts == []


# ────────────────────────────────────────────────────────────────────
# T4-A07 — heading hierarchy skips
# ────────────────────────────────────────────────────────────────────


class TestHeadingSkip:
    @staticmethod
    def test_h1_to_h3_fires() -> None:
        struct_root = {
            "/K": [
                {"/S": "/H1"},
                {"/S": "/H3"},  # Skip — no H2
            ]
        }
        doc = _doc_with_struct(struct_root)
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        skips = [f for f in findings if f.inspection_id == "LPDF_ACCESS_HEADING_SKIP"]
        assert len(skips) == 1
        assert skips[0].severity == Severity.WARNING
        assert skips[0].details["worst_skip_from"] == "H1"
        assert skips[0].details["worst_skip_to"] == "H3"
        assert skips[0].details["skip_count"] == 1

    @staticmethod
    def test_consecutive_levels_silent() -> None:
        struct_root = {
            "/K": [
                {"/S": "/H1"},
                {"/S": "/H2"},
                {"/S": "/H3"},
                {"/S": "/H2"},  # Going back up is fine
            ]
        }
        doc = _doc_with_struct(struct_root)
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        skips = [f for f in findings if f.inspection_id == "LPDF_ACCESS_HEADING_SKIP"]
        assert skips == []

    @staticmethod
    def test_multiple_skips_reports_worst() -> None:
        struct_root = {
            "/K": [
                {"/S": "/H1"},
                {"/S": "/H4"},  # Skip 3 levels (worst)
                {"/S": "/H1"},
                {"/S": "/H3"},  # Skip 1 level (smaller gap)
            ]
        }
        doc = _doc_with_struct(struct_root)
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        skips = [f for f in findings if f.inspection_id == "LPDF_ACCESS_HEADING_SKIP"]
        assert len(skips) == 1
        assert skips[0].details["skip_count"] == 2
        assert skips[0].details["worst_skip_from"] == "H1"
        assert skips[0].details["worst_skip_to"] == "H4"


# ────────────────────────────────────────────────────────────────────
# T4-A09 — encryption screen-reader permission
# ────────────────────────────────────────────────────────────────────


class TestScreenReaderPermission:
    @staticmethod
    def test_unencrypted_silent() -> None:
        doc = _doc_with_struct({}, is_encrypted=False)
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        sr = [f for f in findings if f.inspection_id == "LPDF_ACCESS_SCREEN_READER"]
        assert sr == []

    @staticmethod
    def test_bit10_cleared_fires() -> None:
        """/P bit 10 = 0 → screen reader denied. P = -3904 (0xFFFFF0C0)
        clears bit 9 (= ISO 'bit 10'); standard 'extract restricted'."""
        doc = _doc_with_struct(
            {},
            is_encrypted=True,
            trailer={"/Encrypt": {"/P": -3904}},
        )
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        sr = [f for f in findings if f.inspection_id == "LPDF_ACCESS_SCREEN_READER"]
        assert len(sr) == 1
        assert sr[0].severity == Severity.WARNING
        assert sr[0].details["screen_reader_allowed"] is False

    @staticmethod
    def test_bit10_set_silent() -> None:
        """All permissions allowed (P = -1 = 0xFFFFFFFF) → silent."""
        doc = _doc_with_struct(
            {},
            is_encrypted=True,
            trailer={"/Encrypt": {"/P": -1}},
        )
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        sr = [f for f in findings if f.inspection_id == "LPDF_ACCESS_SCREEN_READER"]
        assert sr == []

    @staticmethod
    def test_no_p_value_silent() -> None:
        doc = _doc_with_struct(
            {},
            is_encrypted=True,
            trailer={"/Encrypt": {"/Filter": "/Standard"}},
        )
        findings = AccessibilityAnalyzer().analyze(doc, events=[])
        sr = [f for f in findings if f.inspection_id == "LPDF_ACCESS_SCREEN_READER"]
        assert sr == []
