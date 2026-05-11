"""Unit tests for the OCG cache-suffix helper in the viewer route module.

The ``_apply_ocg_overrides`` tests this file used to carry targeted
a private helper that lived in ``lintpdf.rendering`` before page
rendering moved to ``codex-pdf``. OCG override application now
happens inside codex's render service; the cache-suffix helper
stays in lint-pdf because it shapes the viewer-side S3 key.
"""

from __future__ import annotations

from lintpdf.api.routes.viewer import _ocg_cache_suffix


def test_cache_suffix_empty_for_default_state():
    assert _ocg_cache_suffix(None, None) == ""
    assert _ocg_cache_suffix([], []) == ""
    assert _ocg_cache_suffix(None, []) == ""


def test_cache_suffix_non_empty_for_overrides():
    s = _ocg_cache_suffix([0, 3], [2])
    assert s.startswith("_ocg-")
    assert len(s) == len("_ocg-") + 12  # 12-hex prefix


def test_cache_suffix_is_order_independent():
    a = _ocg_cache_suffix([3, 1], [2])
    b = _ocg_cache_suffix([1, 3], [2])
    assert a == b


def test_cache_suffix_differs_when_masks_differ():
    a = _ocg_cache_suffix([0], [])
    b = _ocg_cache_suffix([], [0])
    assert a != b

    c = _ocg_cache_suffix([0, 1], [])
    d = _ocg_cache_suffix([0, 2], [])
    assert c != d
