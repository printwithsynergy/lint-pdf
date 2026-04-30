"""Page-rendering capability — wraps the SaaS Renderer service.

Provides ``PageImageProvider`` semantics over a ``Services.renderer``.
Multiple consumer plugins request the same page+DPI; this provider
caches per-(page, dpi) so the underlying ``render_page`` runs once.

Phase 1: simple in-memory cache keyed by ``(page_num, dpi)``. Phase 2
introduces a process-wide cache so the cost is shared across orchestrator
calls within a single job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siftpdf.plugin.services import Renderer


@dataclass
class RendererBackedPageImageProvider:
    """``PageImageProvider`` impl that defers to a ``Renderer`` service.

    The provider is constructed per-job so the cache lifetime matches
    the orchestrator's preflight run.
    """

    renderer: Renderer | None
    pdf_bytes: bytes
    _cache: dict[tuple[int, int], bytes] = field(default_factory=dict, init=False)

    def get_page_image(self, *, page_num: int, dpi: int) -> bytes:
        """Return PNG/JPEG bytes for ``page_num`` at ``dpi``.

        Raises ``RuntimeError`` if the renderer service is unavailable —
        callers that listed ``page_images`` in their manifest's
        ``requires_capabilities`` should self-skip on this error rather
        than letting it propagate.
        """

        if self.renderer is None:
            raise RuntimeError(
                "page_images capability requested but renderer service is unavailable on this host"
            )
        key = (page_num, dpi)
        if key not in self._cache:
            self._cache[key] = self.renderer.render_page(
                pdf_bytes=self.pdf_bytes, page_num=page_num, dpi=dpi
            )
        return self._cache[key]
