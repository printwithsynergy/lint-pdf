"""Unit tests for tile cache key versioning.

The overprint-aware GS/poppler renderer selection tests that previously
lived here were removed when ``render_page_to_image`` was migrated to
route through codex (which handles Ghostscript overprint simulation
internally). The cache-key tests remain — they guard against silent
stale-tile regressions when render semantics change.
"""

from __future__ import annotations

from lintpdf.api.routes.viewer import _TILE_RENDER_VERSION, _tile_cache_key


class TestTileCacheKeyVersion:
    """The tile cache key must include the render-version token.

    Otherwise a deploy that changes renderer semantics would silently
    serve stale tiles cached against the old pipeline — exactly what
    happened when the Amalgam tiles were pre-warmed with pdftoppm and
    then survived the switch to GS.
    """

    @staticmethod
    def test_key_includes_render_version() -> None:
        key = _tile_cache_key("tenant-1", "job-1", 1, 150)
        assert f"_rv{_TILE_RENDER_VERSION}" in key
        assert key == (f"tenant-1/job-1/tiles/p1_d150_rv{_TILE_RENDER_VERSION}.png")

    @staticmethod
    def test_key_versioning_buckets_ocg_override_separately() -> None:
        base = _tile_cache_key("t", "j", 1, 150)
        with_ocg = _tile_cache_key("t", "j", 1, 150, ocg_on=[0, 1])
        assert base != with_ocg
        assert f"_rv{_TILE_RENDER_VERSION}" in with_ocg
        assert "_ocg-" in with_ocg

    @staticmethod
    def test_queue_and_route_agree_on_key() -> None:
        """The warm-task key builder must match the read-path key builder."""
        from lintpdf.queue.tasks import _tile_s3_key

        warm_key = _tile_s3_key("tenant-x", "job-x", 3, 300)
        read_key = _tile_cache_key("tenant-x", "job-x", 3, 300)
        assert warm_key == read_key
