"""WS-15 — sample_densitometer must include spot inks, not just CMYK.

Pre-WS-15 the cache-hit fast path returned only the four CMYK
channels. A file with 9 spot colours (our Test3 DailyFiber_10up
fixture) would report `C 0% M 0% Y 0% B 0%` and TAC 0.0% even
though every drop of ink on the page lived in the spots.

These tests lock the contract: when the PDF carries spot
separations, the densitometer response must include one entry
per spot with a correct percent.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from siftpdf.reports.separation_renderer import (
    PROCESS_CHANNEL_ORDER,
    channel_cache_key,
    sample_densitometer,
)


@dataclass
class _FakeStorage:
    """Minimal StorageBackend double used only for cache hits."""

    blobs: dict[str, bytes]

    def download_raw(self, key: str) -> bytes | None:
        return self.blobs.get(key)

    def upload_raw(self, key: str, data: bytes, *, content_type: str = "") -> None:
        self.blobs[key] = data


def _solid_png_bytes(percent: float, width: int = 50, height: int = 50) -> bytes:
    """Produce a PNG that ``_pct_array_from_png_bytes`` decodes to a
    constant-percent raster of ``width x height``.

    The module reads a grayscale PNG where pixel intensity maps back
    to ink percentage (0 black = 0 %, 255 white = 100 %). We want a
    uniform ``percent`` reading, so emit a flat grayscale.
    """
    from io import BytesIO

    from PIL import Image

    # _pct_array_from_png_bytes computes percent = 100 - mean_gray/255*100
    # i.e. 0 intensity → 100 % ink; 255 intensity → 0 % ink.
    intensity = round(255.0 - percent / 100.0 * 255.0)
    img = Image.new("L", (width, height), intensity)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _fake_pdf_with_spots(spot_names: list[str]) -> bytes:
    """Return a sentinel bytes value; `list_separations` is patched in tests."""
    return b"%PDF-fake-" + b",".join(s.encode() for s in spot_names)


class TestDensitometerSpotsOnCacheHit:
    @staticmethod
    def test_spots_included_when_cache_fully_warm(monkeypatch: pytest.MonkeyPatch) -> None:
        spot_names = ["PANTONE 185 C", "PANTONE 485 C"]
        pdf_bytes = _fake_pdf_with_spots(spot_names)

        tenant = "tenant-x"
        job = "job-x"
        page = 1
        dpi = 300

        # Pre-populate the cache with CMYK + both spots at distinct
        # percentages so the assertion catches a swap / miss.
        blobs: dict[str, bytes] = {}
        cmyk_pcts = {"Cyan": 10.0, "Magenta": 25.0, "Yellow": 5.0, "Black": 40.0}
        for ch in PROCESS_CHANNEL_ORDER:
            blobs[channel_cache_key(tenant, job, page, dpi, ch)] = _solid_png_bytes(cmyk_pcts[ch])
        spot_pcts = {"PANTONE 185 C": 60.0, "PANTONE 485 C": 15.0}
        for spot, pct in spot_pcts.items():
            blobs[channel_cache_key(tenant, job, page, dpi, spot)] = _solid_png_bytes(pct)

        # Patch list_separations so the densitometer knows to look
        # for these spots without needing a real PDF.
        monkeypatch.setattr(
            "siftpdf.reports.separation_renderer.list_separations",
            lambda _pdf: [{"name": s, "type": "spot"} for s in spot_names],
        )

        storage = _FakeStorage(blobs=blobs)
        result = sample_densitometer(
            pdf_bytes,
            page,
            x=100.0,
            y=100.0,
            page_w=612.0,
            page_h=792.0,
            dpi=dpi,
            tenant_id=tenant,
            job_id=job,
            storage=storage,
        )

        channels = {c["name"]: c["percent"] for c in result["channels"]}
        assert set(channels) == {"Cyan", "Magenta", "Yellow", "Black", *spot_names}
        for ch, pct in cmyk_pcts.items():
            assert channels[ch] == pytest.approx(pct, abs=1.0)
        for spot, pct in spot_pcts.items():
            assert channels[spot] == pytest.approx(pct, abs=1.0)
        # TAC sums every ink including spots.
        assert result["tac"] == pytest.approx(
            sum(cmyk_pcts.values()) + sum(spot_pcts.values()), abs=2.0
        )

    @staticmethod
    def test_spot_cache_miss_falls_back_to_tiffsep(monkeypatch: pytest.MonkeyPatch) -> None:
        """If CMYK is cached but a spot is missing, the fast path must
        NOT silently drop the spot — the code should fall through to
        the tiffsep branch which re-renders everything."""
        spot_names = ["PANTONE 185 C"]
        pdf_bytes = _fake_pdf_with_spots(spot_names)
        tenant = "tenant-y"
        job = "job-y"
        page = 1
        dpi = 300

        # Cache only CMYK; spot is missing.
        blobs: dict[str, bytes] = {}
        for ch in PROCESS_CHANNEL_ORDER:
            blobs[channel_cache_key(tenant, job, page, dpi, ch)] = _solid_png_bytes(10.0)

        monkeypatch.setattr(
            "siftpdf.reports.separation_renderer.list_separations",
            lambda _pdf: [{"name": s, "type": "spot"} for s in spot_names],
        )

        # Flag so we can tell if _run_tiffsep was called.
        invoked = {"tiffsep": False}

        def fake_run_tiffsep(*args: object, **kwargs: object) -> str:
            invoked["tiffsep"] = True
            raise RuntimeError("stop-test-here")

        monkeypatch.setattr(
            "siftpdf.reports.separation_renderer._run_tiffsep",
            fake_run_tiffsep,
        )

        storage = _FakeStorage(blobs=blobs)
        with pytest.raises(RuntimeError, match="stop-test-here"):
            sample_densitometer(
                pdf_bytes,
                page,
                x=100.0,
                y=100.0,
                page_w=612.0,
                page_h=792.0,
                dpi=dpi,
                tenant_id=tenant,
                job_id=job,
                storage=storage,
            )
        assert invoked["tiffsep"], "Fell through silently — spot ink would be dropped"


class TestCmykOnlyFileSkipsSpotWork:
    @staticmethod
    def test_no_spots_means_cache_hit_returns_cmyk(monkeypatch: pytest.MonkeyPatch) -> None:
        """On a pure-CMYK file the fast path stays unchanged — no
        extra storage hits for spots that don't exist."""
        pdf_bytes = b"%PDF-fake-no-spots"
        tenant = "tenant-z"
        job = "job-z"
        page = 1
        dpi = 300

        blobs: dict[str, bytes] = {}
        for ch in PROCESS_CHANNEL_ORDER:
            blobs[channel_cache_key(tenant, job, page, dpi, ch)] = _solid_png_bytes(20.0)

        monkeypatch.setattr(
            "siftpdf.reports.separation_renderer.list_separations",
            lambda _pdf: [],
        )

        # Would crash if tiffsep ran.
        def must_not_run(*_a: object, **_k: object) -> None:
            raise AssertionError("tiffsep should not run on full cache hit")

        monkeypatch.setattr("siftpdf.reports.separation_renderer._run_tiffsep", must_not_run)

        storage = _FakeStorage(blobs=blobs)
        result = sample_densitometer(
            pdf_bytes,
            page,
            x=100.0,
            y=100.0,
            page_w=612.0,
            page_h=792.0,
            dpi=dpi,
            tenant_id=tenant,
            job_id=job,
            storage=storage,
        )

        names = [c["name"] for c in result["channels"]]
        assert names == PROCESS_CHANNEL_ORDER

        # Silence ``np`` unused-import warning on Python 3.12 lint pass.
        _ = np.array([0])
