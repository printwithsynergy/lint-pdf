"""Unit tests for the codex_signals ImageResolutionAnalyzer.

The analyzer reads ``effective_resolution_dpi`` (and ``placed_width_pts`` /
``width_px``) from ``ctx.config["codex_payload"]["images"]`` and emits:

- LPDF_IMG_001 — effective DPI below minimum (error if <100, warning if <150)
- LPDF_IMG_006 — image upscaled >200%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from lintpdf.ai.analyzers.codex_signals.image_resolution import ImageResolutionAnalyzer
from lintpdf.analyzers.finding import Severity


@dataclass
class _FakeCtx:
    config: dict[str, Any] = field(default_factory=dict)
    document: Any = None
    events: list[Any] = field(default_factory=list)
    pdf_bytes: bytes = b""
    tenant_id: str | None = None
    services: Any = None
    capabilities: Any = None


def _payload(images: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_version": "1.17.0", "images": images}


def _image(
    *,
    image_id: str = "img1",
    page_num: int = 1,
    width_px: int = 1000,
    height_px: int = 800,
    x_dpi: float | None = None,
    y_dpi: float | None = None,
    placed_width_pts: float | None = None,
    placed_height_pts: float | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "image_id": image_id,
        "page_num": page_num,
        "width_px": width_px,
        "height_px": height_px,
    }
    if x_dpi is not None and y_dpi is not None:
        entry["effective_resolution_dpi"] = {"x_dpi": x_dpi, "y_dpi": y_dpi}
    if placed_width_pts is not None:
        entry["placed_width_pts"] = placed_width_pts
    if placed_height_pts is not None:
        entry["placed_height_pts"] = placed_height_pts
    return entry


# ---------------------------------------------------------------------------
# LPDF_IMG_001 — low DPI
# ---------------------------------------------------------------------------


def test_low_dpi_72_emits_error() -> None:
    """Image at 72 DPI is below 100 → LPDF_IMG_001 with ERROR severity."""
    ctx = _FakeCtx(config={"codex_payload": _payload([_image(x_dpi=72.0, y_dpi=72.0)])})
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert len(findings) == 1
    f = findings[0]
    assert f.inspection_id == "LPDF_IMG_001"
    assert f.severity == Severity.ERROR
    assert "72" in f.message
    assert f.details["dpi_effective"] == pytest.approx(72.0)
    assert f.details["source"] == "codex"


def test_dpi_200_no_finding() -> None:
    """Image at 200 DPI is above the 150 DPI minimum → no finding."""
    ctx = _FakeCtx(config={"codex_payload": _payload([_image(x_dpi=200.0, y_dpi=200.0)])})
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert findings == []


def test_dpi_120_emits_warning() -> None:
    """Image at 120 DPI is below 150 but above 100 → LPDF_IMG_001 WARNING."""
    ctx = _FakeCtx(config={"codex_payload": _payload([_image(x_dpi=120.0, y_dpi=130.0)])})
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert len(findings) == 1
    f = findings[0]
    assert f.inspection_id == "LPDF_IMG_001"
    assert f.severity == Severity.WARNING
    # effective = min(120, 130) = 120
    assert f.details["dpi_effective"] == pytest.approx(120.0)


def test_effective_resolution_none_no_finding() -> None:
    """Image with no effective_resolution_dpi field → graceful skip, no finding."""
    ctx = _FakeCtx(
        config={
            "codex_payload": _payload(
                [_image()]  # no x_dpi / y_dpi → field absent
            )
        }
    )
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert findings == []


# ---------------------------------------------------------------------------
# LPDF_IMG_006 — upscaled >200%
# ---------------------------------------------------------------------------


def test_upscaled_image_emits_lpdf_img_006() -> None:
    """Image placed at 400% (placed_width >> pixel width) → LPDF_IMG_006."""
    # 100 px image placed at 400 pts → 400% upscale
    ctx = _FakeCtx(
        config={"codex_payload": _payload([_image(width_px=100, placed_width_pts=400.0)])}
    )
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    upscale_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_006"]
    assert len(upscale_findings) == 1
    f = upscale_findings[0]
    assert f.severity == Severity.WARNING
    assert f.details["upscale_percent"] == pytest.approx(400.0)


def test_not_upscaled_no_lpdf_img_006() -> None:
    """Image placed at 150% is below the 200% threshold → no LPDF_IMG_006."""
    # 100 px image placed at 150 pts → 150% scale
    ctx = _FakeCtx(
        config={"codex_payload": _payload([_image(width_px=100, placed_width_pts=150.0)])}
    )
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert not any(f.inspection_id == "LPDF_IMG_006" for f in findings)


# ---------------------------------------------------------------------------
# Empty / missing payload
# ---------------------------------------------------------------------------


def test_no_images_in_payload_returns_empty() -> None:
    """Payload with no 'images' key → empty list."""
    ctx = _FakeCtx(config={"codex_payload": {"schema_version": "1.17.0"}})
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert findings == []


def test_empty_images_list_returns_empty() -> None:
    """Payload with empty images list → empty list."""
    ctx = _FakeCtx(config={"codex_payload": _payload([])})
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert findings == []


def test_missing_codex_payload_returns_empty() -> None:
    """No codex_payload key in config → short-circuit, empty list."""
    ctx = _FakeCtx(config={})
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert findings == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_uses_min_of_x_and_y_dpi() -> None:
    """Effective DPI = min(x_dpi, y_dpi); y axis drives the violation."""
    # x is fine (300), y is low (80) → error
    ctx = _FakeCtx(config={"codex_payload": _payload([_image(x_dpi=300.0, y_dpi=80.0)])})
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].details["dpi_effective"] == pytest.approx(80.0)
    assert findings[0].severity == Severity.ERROR


def test_custom_min_dpi_via_config() -> None:
    """Tenant can override min_dpi via ctx.config['image_resolution']['min_dpi']."""
    # Image at 200 DPI; default min is 150 → no finding.
    # Custom min = 250 → should flag.
    ctx = _FakeCtx(
        config={
            "codex_payload": _payload([_image(x_dpi=200.0, y_dpi=200.0)]),
            "image_resolution": {"min_dpi": 250.0},
        }
    )
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_IMG_001"


def test_finding_metadata() -> None:
    """Findings carry source='codex', object_type='image', correct page_num."""
    ctx = _FakeCtx(
        config={
            "codex_payload": _payload(
                [_image(image_id="logo_jpg", page_num=3, x_dpi=50.0, y_dpi=50.0)]
            )
        }
    )
    findings = ImageResolutionAnalyzer().analyze_v2(ctx)
    assert len(findings) == 1
    f = findings[0]
    assert f.page_num == 3
    assert f.object_id == "logo_jpg"
    assert f.object_type == "image"
    assert f.details["source"] == "codex"
    assert f.source == "ai"  # set by BaseAIAnalyzer._make_finding
