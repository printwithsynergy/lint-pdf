"""Text-region capability — wraps the GPU inference detect_outlines call.

The OCR-text-region pre-pass currently lives as a method on the GPU
inference client (no standalone module). This provider exposes it via
the ``TextRegionProvider`` Protocol and caches per-(page, dpi).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lintpdf.plugin.services import GPUClient


@dataclass
class GPUTextRegionProvider:
    """``TextRegionProvider`` impl backed by ``GPUClient.detect_outlines``."""

    gpu_client: GPUClient | None
    pdf_bytes: bytes
    _cache: dict[tuple[int, int], list[dict[str, Any]]] = field(default_factory=dict, init=False)

    def get_text_regions(self, *, page_num: int, dpi: int) -> list[dict[str, Any]]:
        if self.gpu_client is None:
            raise RuntimeError(
                "text_regions capability requested but GPU client is unavailable on this host"
            )
        key = (page_num, dpi)
        if key not in self._cache:
            self._cache[key] = self.gpu_client.detect_outlines(
                pdf_bytes=self.pdf_bytes, page_num=page_num, dpi=dpi
            )
        return self._cache[key]
