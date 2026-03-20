from __future__ import annotations

import logging
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


class NSFWDetector:
    """NSFW content detection using NudeNet.

    Lazy-loads the model on first detection request.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load the NudeNet model."""
        if self._loaded:
            return
        try:
            from nudenet import NudeDetector

            self._model = NudeDetector()
            self._loaded = True
            logger.info("NudeNet detector loaded")
        except ImportError:
            logger.warning(
                "nudenet not installed; NSFW detector running in placeholder mode"
            )
            self._model = None
            self._loaded = True
        except Exception:
            logger.exception("Failed to load NudeNet")
            self._model = None
            self._loaded = True

    def detect(self, image_bytes: bytes) -> dict:
        """Detect NSFW content in an image.

        Args:
            image_bytes: Raw bytes of the image file.

        Returns:
            Dictionary with detections list, each containing category,
            confidence, and bbox.
        """
        self.load()

        detections: list[dict] = []

        if self._model is None:
            return {"detections": detections, "is_nsfw": False}

        try:
            # NudeNet requires a file path, so write to a temp file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
                tmp.write(image_bytes)
                tmp.flush()
                results = self._model.detect(tmp.name)

            is_nsfw = False
            unsafe_categories = {
                "FEMALE_BREAST_EXPOSED",
                "FEMALE_GENITALIA_EXPOSED",
                "MALE_GENITALIA_EXPOSED",
                "BUTTOCKS_EXPOSED",
                "ANUS_EXPOSED",
            }

            for det in results:
                category = det.get("class", "unknown")
                confidence = det.get("score", 0.0)
                box = det.get("box", [0, 0, 0, 0])

                if len(box) == 4:
                    bbox = {
                        "x1": box[0],
                        "y1": box[1],
                        "x2": box[2],
                        "y2": box[3],
                    }
                else:
                    bbox = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

                if category in unsafe_categories and confidence > 0.5:
                    is_nsfw = True

                detections.append(
                    {
                        "category": category,
                        "confidence": round(confidence, 4),
                        "bbox": bbox,
                    }
                )

            return {"detections": detections, "is_nsfw": is_nsfw}

        except Exception:
            logger.exception("Error during NSFW detection")
            return {"detections": [], "is_nsfw": False}
