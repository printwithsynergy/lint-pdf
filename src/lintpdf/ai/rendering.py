"""Backwards-compat shim — page rendering moved to ``lintpdf.rendering``.

Phase 3c moved this module from ``lintpdf.ai.rendering`` to
``lintpdf.rendering`` because it's a pure CPU helper (pdf2image /
pikepdf / Pillow), not an AI-only utility. AI analyzers reach the
helpers through ``ctx.services.renderer`` (per the plugin protocol);
non-AI analyzers can import them directly from ``lintpdf.rendering``.

This shim re-exports every symbol the old module exposed so any
external caller still pointing at the old import path keeps working.
Phase 4 will delete the shim once the import path is confirmed dead.
"""

from __future__ import annotations

from lintpdf.rendering import (  # noqa: F401
    OCGError,
    _apply_ocg_overrides,
    _has_ghostscript,
    _render_page_via_ghostscript,
    get_page_count,
    render_all_pages,
    render_isolated_layer_tile,
    render_page_to_image,
)
