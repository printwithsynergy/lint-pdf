from __future__ import annotations

import logging
from typing import Any

from inference_service.config import settings

logger = logging.getLogger(__name__)


class Translator:
    """Text translation using Helsinki-NLP OPUS-MT models via transformers.

    Supports translation between multiple language pairs using the
    Helsinki-NLP/opus-mt-* family of models.
    Lazy-loads models per language pair on first request.
    """

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._tokenizers: dict[str, Any] = {}
        self._loaded_pairs: set[str] = set()

    @staticmethod
    def _get_pair_key(source_lang: str, target_lang: str) -> str:
        return f"{source_lang}-{target_lang}"

    def _load_pair(self, source_lang: str, target_lang: str) -> bool:
        """Load a translation model for a specific language pair."""
        pair_key = self._get_pair_key(source_lang, target_lang)
        if pair_key in self._loaded_pairs:
            return pair_key in self._models

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
            cache_dir = settings.model_cache_dir

            tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            model.to(settings.device)
            model.eval()

            self._models[pair_key] = model
            self._tokenizers[pair_key] = tokenizer
            self._loaded_pairs.add(pair_key)
            logger.info("OPUS-MT %s model loaded on %s", pair_key, settings.device)
            return True

        except ImportError:
            logger.warning(
                "transformers not installed; translator running in placeholder mode"
            )
            self._loaded_pairs.add(pair_key)
            return False
        except Exception:
            logger.exception("Failed to load OPUS-MT model for %s", pair_key)
            self._loaded_pairs.add(pair_key)
            return False

    def load(self) -> None:
        """Pre-load common language pairs."""
        # Pre-load the most common pair; others loaded lazily
        self._load_pair("en", "fr")

    def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "fr",
    ) -> dict:
        """Translate text between languages.

        Args:
            text: The text to translate.
            source_lang: ISO 639-1 source language code.
            target_lang: ISO 639-1 target language code.

        Returns:
            Dictionary with translated_text, source_lang, target_lang.
        """
        pair_key = self._get_pair_key(source_lang, target_lang)
        available = self._load_pair(source_lang, target_lang)

        if not available:
            return {
                "translated_text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "error": f"Translation model not available for {pair_key}",
            }

        try:
            import torch

            model = self._models[pair_key]
            tokenizer = self._tokenizers[pair_key]

            inputs = tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512
            )
            inputs = {k: v.to(settings.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=512, num_beams=4)

            translated = tokenizer.decode(outputs[0], skip_special_tokens=True)

            return {
                "translated_text": translated,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }

        except Exception:
            logger.exception("Error during translation")
            return {
                "translated_text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "error": "translation_failed",
            }
