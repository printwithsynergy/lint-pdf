from __future__ import annotations

import io
import logging
from typing import Any

from inference_service.config import settings

logger = logging.getLogger(__name__)

CATEGORIES = [
    "packaging_label",
    "packaging_folding_carton",
    "packaging_flexible",
    "packaging_corrugated",
    "commercial_print",
    "wide_format",
    "newspaper",
    "business_card",
    "brochure",
    "poster",
    "book_cover",
    "other",
]

# Mapping from RVL-CDIP labels to our domain categories
_RVLCDIP_TO_CATEGORY = {
    "letter": "commercial_print",
    "form": "commercial_print",
    "email": "other",
    "handwritten": "other",
    "advertisement": "poster",
    "scientific_report": "commercial_print",
    "scientific_publication": "book_cover",
    "specification": "commercial_print",
    "file_folder": "other",
    "news_article": "newspaper",
    "budget": "commercial_print",
    "invoice": "commercial_print",
    "presentation": "wide_format",
    "questionnaire": "commercial_print",
    "resume": "commercial_print",
    "memo": "commercial_print",
}


class DocumentClassifier:
    """Document / print-type classifier using DiT (Document Image Transformer).

    Lazy-loads the model on first prediction request.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._processor: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load the DiT classification model."""
        if self._loaded:
            return
        try:
            from transformers import AutoImageProcessor, AutoModelForImageClassification

            model_name = "microsoft/dit-base-finetuned-rvlcdip"
            cache_dir = settings.model_cache_dir

            self._processor = AutoImageProcessor.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            self._model = AutoModelForImageClassification.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            self._model.to(settings.device)
            self._model.eval()
            self._loaded = True
            logger.info("DiT classifier loaded on %s", settings.device)
        except ImportError:
            logger.warning(
                "transformers not installed; classifier running in placeholder mode"
            )
            self._model = None
            self._loaded = True
        except Exception:
            logger.exception("Failed to load DiT model")
            self._model = None
            self._loaded = True

    def predict(self, image_bytes: bytes) -> dict:
        """Classify a document image.

        Args:
            image_bytes: Raw bytes of the image file.

        Returns:
            Dictionary with category, confidence, and top_3 predictions.
        """
        self.load()

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        if self._model is None or self._processor is None:
            return {
                "category": "other",
                "confidence": 0.0,
                "top_3": [
                    {"category": "other", "confidence": 0.0},
                ],
            }

        try:
            import torch

            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {k: v.to(settings.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)

            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)[0]

            # Map RVL-CDIP labels to our categories
            id2label = self._model.config.id2label
            scored: list[tuple[str, float]] = []
            for idx, prob in enumerate(probs):
                rvl_label = id2label.get(idx, "other")
                category = _RVLCDIP_TO_CATEGORY.get(rvl_label, "other")
                scored.append((category, prob.item()))

            # Aggregate scores by category
            cat_scores: dict[str, float] = {}
            for cat, score in scored:
                cat_scores[cat] = cat_scores.get(cat, 0.0) + score

            ranked = sorted(cat_scores.items(), key=lambda x: x[1], reverse=True)
            top_category, top_confidence = ranked[0]

            top_3 = [
                {"category": cat, "confidence": round(conf, 4)}
                for cat, conf in ranked[:3]
            ]

            return {
                "category": top_category,
                "confidence": round(top_confidence, 4),
                "top_3": top_3,
            }
        except Exception:
            logger.exception("Error during document classification")
            return {
                "category": "other",
                "confidence": 0.0,
                "top_3": [{"category": "other", "confidence": 0.0}],
            }
