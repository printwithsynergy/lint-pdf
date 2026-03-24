from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np

from inference_service.config import settings

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR text detection using PaddleOCR.

    Falls back to a placeholder if PaddleOCR is not available.
    Lazy-loads the engine on first detection request.
    """

    def __init__(self) -> None:
        self._engine: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load the PaddleOCR engine."""
        if self._loaded:
            return
        try:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False,  # CPU PaddlePaddle; GPU work via PyTorch models
                show_log=False,
            )
            self._loaded = True
            logger.info("PaddleOCR engine loaded (GPU=%s)", settings.device == "cuda")
        except ImportError:
            logger.warning(
                "paddleocr not installed; OCR engine running in placeholder mode"
            )
            self._engine = None
            self._loaded = True
        except Exception:
            logger.exception("Failed to load PaddleOCR")
            self._engine = None
            self._loaded = True

    def detect(self, image_bytes: bytes) -> dict:
        """Detect and recognize text regions in an image.

        Args:
            image_bytes: Raw bytes of the image file.

        Returns:
            Dictionary with text_regions list, each containing text, confidence,
            and bbox (polygon points).
        """
        self.load()

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        text_regions: list[dict] = []

        if self._engine is None:
            return {"text_regions": text_regions}

        try:
            img_array = np.array(image)
            results = self._engine.ocr(img_array, cls=True)

            if results and results[0]:
                for line in results[0]:
                    polygon = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    text_info = line[1]  # (text, confidence)

                    text = text_info[0]
                    confidence = float(text_info[1])

                    # Convert polygon to bbox dict
                    xs = [p[0] for p in polygon]
                    ys = [p[1] for p in polygon]
                    bbox = {
                        "x1": round(min(xs), 1),
                        "y1": round(min(ys), 1),
                        "x2": round(max(xs), 1),
                        "y2": round(max(ys), 1),
                        "polygon": [[round(p[0], 1), round(p[1], 1)] for p in polygon],
                    }

                    text_regions.append(
                        {
                            "text": text,
                            "confidence": round(confidence, 4),
                            "bbox": bbox,
                        }
                    )

        except Exception:
            logger.exception("Error during OCR detection")

        return {"text_regions": text_regions}
