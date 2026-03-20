from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np
from PIL import Image

from inference_service.config import settings

logger = logging.getLogger(__name__)


class LogoDetector:
    """Logo detection using YOLOv8 for region proposals and OpenCLIP for embeddings.

    Lazy-loads models on first detection request.
    """

    def __init__(self) -> None:
        self._yolo_model: Any = None
        self._clip_model: Any = None
        self._clip_preprocess: Any = None
        self._tokenizer: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load YOLOv8 and OpenCLIP models."""
        if self._loaded:
            return

        # Load YOLOv8
        try:
            from ultralytics import YOLO

            self._yolo_model = YOLO("yolov8n.pt")
            logger.info("YOLOv8 model loaded")
        except ImportError:
            logger.warning("ultralytics not installed; YOLOv8 unavailable")
            self._yolo_model = None
        except Exception:
            logger.exception("Failed to load YOLOv8")
            self._yolo_model = None

        # Load OpenCLIP
        try:
            import open_clip

            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32",
                pretrained="laion2b_s34b_b79k",
                device=settings.device,
                cache_dir=settings.model_cache_dir,
            )
            self._clip_model = model
            self._clip_preprocess = preprocess
            self._tokenizer = open_clip.get_tokenizer("ViT-B-32")
            logger.info("OpenCLIP model loaded on %s", settings.device)
        except ImportError:
            logger.warning("open_clip not installed; CLIP embedding unavailable")
            self._clip_model = None
        except Exception:
            logger.exception("Failed to load OpenCLIP")
            self._clip_model = None

        self._loaded = True

    def detect(
        self,
        image_bytes: bytes,
        reference_embeddings: list[list[float]] | None = None,
    ) -> dict:
        """Detect logos in an image.

        Args:
            image_bytes: Raw bytes of the image file.
            reference_embeddings: Optional list of reference CLIP embeddings to
                compare detected regions against.

        Returns:
            Dictionary with detections list, each containing bbox, confidence,
            clip_embedding, and optional match_score.
        """
        self.load()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        detections: list[dict] = []

        if self._yolo_model is None:
            return {"detections": detections}

        try:
            import torch

            results = self._yolo_model(image, verbose=False)

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for _i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    confidence = box.conf[0].item()

                    # Only consider detections with reasonable confidence
                    if confidence < 0.3:
                        continue

                    detection: dict[str, Any] = {
                        "bbox": {
                            "x1": round(x1, 1),
                            "y1": round(y1, 1),
                            "x2": round(x2, 1),
                            "y2": round(y2, 1),
                        },
                        "confidence": round(confidence, 4),
                        "clip_embedding": None,
                        "match_score": None,
                    }

                    # Generate CLIP embedding for the cropped region
                    if (
                        self._clip_model is not None
                        and self._clip_preprocess is not None
                    ):
                        try:
                            crop = image.crop((int(x1), int(y1), int(x2), int(y2)))
                            crop_tensor = (
                                self._clip_preprocess(crop)
                                .unsqueeze(0)
                                .to(settings.device)
                            )
                            with torch.no_grad():
                                embedding = self._clip_model.encode_image(crop_tensor)
                                embedding = embedding / embedding.norm(
                                    dim=-1, keepdim=True
                                )
                            emb_list = embedding[0].cpu().numpy().tolist()
                            detection["clip_embedding"] = emb_list

                            # Compare against reference embeddings
                            if reference_embeddings:
                                best_score = 0.0
                                emb_np = np.array(emb_list)
                                for ref in reference_embeddings:
                                    ref_np = np.array(ref)
                                    cosine_sim = float(
                                        np.dot(emb_np, ref_np)
                                        / (
                                            np.linalg.norm(emb_np)
                                            * np.linalg.norm(ref_np)
                                            + 1e-8
                                        )
                                    )
                                    best_score = max(best_score, cosine_sim)
                                detection["match_score"] = round(best_score, 4)
                        except Exception:
                            logger.exception("Failed to compute CLIP embedding")

                    detections.append(detection)

        except Exception:
            logger.exception("Error during logo detection")

        return {"detections": detections}
