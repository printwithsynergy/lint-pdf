from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image

from inference_service.config import settings

logger = logging.getLogger(__name__)

# Known regulatory / packaging symbols and their text descriptions for CLIP matching
KNOWN_SYMBOLS = {
    "triman": "Triman recycling logo, three arrows in a circle with a human figure",
    "green_dot": "Green Dot symbol, two intertwined arrows forming a circle, one green one white",
    "how2recycle": "How2Recycle label with recycling instructions",
    "ce_mark": "CE marking, European conformity mark, letters C and E",
    "ukca": "UKCA mark, United Kingdom Conformity Assessed",
    "mobius_loop": "Mobius loop recycling symbol, three chasing arrows triangle",
    "recycling_arrows": "Recycling arrows symbol, chasing arrows in a triangle with number",
    "fsc": "FSC Forest Stewardship Council logo, tree checkmark",
    "tidyman": "Tidyman symbol, person disposing litter in bin",
    "ean_barcode": "EAN barcode, product barcode with vertical lines",
}


class SymbolDetector:
    """Regulatory symbol detection using CLIP-based template matching.

    Detects known packaging and regulatory symbols by comparing image crops
    against text descriptions using CLIP similarity.
    Lazy-loads the model on first detection request.
    """

    def __init__(self) -> None:
        self._clip_model: Any = None
        self._clip_preprocess: Any = None
        self._tokenizer: Any = None
        self._text_features: Any = None
        self._loaded = False

    def load(self) -> None:
        """Load the CLIP model and precompute text embeddings for known symbols."""
        if self._loaded:
            return
        try:
            import open_clip
            import torch

            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32",
                pretrained="laion2b_s34b_b79k",
                device=settings.device,
                cache_dir=settings.model_cache_dir,
            )
            tokenizer = open_clip.get_tokenizer("ViT-B-32")

            self._clip_model = model
            self._clip_preprocess = preprocess
            self._tokenizer = tokenizer

            # Precompute text features for all known symbols
            descriptions = list(KNOWN_SYMBOLS.values())
            text_tokens = tokenizer(descriptions).to(settings.device)
            with torch.no_grad():
                text_features = model.encode_text(text_tokens)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            self._text_features = text_features

            self._loaded = True
            logger.info("CLIP symbol detector loaded on %s", settings.device)
        except ImportError:
            logger.warning(
                "open_clip not installed; symbol detector running in placeholder mode"
            )
            self._clip_model = None
            self._loaded = True
        except Exception:
            logger.exception("Failed to load CLIP for symbol detection")
            self._clip_model = None
            self._loaded = True

    def detect(self, image_bytes: bytes) -> dict:
        """Detect regulatory symbols in an image.

        Uses a sliding window approach to scan the image and compares each
        crop against known symbol descriptions via CLIP similarity.

        Args:
            image_bytes: Raw bytes of the image file.

        Returns:
            Dictionary with symbols list, each containing type, confidence,
            bbox, and estimated size_mm.
        """
        self.load()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        symbols: list[dict] = []

        if self._clip_model is None:
            return {"symbols": symbols}

        try:
            import torch

            img_w, img_h = image.size
            symbol_names = list(KNOWN_SYMBOLS.keys())

            # Use a multi-scale sliding window approach
            window_sizes = [
                max(64, min(img_w, img_h) // 8),
                max(96, min(img_w, img_h) // 5),
                max(128, min(img_w, img_h) // 3),
            ]

            found_symbols: dict[str, dict] = {}

            for win_size in window_sizes:
                stride = win_size // 2
                for y in range(0, img_h - win_size + 1, stride):
                    for x in range(0, img_w - win_size + 1, stride):
                        crop = image.crop((x, y, x + win_size, y + win_size))
                        crop_tensor = (
                            self._clip_preprocess(crop).unsqueeze(0).to(settings.device)
                        )

                        with torch.no_grad():
                            image_features = self._clip_model.encode_image(crop_tensor)
                            image_features = image_features / image_features.norm(
                                dim=-1, keepdim=True
                            )
                            similarities = (image_features @ self._text_features.T)[0]

                        for idx, sim in enumerate(similarities):
                            sim_val = sim.item()
                            symbol_type = symbol_names[idx]

                            # Only keep high-confidence matches
                            if sim_val < 0.25:
                                continue

                            # Keep the best detection for each symbol type
                            if (
                                symbol_type not in found_symbols
                                or sim_val > found_symbols[symbol_type]["confidence"]
                            ):
                                # Estimate physical size assuming ~300 DPI for print
                                size_px = win_size
                                size_mm = round(size_px / 300.0 * 25.4, 1)

                                found_symbols[symbol_type] = {
                                    "type": symbol_type,
                                    "confidence": round(sim_val, 4),
                                    "bbox": {
                                        "x1": x,
                                        "y1": y,
                                        "x2": x + win_size,
                                        "y2": y + win_size,
                                    },
                                    "size_mm": size_mm,
                                }

            symbols = list(found_symbols.values())
            symbols.sort(key=lambda s: s["confidence"], reverse=True)

        except Exception:
            logger.exception("Error during symbol detection")

        return {"symbols": symbols}
