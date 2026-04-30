"""Tests for SpellCheckAnalyzer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lintpdf.analyzers.finding import Severity
from lintpdf.plugin import AnalyzerContext


def _doc_with_text(page_text: str) -> MagicMock:
    """Create a SemanticDocument mock with text in the content stream."""
    page = MagicMock()
    page.page_num = 1
    page.content_stream = f"({page_text}) Tj".encode("latin-1")

    doc = MagicMock()
    doc.pages = [page]
    return doc


def _ctx(document: MagicMock, ai_config: dict | None = None) -> AnalyzerContext:
    """Build an AnalyzerContext mirroring orchestrator-driven analyze_v2 calls.

    Phase 2 alpha-stream batch 3 migrated SpellCheckAnalyzer from
    legacy analyze() to analyze_v2(ctx); ai_config flows through
    config["ai_config"] as a plain dict (or None).
    """
    return AnalyzerContext(
        document=document,
        events=[],
        pdf_bytes=b"fake_pdf",
        config={"ai_config": ai_config} if ai_config is not None else {},
    )


class TestSpellCheckAnalyzer:
    """Tests for SpellCheckAnalyzer with basic fallback mode."""

    @staticmethod
    def test_no_text_returns_empty(minimal_semantic_doc: MagicMock) -> None:
        """Document with no text content should produce no findings."""
        from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

        analyzer = SpellCheckAnalyzer()
        findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc))
        assert findings == []

    @staticmethod
    def test_basic_check_flags_repeated_chars() -> None:
        """Basic fallback should flag words with 4+ repeated characters."""
        doc = _doc_with_text("The proooof is in the pudding")

        with patch(
            "lintpdf.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze_v2(_ctx(doc))

        flagged_words = [f.details.get("word") for f in findings]
        assert "proooof" in flagged_words

    @staticmethod
    def test_basic_check_flags_mid_word_caps() -> None:
        """Basic fallback should flag unexpected mid-word capitalization."""
        doc = _doc_with_text("This is a weirdWord example")

        with patch(
            "lintpdf.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze_v2(_ctx(doc))

        flagged_words = [f.details.get("word") for f in findings]
        assert "weirdWord" in flagged_words

    @staticmethod
    def test_custom_dictionary_excludes_words() -> None:
        """Words in the custom dictionary should not be flagged."""
        doc = _doc_with_text("The proooof is in LintPDF")

        with patch(
            "lintpdf.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze_v2(_ctx(doc, {"custom_dictionary": ["proooof"]}))

        flagged_words = [f.details.get("word") for f in findings]
        assert "proooof" not in flagged_words

    @staticmethod
    def test_custom_dictionary_case_insensitive() -> None:
        """Custom dictionary matching should be case-insensitive."""
        doc = _doc_with_text("The Proooof is here")

        with patch(
            "lintpdf.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze_v2(_ctx(doc, {"custom_dictionary": ["PROOOOF"]}))

        flagged_words = [f.details.get("word") for f in findings]
        assert "Proooof" not in flagged_words

    @staticmethod
    def test_findings_have_ai_source() -> None:
        doc = _doc_with_text("The proooof is here")

        with patch(
            "lintpdf.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze_v2(_ctx(doc))

        assert len(findings) > 0
        for f in findings:
            assert f.source == "ai"
            assert f.category == "content_quality"
            assert f.severity == Severity.ADVISORY

    @staticmethod
    def test_analyzer_metadata() -> None:
        from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

        analyzer = SpellCheckAnalyzer()
        assert analyzer.category == "content_quality"
        assert analyzer.feature_slug == "spell_check"
        assert analyzer.tier == "cpu"
        assert analyzer.credits_per_run == 1

    @staticmethod
    def test_none_ai_config_handled() -> None:
        """Passing None for ai_config should not crash."""
        doc = _doc_with_text("Normal text here")

        with patch(
            "lintpdf.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze_v2(_ctx(doc))

        # Should not raise, may or may not have findings for normal text
        assert isinstance(findings, list)

    @staticmethod
    def test_multi_page_text() -> None:
        """Analyzer should process text from multiple pages."""
        page1 = MagicMock()
        page1.page_num = 1
        page1.content_stream = b"(Normal text) Tj"

        page2 = MagicMock()
        page2.page_num = 2
        page2.content_stream = b"(The proooof is here) Tj"

        doc = MagicMock()
        doc.pages = [page1, page2]

        with patch(
            "lintpdf.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from lintpdf.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze_v2(_ctx(doc))

        # Should flag the word on page 2
        page2_findings = [f for f in findings if f.page_num == 2]
        assert len(page2_findings) > 0
