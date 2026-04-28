"""Unit tests for the overprint-aware renderer + tile cache versioning.

Context — the 2026-04-22 Amalgam_Catalyst regression: the Amalgam wine
label uses 9 spot colors with overprint active, and the previous
pdftoppm-backed preview rendered the entire page as a single tint
(because pdftoppm ignores overprint in RGB mode). ``render_page_to_image``
was switched to route through Ghostscript with
``-dSimulateOverprint=true`` whenever ``gs`` is on PATH, while keeping
the pdftoppm path as a graceful fallback for dev environments without
GS.

These tests exercise the selection logic + cache-key versioning without
actually shelling out to Ghostscript (that would need a full GS install
in CI). The GS-enabled code path itself is small (the subprocess call)
and covered by the integration probe on prod.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from lintpdf.ai import rendering
from lintpdf.ai.rendering import render_page_to_image
from lintpdf.api.routes.viewer import _TILE_RENDER_VERSION, _tile_cache_key

if TYPE_CHECKING:
    import pytest


class TestRendererSelection:
    """``simulate_overprint=True`` + GS present → Ghostscript wins."""

    @staticmethod
    def test_gs_path_used_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(rendering, "_gs_checked", True)
        monkeypatch.setattr(rendering, "_has_gs", True)

        gs_mock = MagicMock(return_value=b"PNG-from-gs")
        poppler_mock = MagicMock()

        monkeypatch.setattr(rendering, "_render_page_via_ghostscript", gs_mock)
        monkeypatch.setattr(rendering, "_HAS_PDF2IMAGE", True)
        monkeypatch.setattr(rendering, "_convert_from_bytes", poppler_mock)

        out = render_page_to_image(b"%PDF-fake", page_num=1, dpi=150)
        assert out == b"PNG-from-gs"
        gs_mock.assert_called_once_with(b"%PDF-fake", 1, 150)
        poppler_mock.assert_not_called()

    @staticmethod
    def test_falls_back_to_poppler_when_gs_missing(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(rendering, "_gs_checked", True)
        monkeypatch.setattr(rendering, "_has_gs", False)

        gs_mock = MagicMock()
        fake_img = MagicMock()
        fake_img.save = MagicMock(
            side_effect=lambda buf, format: buf.write(b"PNG-from-poppler"),
        )

        monkeypatch.setattr(rendering, "_render_page_via_ghostscript", gs_mock)
        monkeypatch.setattr(rendering, "_HAS_PDF2IMAGE", True)
        monkeypatch.setattr(rendering, "_convert_from_bytes", MagicMock(return_value=[fake_img]))

        out = render_page_to_image(b"%PDF-fake", page_num=1, dpi=150)
        assert out == b"PNG-from-poppler"
        gs_mock.assert_not_called()

    @staticmethod
    def test_gs_failure_falls_through_to_poppler(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A transient GS hiccup must not 500 the viewer — it falls through."""
        monkeypatch.setattr(rendering, "_gs_checked", True)
        monkeypatch.setattr(rendering, "_has_gs", True)

        gs_mock = MagicMock(side_effect=RuntimeError("gs crashed"))
        fake_img = MagicMock()
        fake_img.save = MagicMock(
            side_effect=lambda buf, format: buf.write(b"PNG-poppler-fallback"),
        )
        poppler_mock = MagicMock(return_value=[fake_img])

        monkeypatch.setattr(rendering, "_render_page_via_ghostscript", gs_mock)
        monkeypatch.setattr(rendering, "_HAS_PDF2IMAGE", True)
        monkeypatch.setattr(rendering, "_convert_from_bytes", poppler_mock)

        out = render_page_to_image(b"%PDF-fake", page_num=1, dpi=150)
        assert out == b"PNG-poppler-fallback"
        gs_mock.assert_called_once()
        poppler_mock.assert_called_once()

    @staticmethod
    def test_simulate_overprint_false_forces_poppler(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Callers can opt out of GS (e.g. speed-over-correctness)."""
        monkeypatch.setattr(rendering, "_gs_checked", True)
        monkeypatch.setattr(rendering, "_has_gs", True)

        gs_mock = MagicMock()
        fake_img = MagicMock()
        fake_img.save = MagicMock(
            side_effect=lambda buf, format: buf.write(b"PNG-from-poppler"),
        )

        monkeypatch.setattr(rendering, "_render_page_via_ghostscript", gs_mock)
        monkeypatch.setattr(rendering, "_HAS_PDF2IMAGE", True)
        monkeypatch.setattr(rendering, "_convert_from_bytes", MagicMock(return_value=[fake_img]))

        render_page_to_image(b"%PDF-fake", page_num=1, dpi=150, simulate_overprint=False)
        gs_mock.assert_not_called()


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
