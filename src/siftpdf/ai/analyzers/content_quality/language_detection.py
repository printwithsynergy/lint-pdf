"""Language detection analyzer using fastText.

Extracts text from each page and detects the language(s) present in
the document, reporting per-page and overall language detection results.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from siftpdf.ai.base import BaseAIAnalyzer
from siftpdf.ai.registry import register_ai_analyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.plugin.protocol import AnalyzerContext
    from siftpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

try:
    import fasttext

    _HAS_FASTTEXT = True
except ImportError:
    fasttext = None
    _HAS_FASTTEXT = False


def _extract_text_per_page(document: SemanticDocument) -> dict[int, str]:
    """Extract text content per page from content streams."""
    texts: dict[int, str] = {}
    for page in document.pages:
        page_text_parts: list[str] = []
        if page.content_stream:
            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    decoded = raw.decode("latin-1")
                except Exception:
                    decoded = ""
            else:
                decoded = str(raw)

            for match in re.finditer(r"\(([^)]*)\)", decoded):
                text_fragment = match.group(1)
                text_fragment = text_fragment.replace("\\(", "(").replace("\\)", ")")
                text_fragment = text_fragment.replace("\\\\", "\\")
                if text_fragment.strip():
                    page_text_parts.append(text_fragment)

        if page_text_parts:
            texts[page.page_num] = " ".join(page_text_parts)
    return texts


# Singleton model holder to avoid reloading on every call
_ft_state: dict[str, Any] = {"model": None}


def _get_fasttext_model() -> Any:
    """Load the fastText language identification model (lid.176.ftz)."""
    if _ft_state["model"] is not None:
        return _ft_state["model"]

    import os

    # Standard locations for the pre-trained model
    candidates = [
        os.path.expanduser("~/.fasttext/lid.176.ftz"),
        "/usr/share/fasttext/lid.176.ftz",
        os.path.join(os.path.dirname(__file__), "lid.176.ftz"),
    ]

    for path in candidates:
        if os.path.isfile(path):
            _ft_state["model"] = fasttext.load_model(path)
            return _ft_state["model"]

    # Try downloading the compact model
    try:
        import urllib.request

        url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
        model_dir = os.path.expanduser("~/.fasttext")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "lid.176.ftz")
        urllib.request.urlretrieve(
            url, model_path
        )  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        _ft_state["model"] = fasttext.load_model(model_path)
        return _ft_state["model"]
    except Exception:
        logger.debug("Could not download fastText language model")
        return None


@register_ai_analyzer
class LanguageDetectionAnalyzer(BaseAIAnalyzer):
    """Detect language(s) present in document text using fastText."""

    category = "content_quality"
    feature_slug = "language_detection"
    tier = "cpu"
    credits_per_run = 1

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses document
        # only. ai_config + events + pdf_bytes were declared but
        # never used; dropped.
        document = ctx.document

        if not _HAS_FASTTEXT:
            logger.debug("fasttext not installed — skipping language detection")
            return []

        model = _get_fasttext_model()
        if model is None:
            logger.debug("fastText model not available — skipping language detection")
            return []

        page_texts = _extract_text_per_page(document)
        if not page_texts:
            return []

        findings: list[Finding] = []
        page_languages: dict[int, list[tuple[str, float]]] = {}

        for page_num, text in page_texts.items():
            # fastText expects single-line input, replace newlines
            clean_text = text.replace("\n", " ").strip()
            if len(clean_text) < 10:
                # Too little text for reliable detection
                continue

            try:
                labels, scores = model.predict(clean_text, k=3)
            except Exception:
                logger.debug("fastText prediction failed for page %d", page_num)
                continue

            # labels are like ['__label__en', '__label__fr', ...]
            detected: list[tuple[str, float]] = []
            for label, score in zip(labels, scores, strict=False):
                lang_code = label.replace("__label__", "")
                confidence = round(float(score), 4)
                if confidence > 0.01:
                    detected.append((lang_code, confidence))

            if detected:
                page_languages[page_num] = detected

        if not page_languages:
            return []

        # Determine overall document language (most common primary)
        primary_counts: dict[str, int] = {}
        for langs in page_languages.values():
            primary = langs[0][0]
            primary_counts[primary] = primary_counts.get(primary, 0) + 1

        overall_language = max(primary_counts, key=primary_counts.get)  # type: ignore[arg-type]
        total_pages = len(page_languages)

        # Document-level finding
        lang_summary = ", ".join(
            f"{lang} ({count}/{total_pages} pages)"
            for lang, count in sorted(primary_counts.items(), key=lambda x: -x[1])
        )
        findings.append(
            self._make_finding(
                inspection_id="AI_LANG_001",
                severity=Severity.ADVISORY,
                message=f"Detected languages: {lang_summary}. Primary: {overall_language}",
                details={
                    "primary_language": overall_language,
                    "language_distribution": primary_counts,
                    "pages_analyzed": total_pages,
                },
            )
        )

        # Per-page findings for pages with different primary language
        for page_num, langs in page_languages.items():
            primary_lang, confidence = langs[0]
            if primary_lang != overall_language:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_LANG_002",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Page {page_num} language ({primary_lang}, "
                            f"confidence {confidence:.1%}) differs from "
                            f"document primary ({overall_language})"
                        ),
                        page_num=page_num,
                        details={
                            "page_language": primary_lang,
                            "confidence": confidence,
                            "all_detected": [
                                {"language": lang, "confidence": s} for lang, s in langs
                            ],
                        },
                    )
                )

        return findings
