from __future__ import annotations

import io
import logging
from typing import Any

from inference_service.config import settings

logger = logging.getLogger(__name__)


class ImageEmbedder:
    """Image embedding using DINOv2 via HuggingFace transformers.

    Lazy-loads the model on first embedding request.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._processor: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load the DINOv2 model."""
        if self._loaded:
            return
        try:
            from transformers import AutoImageProcessor, AutoModel

            model_name = "facebook/dinov2-base"
            cache_dir = settings.model_cache_dir

            self._processor = AutoImageProcessor.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            self._model = AutoModel.from_pretrained(model_name, cache_dir=cache_dir)
            self._model.to(settings.device)
            self._model.eval()
            self._loaded = True
            logger.info("DINOv2 embedder loaded on %s", settings.device)
        except ImportError:
            logger.warning(
                "transformers not installed; embedder running in placeholder mode"
            )
            self._model = None
            self._loaded = True
        except Exception:
            logger.exception("Failed to load DINOv2")
            self._model = None
            self._loaded = True

    def embed(self, image_bytes: bytes) -> dict:
        """Generate an embedding vector for an image.

        Args:
            image_bytes: Raw bytes of the image file.

        Returns:
            Dictionary with embedding (list of floats) and dimension.
        """
        self.load()

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        if self._model is None or self._processor is None:
            # Return a zero placeholder embedding
            dim = 768
            return {
                "embedding": [0.0] * dim,
                "dimension": dim,
            }

        try:
            import torch

            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {k: v.to(settings.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)

            # Use the CLS token embedding
            cls_embedding = outputs.last_hidden_state[:, 0, :]
            # L2 normalize
            cls_embedding = cls_embedding / cls_embedding.norm(dim=-1, keepdim=True)

            embedding_list = cls_embedding[0].cpu().numpy().tolist()
            return {
                "embedding": embedding_list,
                "dimension": len(embedding_list),
            }

        except Exception:
            logger.exception("Error during image embedding")
            dim = 768
            return {
                "embedding": [0.0] * dim,
                "dimension": dim,
            }
