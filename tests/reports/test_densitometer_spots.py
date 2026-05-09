"""WS-15 — sample_densitometer must include spot inks, not just CMYK.

Pre-WS-15 the cache-hit fast path returned only the four CMYK
channels. A file with 9 spot colours (our Test3 DailyFiber_10up
fixture) would report `C 0% M 0% Y 0% B 0%` and TAC 0.0% even
though every drop of ink on the page lived in the spots.

These tests lock the contract: when the PDF carries spot
separations, the densitometer response must include one entry
per spot with a correct percent.

After the codex-backed refactor, ``sample_densitometer`` delegates to
``_codex_sample_density`` (the codex render client) rather than the old
in-process tiffsep + storage-cache pipeline. Tests monkeypatch at the
codex boundary instead of the removed ``_run_tiffsep`` hook.
"""

from __future__ import annotations

import pytest

from lintpdf.reports.separation_renderer import (
    PROCESS_CHANNEL_ORDER,
    sample_densitometer,
)


def _fake_codex_response(
    channel_pcts: dict[str, float],
    *,
    tac_limit: float = 300.0,
) -> dict[str, object]:
    """Build a minimal codex sample_density response dict."""
    channels = [{"name": k, "percent": v} for k, v in channel_pcts.items()]
    tac = sum(channel_pcts.values())
    return {
        "x": 100.0,
        "y": 100.0,
        "dpi": 300,
        "channels": channels,
        "tac": tac,
        "tac_limit": tac_limit,
        "limit_exceeded": tac > tac_limit,
    }


class TestDensitometerSpotsOnCacheHit:
    @staticmethod
    def test_spots_included_when_codex_returns_spots(monkeypatch: pytest.MonkeyPatch) -> None:
        """Spot channels from the codex response are passed through unchanged."""
        spot_names = ["PANTONE 185 C", "PANTONE 485 C"]
        cmyk_pcts = {"Cyan": 10.0, "Magenta": 25.0, "Yellow": 5.0, "Black": 40.0}
        spot_pcts = {"PANTONE 185 C": 60.0, "PANTONE 485 C": 15.0}
        all_pcts = {**cmyk_pcts, **spot_pcts}

        monkeypatch.setattr(
            "lintpdf.reports.separation_renderer._codex_sample_density",
            lambda *_a, **_kw: _fake_codex_response(all_pcts),
        )

        result = sample_densitometer(
            b"%PDF-fake",
            1,
            x=100.0,
            y=100.0,
            page_w=612.0,
            page_h=792.0,
            dpi=300,
        )

        channels = {c["name"]: c["percent"] for c in result["channels"]}
        assert set(channels) == {"Cyan", "Magenta", "Yellow", "Black", *spot_names}
        for ch, pct in cmyk_pcts.items():
            assert channels[ch] == pytest.approx(pct, abs=1.0)
        for spot, pct in spot_pcts.items():
            assert channels[spot] == pytest.approx(pct, abs=1.0)
        assert result["tac"] == pytest.approx(sum(all_pcts.values()), abs=2.0)

    @staticmethod
    def test_spot_channels_not_silently_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
        """Codex response with spots must not be truncated to CMYK-only."""
        all_pcts = {
            "Cyan": 10.0,
            "Magenta": 10.0,
            "Yellow": 10.0,
            "Black": 10.0,
            "PANTONE 185 C": 60.0,
        }

        monkeypatch.setattr(
            "lintpdf.reports.separation_renderer._codex_sample_density",
            lambda *_a, **_kw: _fake_codex_response(all_pcts),
        )

        result = sample_densitometer(
            b"%PDF-fake",
            1,
            x=100.0,
            y=100.0,
            page_w=612.0,
            page_h=792.0,
            dpi=300,
        )

        names = {c["name"] for c in result["channels"]}
        assert "PANTONE 185 C" in names, "Spot ink channel was silently dropped"


class TestCmykOnlyFileSkipsSpotWork:
    @staticmethod
    def test_no_spots_means_cmyk_only_channels(monkeypatch: pytest.MonkeyPatch) -> None:
        """On a pure-CMYK file the response contains exactly the four process channels."""
        cmyk_pcts = {"Cyan": 20.0, "Magenta": 20.0, "Yellow": 20.0, "Black": 20.0}

        monkeypatch.setattr(
            "lintpdf.reports.separation_renderer._codex_sample_density",
            lambda *_a, **_kw: _fake_codex_response(cmyk_pcts),
        )

        result = sample_densitometer(
            b"%PDF-fake-no-spots",
            1,
            x=100.0,
            y=100.0,
            page_w=612.0,
            page_h=792.0,
            dpi=300,
        )

        names = [c["name"] for c in result["channels"]]
        assert names == PROCESS_CHANNEL_ORDER
