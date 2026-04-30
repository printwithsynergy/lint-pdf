"""Services protocol + no-op stub tests."""

from __future__ import annotations

from siftpdf.plugin import (
    noop_cost_cap,
    noop_metering,
    noop_tenants,
    noop_verapdf,
)


def test_noop_metering_returns_none():
    metering = noop_metering()
    assert metering.record_usage(tenant_id="t1", feature_slug="x", units=1, metadata={}) is None


def test_noop_cost_cap_does_not_raise():
    cap = noop_cost_cap()
    # No raise == allowed.
    cap.check_or_raise(tenant_id="t1", feature_slug="x", estimated_units=10)


def test_noop_verapdf_reports_unconfigured_and_advisory_skip():
    verapdf = noop_verapdf()
    assert verapdf.is_configured() is False
    result = verapdf.validate(pdf_bytes=b"%PDF-1.4", profile="pdfa-1b")
    assert result["status"] == "skipped"
    assert "veraPDF" in result["advisory"]


def test_noop_tenants_returns_empty():
    tenants = noop_tenants()
    assert tenants.get_ai_config("t1") is None
    assert tenants.get_entitlements("t1") == {}
