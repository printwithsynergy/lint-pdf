"""Capability providers — pull-based cross-cutting work.

Page rendering, text-region detection, and content-stream event
re-parsing are all things multiple plugins want at the same DPI / page
combination. The orchestrator runs the underlying work once and shares
the result across consumer plugins via these provider objects, which
implement the Protocols defined in ``siftpdf.plugin.protocol``.

Phase 1 wraps the existing concrete entry points (``ai.rendering``,
``ai.gpu_client.detect_outlines``) into providers that satisfy the
Protocols. Phase 2 will inline result caching here so the orchestrator
no longer needs an external memoization layer.
"""

from siftpdf.plugin.capabilities.page_rendering import RendererBackedPageImageProvider
from siftpdf.plugin.capabilities.text_regions import GPUTextRegionProvider

__all__ = [
    "GPUTextRegionProvider",
    "RendererBackedPageImageProvider",
]
