from __future__ import annotations

import io
import logging
from typing import Any

from inference_service.config import settings

logger = logging.getLogger(__name__)


class ImageQualityModel:
    """Image quality assessment using pyiqa MUSIQ metric.

    Lazy-loads the model on first prediction request.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load the MUSIQ model."""
        if self._loaded:
            return
        try:
            import pyiqa

            self._model = pyiqa.create_metric(
                "musiq",
                device=settings.device,
            )
            self._loaded = True
            logger.info("MUSIQ image quality model loaded on %s", settings.device)
        except ImportError:
            logger.warning(
                "pyiqa not installed; image quality model running in placeholder mode"
            )
            self._model = None
            self._loaded = True
        except Exception:
            logger.exception("Failed to load MUSIQ model")
            self._model = None
            self._loaded = True

    def predict(self, image_bytes: bytes) -> dict:
        """Assess quality of an image.

        Args:
            image_bytes: Raw bytes of the image file.

        Returns:
            Dictionary with score (0-100), grade, and issues list.
        """
        self.load()

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        if self._model is None:
            return {
                "score": 50.0,
                "grade": "unknown",
                "issues": ["model_not_available"],
            }

        try:
            import torch
            import torchvision.transforms as T

            transform = T.Compose(
                [
                    T.Resize((224, 224)),
                    T.ToTensor(),
                ]
            )
            tensor = transform(image).unsqueeze(0).to(settings.device)

            with torch.no_grad():
                raw_score = self._model(tensor).item()

            # MUSIQ outputs roughly 0-100 range
            score = max(0.0, min(100.0, raw_score))

            grade = _score_to_grade(score)
            issues = _detect_issues(score)

            return {
                "score": round(score, 2),
                "grade": grade,
                "issues": issues,
            }
        except Exception:
            logger.exception("Error during image quality prediction")
            return {
                "score": 0.0,
                "grade": "error",
                "issues": ["prediction_failed"],
            }


def _score_to_grade(score: float) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    if score >= 20:
        return "poor"
    return "bad"


def _detect_issues(score: float) -> list[str]:
    issues: list[str] = []
    if score < 30:
        issues.append("very_low_quality")
    if score < 50:
        issues.append("below_average")
    return issues
