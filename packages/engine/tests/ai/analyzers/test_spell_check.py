"""Tests for SpellCheckAnalyzer."""

from __future__ import annotations

# skipcq: PYL-R0201
from unittest.mock import MagicMock, patch

from grounded.analyzers.finding import Severity


def _doc_with_text(page_text: str) -> MagicMock:
    """Create a SemanticDocument mock with text in the content stream."""
    page = MagicMock()
    page.page_num = 1
    page.content_stream = f"({page_text}) Tj".encode("latin-1")

    doc = MagicMock()
    doc.pages = [page]
    return doc


class TestSpellCheckAnalyzer:
    """Tests for SpellCheckAnalyzer with basic fallback mode."""

    def test_no_text_returns_empty(self, minimal_semantic_doc: MagicMock) -> None:
        """Document with no text content should produce no findings."""
        from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

        analyzer = SpellCheckAnalyzer()
        findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")
        assert findings == []

    def test_basic_check_flags_repeated_chars(self) -> None:
        """Basic fallback should flag words with 4+ repeated characters."""
        doc = _doc_with_text("The proooof is in the pudding")

        with patch(
            "grounded.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze(doc, [], b"fake_pdf")

        flagged_words = [f.details.get("word") for f in findings]
        assert "proooof" in flagged_words

    def test_basic_check_flags_mid_word_caps(self) -> None:
        """Basic fallback should flag unexpected mid-word capitalization."""
        doc = _doc_with_text("This is a weirdWord example")

        with patch(
            "grounded.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze(doc, [], b"fake_pdf")

        flagged_words = [f.details.get("word") for f in findings]
        assert "weirdWord" in flagged_words

    def test_custom_dictionary_excludes_words(self) -> None:
        """Words in the custom dictionary should not be flagged."""
        doc = _doc_with_text("The proooof is in NeverGrounded")

        ai_config = MagicMock()
        ai_config.custom_dictionary = ["proooof"]

        with patch(
            "grounded.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze(doc, [], b"fake_pdf", ai_config=ai_config)

        flagged_words = [f.details.get("word") for f in findings]
        assert "proooof" not in flagged_words

    def test_custom_dictionary_case_insensitive(self) -> None:
        """Custom dictionary matching should be case-insensitive."""
        doc = _doc_with_text("The Proooof is here")

        ai_config = MagicMock()
        ai_config.custom_dictionary = ["PROOOOF"]

        with patch(
            "grounded.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze(doc, [], b"fake_pdf", ai_config=ai_config)

        flagged_words = [f.details.get("word") for f in findings]
        assert "Proooof" not in flagged_words

    def test_findings_have_ai_source(self) -> None:
        doc = _doc_with_text("The proooof is here")

        with patch(
            "grounded.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze(doc, [], b"fake_pdf")

        assert len(findings) > 0
        for f in findings:
            assert f.source == "ai"
            assert f.category == "content_quality"
            assert f.severity == Severity.ADVISORY

    def test_analyzer_metadata(self) -> None:
        from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

        analyzer = SpellCheckAnalyzer()
        assert analyzer.category == "content_quality"
        assert analyzer.feature_slug == "spell_check"
        assert analyzer.tier == "cpu"
        assert analyzer.credits_per_run == 1

    def test_none_ai_config_handled(self) -> None:
        """Passing None for ai_config should not crash."""
        doc = _doc_with_text("Normal text here")

        with patch(
            "grounded.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze(doc, [], b"fake_pdf", ai_config=None)

        # Should not raise, may or may not have findings for normal text
        assert isinstance(findings, list)

    def test_multi_page_text(self) -> None:
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
            "grounded.ai.analyzers.content_quality.spell_check._HAS_LANGUAGE_TOOL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.spell_check import SpellCheckAnalyzer

            analyzer = SpellCheckAnalyzer()
            findings = analyzer.analyze(doc, [], b"fake_pdf")

        # Should flag the word on page 2
        page2_findings = [f for f in findings if f.page_num == 2]
        assert len(page2_findings) > 0
