"""Registry discovery tests — entry points + legacy fallback."""

from __future__ import annotations

from siftpdf.plugin import discover_entry_points, discover_legacy_ai


def test_entry_point_discovery_returns_list():
    # No third-party plugins installed in the test env; the call must
    # still return a list (possibly empty), never raise.
    result = discover_entry_points()
    assert isinstance(result, list)


def test_legacy_ai_discovery_returns_list():
    # Even when the legacy AI registry is present, discovery must
    # return a list of adapter instances.
    result = discover_legacy_ai()
    assert isinstance(result, list)
    # Every item exposes the new Plugin Protocol surface.
    for plugin in result[:5]:  # spot-check first 5 — registry is large
        assert hasattr(plugin, "manifest")
        assert hasattr(plugin, "analyze_v2")
        assert plugin.manifest.id.startswith("siftpdf.legacy.")
