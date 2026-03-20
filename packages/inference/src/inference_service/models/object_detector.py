from __future__ import annotations

import io
import logging
from typing import Any

from inference_service.config import settings

logger = logging.getLogger(__name__)


class ObjectDetector:
    """Object detection using Grounding DINO.

    Accepts a text prompt and detects matching objects in the image.
    Currently a placeholder implementation pending Grounding DINO integration.
    Lazy-loads the model on first detection request.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._processor: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load the Grounding DINO model."""
        if self._loaded:
            return
        try:
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

            model_name = "IDEA-Research/grounding-dino-tiny"
            cache_dir = settings.model_cache_dir

            self._processor = AutoProcessor.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            self._model = AutoModelForZeroShotObjectDetection.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            self._model.to(settings.device)
            self._model.eval()
            self._loaded = True
            logger.info("Grounding DINO loaded on %s", settings.device)
        except ImportError:
            logger.warning(
                "transformers zero-shot detection not available; "
                "object detector running in placeholder mode"
            )
            self._model = None
            self._loaded = True
        except Exception:
            logger.exception("Failed to load Grounding DINO")
            self._model = None
            self._loaded = True

    def detect(self, image_bytes: bytes, prompt: str = "object") -> dict:
        """Detect objects matching a text prompt in an image.

        Args:
            image_bytes: Raw bytes of the image file.
            prompt: Text description of what to detect (e.g. "logo . barcode . text").

        Returns:
            Dictionary with detections list, each containing label, confidence,
            and bbox.
        """
        self.load()

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        detections: list[dict] = []

        if self._model is None or self._processor is None:
            return {"detections": detections, "prompt": prompt}

        try:
            import torch

            inputs = self._processor(images=image, text=prompt, return_tensors="pt")
            inputs = {k: v.to(settings.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)

            target_sizes = torch.tensor([image.size[::-1]]).to(settings.device)
            results = self._processor.post_process_grounded_object_detection(
                outputs,
                inputs["input_ids"],
                box_threshold=0.25,
                text_threshold=0.25,
                target_sizes=target_sizes,
            )

            if results:
                result = results[0]
                boxes = result["boxes"]
                scores = result["scores"]
                labels = result.get("labels", ["object"] * len(scores))

                for box, score, label in zip(boxes, scores, labels):
                    x1, y1, x2, y2 = box.tolist()
                    detections.append(
                        {
                            "label": label if isinstance(label, str) else str(label),
                            "confidence": round(score.item(), 4),
                            "bbox": {
                                "x1": round(x1, 1),
                                "y1": round(y1, 1),
                                "x2": round(x2, 1),
                                "y2": round(y2, 1),
                            },
                        }
                    )

        except Exception:
            logger.exception("Error during object detection")

        return {"detections": detections, "prompt": prompt}
