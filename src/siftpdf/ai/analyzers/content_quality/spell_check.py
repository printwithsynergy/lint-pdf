"""Spell-check analyzer for text content in PDF documents.

Extracts text from the semantic model and checks spelling using
language_tool_python (preferred) or a basic regex heuristic fallback.
"""

from __future__ import annotations

import contextlib
import logging
import re
from typing import TYPE_CHECKING

from siftpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from siftpdf.ai.registry import register_ai_analyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.plugin.protocol import AnalyzerContext
    from siftpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Try language_tool_python first (full grammar/spell checker)
try:
    import language_tool_python

    _HAS_LANGUAGE_TOOL = True
except ImportError:
    language_tool_python = None
    _HAS_LANGUAGE_TOOL = False


def _extract_text_per_page(document: SemanticDocument) -> dict[int, str]:
    """Extract text content per page from the semantic document.

    Iterates over TextRenderedEvent-style data embedded in content streams.
    Falls back to decoding the raw content stream bytes for basic text extraction.
    """
    texts: dict[int, str] = {}
    for page in document.pages:
        page_text_parts: list[str] = []
        if page.content_stream:
            # Basic extraction: look for text between parentheses in the content stream
            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    decoded = raw.decode("latin-1")
                except Exception:
                    decoded = ""
            else:
                decoded = str(raw)

            # Extract literal strings from PDF content stream — (text) Tj patterns
            for match in re.finditer(r"\(([^)]*)\)", decoded):
                text_fragment = match.group(1)
                # Unescape PDF string escapes
                text_fragment = text_fragment.replace("\\(", "(").replace("\\)", ")")
                text_fragment = text_fragment.replace("\\\\", "\\")
                if text_fragment.strip():
                    page_text_parts.append(text_fragment)

        if page_text_parts:
            texts[page.page_num] = " ".join(page_text_parts)
    return texts


@register_ai_analyzer
class SpellCheckAnalyzer(BaseAIAnalyzer):
    """Check spelling of text content across all pages."""

    category = "content_quality"
    feature_slug = "spell_check"
    tier = "cpu"
    credits_per_run = 1

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses document
        # + ai_config.custom_dictionary. ai_config reconstituted via
        # the same helper BaseAIAnalyzer.analyze_v2 default uses
        # to preserve attribute-access semantics.
        document = ctx.document
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        page_texts = _extract_text_per_page(document)
        if not page_texts:
            return []

        # Build custom dictionary ignore list
        custom_words: set[str] = set()
        if ai_config is not None and hasattr(ai_config, "custom_dictionary"):
            dictionary = ai_config.custom_dictionary
            if dictionary:
                custom_words = {w.lower() for w in dictionary}

        if _HAS_LANGUAGE_TOOL:
            return self._check_with_language_tool(page_texts, custom_words)

        logger.debug("language_tool_python not installed — using basic spell check fallback")
        return self._check_basic(page_texts, custom_words)

    def _check_with_language_tool(  # skipcq: PY-R1000
        self,
        page_texts: dict[int, str],
        custom_words: set[str],
    ) -> list[Finding]:
        """Use language_tool_python for comprehensive spell/grammar checking."""
        findings: list[Finding] = []

        try:
            tool = language_tool_python.LanguageTool("en-US")
        except Exception:
            logger.debug("Failed to initialize LanguageTool — skipping spell check")
            return []

        try:
            for page_num, text in page_texts.items():
                matches = tool.check(text)
                for match in matches:
                    # Only report spelling errors (MORFOLOGIK_RULE_EN_US and similar)
                    if (
                        "spell" not in match.ruleId.lower()
                        and "morfologik" not in match.ruleId.lower()
                    ):
                        continue

                    # Check if the misspelled word is in the custom dictionary
                    context = match.context
                    offset = match.offsetInContext
                    length = match.errorLength
                    misspelled = context[offset : offset + length] if offset is not None else ""

                    if misspelled.lower() in custom_words:
                        continue

                    suggestions = match.replacements[:3] if match.replacements else []

                    findings.append(
                        self._make_finding(
                            inspection_id="AI_SPELL_001",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Possible misspelling on page {page_num}: "
                                f"'{misspelled}'"
                                + (
                                    f" — suggestions: {', '.join(suggestions)}"
                                    if suggestions
                                    else ""
                                )
                            ),
                            page_num=page_num,
                            details={
                                "word": misspelled,
                                "suggestions": suggestions,
                                "rule_id": match.ruleId,
                                "offset": match.offset,
                            },
                        )
                    )
        finally:
            with contextlib.suppress(Exception):
                tool.close()

        return findings

    def _check_basic(
        self,
        page_texts: dict[int, str],
        custom_words: set[str],
    ) -> list[Finding]:
        """Basic fallback: flag words with unusual character patterns.

        This is a very rough heuristic — it flags words with mixed case in the
        middle, repeated characters (3+), or non-ASCII characters that may indicate
        encoding issues. It is not a real spell checker.
        """
        findings: list[Finding] = []

        # Patterns that suggest encoding issues or mangled text
        suspicious_patterns = [
            (re.compile(r"[a-z]{2,}[A-Z][a-z]"), "unexpected mid-word capitalisation"),
            (re.compile(r"(.)\1{3,}"), "repeated characters"),
            (re.compile(r"[\x00-\x08\x0e-\x1f]"), "control characters in text"),
        ]

        for page_num, text in page_texts.items():
            words = re.findall(r"\b[A-Za-z\u00C0-\u024F]{2,}\b", text)
            for word in words:
                if word.lower() in custom_words:
                    continue

                for pattern, reason in suspicious_patterns:
                    if pattern.search(word):
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_SPELL_002",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"Suspicious text on page {page_num}: '{word}' ({reason})"
                                ),
                                page_num=page_num,
                                details={
                                    "word": word,
                                    "reason": reason,
                                },
                            )
                        )
                        break  # One finding per word

        return findings
