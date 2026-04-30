"""Plugin manifest unit tests."""

from __future__ import annotations

import pytest

from siftpdf.plugin import PluginManifest, Tier


def test_manifest_minimal_construction():
    m = PluginManifest(id="siftpdf.test.simple", version="1.0.0", tier=Tier.CPU)
    assert m.id == "siftpdf.test.simple"
    assert m.version == "1.0.0"
    assert m.tier is Tier.CPU
    assert m.requires_capabilities == ()
    assert m.requires_services == ()
    assert m.declared_check_ids == ()
    assert m.config_schema is None


def test_manifest_full_construction():
    m = PluginManifest(
        id="siftpdf.barcode.qr",
        version="2.3.1",
        tier=Tier.GPU,
        requires_capabilities=("page_images", "text_regions"),
        requires_services=("metering", "cost_cap"),
        declared_check_ids=("LPDF_BARCODE_001", "LPDF_BARCODE_002"),
        config_schema={"type": "object"},
    )
    assert m.tier is Tier.GPU
    assert "page_images" in m.requires_capabilities
    assert "LPDF_BARCODE_001" in m.declared_check_ids
    assert m.config_schema == {"type": "object"}


def test_manifest_is_frozen():
    m = PluginManifest(id="x", version="0.1.0", tier=Tier.CPU)
    with pytest.raises((AttributeError, Exception)):
        m.id = "y"  # type: ignore[misc]


def test_tier_values():
    assert Tier.CPU.value == "cpu"
    assert Tier.GPU.value == "gpu"
    assert Tier.EXTERNAL_AI.value == "external_ai"
