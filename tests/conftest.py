"""Shared test fixtures for LintPDF test suite."""

from pathlib import Path

import pytest

# Audit-fix #3c (catalog item #3) -- the OSS engine no longer ships
# SaaS plan-tier baselines (``PLAN_LIMITS`` moved to
# ``lintpdf_saas.tenants.entitlement_defaults``). The OSS default
# ``EntitlementDefaultsService`` returns a permissive everything-
# enabled bag regardless of plan; OSS tests that assert SaaS-tier
# semantics (Viewer blocks ``engine`` source, Scale grants
# packaging-stack AI features but not similarity, etc.) need a
# tier-aware stub installed for the test session. Mirrors what
# ``SaaSEntitlementDefaultsService`` does in production SaaS.
_ALL_PREFLIGHT_SOURCES = ["engine", "external", "minimal"]
_AI_FEATURES_GROWTH = ["audit"]
_AI_FEATURES_SCALE = ["audit", "ocr", "dieline", "art_size", "legend"]
_AI_FEATURES_ENTERPRISE = [*_AI_FEATURES_SCALE, "similarity", "sonnet_fallback"]
_PLAN_LIMITS_TEST: dict[str, dict] = {
    "free": {
        "rate_limit_daily": 50,
        "max_file_size_mb": 25,
        "max_custom_profiles": 1,
        "overage_rate_cents": 0,
        "report_storage_mb": 100,
        "report_default_expiry_days": 7,
        "allowed_report_formats": ["json", "html"],
        "allowed_preflight_sources": _ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": False,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": False,
        "max_webhooks": 0,
        "approval_chains_enabled": False,
        "max_approval_templates": 0,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 0,
        "monthly_files_included": 50,
        "ai_features": [],
    },
    "viewer": {
        "rate_limit_daily": 150,
        "max_file_size_mb": 250,
        "max_custom_profiles": 0,
        "overage_rate_cents": 5,
        "report_storage_mb": 2048,
        "report_default_expiry_days": 30,
        "allowed_report_formats": [],
        "allowed_preflight_sources": ["minimal", "external"],
        "capability_fillin_enabled": False,
        "annotations_enabled": False,
        "webhooks_enabled": False,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": False,
        "max_webhooks": 0,
        "approval_chains_enabled": False,
        "max_approval_templates": 0,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 0,
        "monthly_files_included": 50,
        "ai_features": [],
    },
    "starter": {
        "rate_limit_daily": 500,
        "max_file_size_mb": 250,
        "max_custom_profiles": 10,
        "overage_rate_cents": 10,
        "report_storage_mb": 5120,
        "report_default_expiry_days": 30,
        "allowed_report_formats": ["json", "html", "pdf", "xml"],
        "allowed_preflight_sources": _ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": False,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": False,
        "max_webhooks": 0,
        "approval_chains_enabled": False,
        "max_approval_templates": 0,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 0,
        "monthly_files_included": 500,
        "ai_features": [],
    },
    "growth": {
        "rate_limit_daily": 5000,
        "max_file_size_mb": 500,
        "max_custom_profiles": 25,
        "overage_rate_cents": 10,
        "report_storage_mb": 25600,
        "report_default_expiry_days": 90,
        "allowed_report_formats": ["json", "html", "pdf", "xml"],
        "allowed_preflight_sources": _ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": True,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": True,
        "max_webhooks": 5,
        "approval_chains_enabled": True,
        "max_approval_templates": 3,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 500,
        "monthly_files_included": 2500,
        "ai_features": _AI_FEATURES_GROWTH,
    },
    "scale": {
        "rate_limit_daily": 25000,
        "max_file_size_mb": 1024,
        "max_custom_profiles": 50,
        "overage_rate_cents": 10,
        "report_storage_mb": 51200,
        "report_default_expiry_days": 180,
        "allowed_report_formats": [
            "json",
            "html",
            "pdf",
            "xml",
            "annotated_pdf",
            "annotated_pdf_markup",
        ],
        "allowed_preflight_sources": _ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": True,
        "whitelabel_enabled": True,
        "priority_processing": True,
        "custom_integrations": False,
        "custom_profiles": True,
        "max_webhooks": 20,
        "approval_chains_enabled": True,
        "max_approval_templates": None,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 2500,
        "monthly_files_included": 10000,
        "ai_features": _AI_FEATURES_SCALE,
    },
    "enterprise": {
        "rate_limit_daily": 100000,
        "max_file_size_mb": 2048,
        "max_custom_profiles": 100,
        "overage_rate_cents": 10,
        "report_storage_mb": 102400,
        "report_default_expiry_days": 365,
        "allowed_report_formats": [
            "json",
            "html",
            "pdf",
            "xml",
            "annotated_pdf",
            "annotated_pdf_markup",
        ],
        "allowed_preflight_sources": _ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": True,
        "whitelabel_enabled": True,
        "priority_processing": True,
        "custom_integrations": True,
        "custom_profiles": True,
        "max_webhooks": 100,
        "approval_chains_enabled": True,
        "max_approval_templates": None,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 25000,
        "monthly_files_included": 100000,
        "ai_features": _AI_FEATURES_ENTERPRISE,
    },
}


class _TestEntitlementDefaultsService:
    def defaults_for(self, plan: str) -> dict:
        return dict(_PLAN_LIMITS_TEST.get(plan, _PLAN_LIMITS_TEST["free"]))

    def overage_rate_cents_for(self, plan: str) -> int:
        return int(_PLAN_LIMITS_TEST.get(plan, {}).get("overage_rate_cents", 0))


@pytest.fixture(autouse=True)
def _install_test_entitlement_defaults():
    """Install the SaaS-style EntitlementDefaultsService stub for OSS tests."""
    from lintpdf.services.entitlement_defaults import (
        DefaultEntitlementDefaultsService,
        set_entitlement_defaults_service,
    )

    set_entitlement_defaults_service(_TestEntitlementDefaultsService())
    yield
    set_entitlement_defaults_service(DefaultEntitlementDefaultsService())


# Paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CORPUS_DIR = Path(__file__).parent / "corpus"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def corpus_dir() -> Path:
    """Path to downloaded test corpus directory."""
    return CORPUS_DIR


@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    """Minimal valid PDF (1 page, no content).

    This is a hand-crafted minimal PDF that passes basic structure
    validation. It has a single blank page with a MediaBox.
    """
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n206\n%%EOF\n"
    )


@pytest.fixture
def sample_pdf_path(tmp_path: Path, minimal_pdf_bytes: bytes) -> Path:
    """Write minimal PDF to a temporary file and return its path."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(minimal_pdf_bytes)
    return pdf_path
