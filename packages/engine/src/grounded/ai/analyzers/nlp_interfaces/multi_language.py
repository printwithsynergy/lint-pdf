"""Multi-language reports analyzer — GPU-based translation of findings.

Uses OPUS-MT on the GPU inference service to translate finding messages
into the tenant's configured languages.  Translated findings are reported
as ADVISORY with the translated text in the details payload.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from grounded.ai.base import BaseAIAnalyzer
from grounded.ai.gpu_client import GPUInferenceClient, GPUServiceUnavailableError
from grounded.ai.registry import register_ai_analyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.api.models import TenantAIConfig
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Default source language when not configured
_DEFAULT_SOURCE_LANG = "en"


def _get_gpu_client() -> GPUInferenceClient:
    from grounded.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


def _extract_document_text(document: SemanticDocument) -> str:
    """Extract concatenated text content from all pages."""
    text_parts: list[str] = []
    for page in document.pages:
        if hasattr(page, "text_content") and page.text_content:
            text_parts.append(str(page.text_content))
        elif hasattr(page, "content_stream") and page.content_stream:
            raw = page.content_stream
            if isinstance(raw, bytes):
                with contextlib.suppress(Exception):
                    text_parts.append(raw.decode("latin-1"))
            else:
                text_parts.append(str(raw))
    return "\n".join(text_parts)


@register_ai_analyzer
class MultiLanguageReportsAnalyzer(BaseAIAnalyzer):
    """Translate document text content into configured target languages."""

    category = "nlp_interfaces"
    feature_slug = "multi_language_reports"
    tier = "gpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        # Determine target languages from config
        target_languages: list[str] = []
        source_lang = _DEFAULT_SOURCE_LANG

        if ai_config is not None:
            configured_langs = getattr(ai_config, "target_languages", None)
            if configured_langs and isinstance(configured_langs, list):
                target_languages = configured_langs
            configured_source = getattr(ai_config, "source_language", None)
            if configured_source:
                source_lang = str(configured_source)

        if not target_languages:
            return [
                self._make_finding(
                    inspection_id="AI_LANG_001",
                    severity=Severity.ADVISORY,
                    message=(
                        "No target languages configured for multi-language "
                        "reports. Configure target_languages in AI settings."
                    ),
                    details={"reason": "no_target_languages"},
                )
            ]

        # Extract text to translate
        doc_text = _extract_document_text(document)
        if not doc_text.strip():
            return [
                self._make_finding(
                    inspection_id="AI_LANG_002",
                    severity=Severity.ADVISORY,
                    message="No extractable text content found for translation.",
                    details={"reason": "no_text_content"},
                )
            ]

        # Limit text length for translation to avoid timeout
        max_chars = 5000
        text_to_translate = doc_text[:max_chars]
        truncated = len(doc_text) > max_chars

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        for target_lang in target_languages:
            if target_lang == source_lang:
                continue

            try:
                result = gpu.translate_text(
                    text=text_to_translate,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )
            except GPUServiceUnavailableError as exc:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_LANG_003",
                        severity=Severity.ADVISORY,
                        message=(
                            "GPU inference service unavailable for translation "
                            f"to '{target_lang}': {exc}"
                        ),
                        details={
                            "reason": "gpu_unavailable",
                            "target_lang": target_lang,
                        },
                    )
                )
                continue

            translated_text = result.get("translated_text", "")
            model_name = result.get("model", "opus-mt")

            findings.append(
                self._make_finding(
                    inspection_id="AI_LANG_004",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document text translated from '{source_lang}' to "
                        f"'{target_lang}' ({len(translated_text)} characters)"
                    ),
                    details={
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "translated_text": translated_text,
                        "original_chars": len(text_to_translate),
                        "translated_chars": len(translated_text),
                        "truncated": truncated,
                        "model": model_name,
                    },
                )
            )

        return findings
