"""Shared test fixtures for AI feature tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Tenant fixtures
# ---------------------------------------------------------------------------


def _make_tenant(tenant_id: uuid.UUID | None = None) -> MagicMock:
    """Create a mock Tenant object."""
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.name = "Test Airline"
    tenant.plan = "growth"
    tenant.is_active = True
    return tenant


@pytest.fixture
def tenant_id() -> uuid.UUID:
    """Stable tenant UUID for use across fixtures."""
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def mock_tenant(tenant_id: uuid.UUID) -> MagicMock:
    """A mock Tenant object with a stable UUID."""
    return _make_tenant(tenant_id)


# ---------------------------------------------------------------------------
# AI config fixtures
# ---------------------------------------------------------------------------


def _make_ai_config(
    tenant_id: uuid.UUID,
    *,
    ai_enabled: bool = True,
    credit_balance: Decimal = Decimal("100.00"),
    billing_mode: str = "pay_per_use",
    overage_rate: Decimal = Decimal("0.10"),
    monthly_spending_limit: Decimal | None = None,
    enabled_categories: list[str] | None = None,
    default_ai_features: list[str] | None = None,
    trial_enabled: bool = False,
    trial_expires_at: datetime | None = None,
    brand_palette: list[dict[str, Any]] | None = None,
    reference_logos: list[dict[str, Any]] | None = None,
    custom_dictionary: list[str] | None = None,
    industry_type: str | None = None,
    regulatory_market: str | None = None,
    delta_e_delay_threshold: Decimal = Decimal("2.0"),
    delta_e_no_fly_threshold: Decimal = Decimal("5.0"),
    min_image_quality_score: int = 50,
    default_safe_zone_mm: Decimal = Decimal("3.0"),
) -> MagicMock:
    """Create a mock TenantAIConfig."""
    config = MagicMock()
    config.id = uuid.uuid4()
    config.tenant_id = tenant_id
    config.ai_enabled = ai_enabled
    config.credit_balance = credit_balance
    config.billing_mode = billing_mode
    config.overage_rate = overage_rate
    config.monthly_spending_limit = monthly_spending_limit
    config.enabled_categories = enabled_categories if enabled_categories is not None else ["all"]
    config.default_ai_features = default_ai_features or []
    config.trial_enabled = trial_enabled
    config.trial_expires_at = trial_expires_at
    config.brand_palette = brand_palette
    config.reference_logos = reference_logos
    config.custom_dictionary = custom_dictionary
    config.industry_type = industry_type
    config.regulatory_market = regulatory_market
    config.delta_e_delay_threshold = delta_e_delay_threshold
    config.delta_e_no_fly_threshold = delta_e_no_fly_threshold
    config.delta_e_squall_threshold = delta_e_delay_threshold
    config.delta_e_aground_threshold = delta_e_no_fly_threshold
    config.delta_e_warning_threshold = delta_e_delay_threshold
    config.delta_e_error_threshold = delta_e_no_fly_threshold
    config.min_image_quality_score = min_image_quality_score
    config.default_safe_zone_mm = default_safe_zone_mm
    config.default_package_capacity_ml = None
    config.default_package_surface_area_cm2 = None
    return config


@pytest.fixture
def mock_ai_config(tenant_id: uuid.UUID) -> MagicMock:
    """TenantAIConfig with AI enabled and 100 credits."""
    return _make_ai_config(tenant_id)


@pytest.fixture
def mock_ai_config_disabled(tenant_id: uuid.UUID) -> MagicMock:
    """TenantAIConfig with AI disabled."""
    return _make_ai_config(tenant_id, ai_enabled=False)


@pytest.fixture
def mock_ai_config_trial_expired(tenant_id: uuid.UUID) -> MagicMock:
    """TenantAIConfig with trial enabled but expired."""
    return _make_ai_config(
        tenant_id,
        trial_enabled=True,
        trial_expires_at=datetime.now(UTC) - timedelta(days=1),
    )


@pytest.fixture
def mock_ai_config_trial_active(tenant_id: uuid.UUID) -> MagicMock:
    """TenantAIConfig with trial enabled and still active."""
    return _make_ai_config(
        tenant_id,
        trial_enabled=True,
        trial_expires_at=datetime.now(UTC) + timedelta(days=7),
    )


@pytest.fixture
def mock_ai_config_categories(tenant_id: uuid.UUID) -> MagicMock:
    """TenantAIConfig with specific categories enabled."""
    return _make_ai_config(
        tenant_id,
        enabled_categories=["barcode", "content_quality"],
    )


@pytest.fixture
def mock_ai_config_no_categories(tenant_id: uuid.UUID) -> MagicMock:
    """TenantAIConfig with no categories enabled (empty list)."""
    return _make_ai_config(
        tenant_id,
        enabled_categories=[],
    )


# ---------------------------------------------------------------------------
# Database session fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_session() -> MagicMock:
    """A mock SQLAlchemy Session with chainable query interface.

    Usage:
        mock_db_session.query().filter().first.return_value = some_object
    """
    session = MagicMock()
    # Make the query chain work:  db.query(X).filter(Y).first()
    query_chain = MagicMock()
    session.query.return_value = query_chain
    query_chain.filter.return_value = query_chain
    query_chain.filter_by.return_value = query_chain
    query_chain.order_by.return_value = query_chain
    query_chain.limit.return_value = query_chain
    query_chain.offset.return_value = query_chain
    query_chain.first.return_value = None
    query_chain.all.return_value = []
    query_chain.scalar.return_value = 0
    return session


# ---------------------------------------------------------------------------
# PDF bytes fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes for testing (single blank page)."""
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


# ---------------------------------------------------------------------------
# GPU client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_gpu_client() -> MagicMock:
    """Mocked GPUInferenceClient — all methods return plausible dicts."""
    client = MagicMock()
    client.assess_image_quality.return_value = {
        "score": 72.5,
        "model": "musiq",
    }
    client.classify_document.return_value = {
        "class": "packaging_artwork",
        "confidence": 0.92,
    }
    client.detect_logos.return_value = {
        "logos": [{"label": "brand_logo", "confidence": 0.95, "bbox": [10, 10, 100, 100]}],
    }
    client.detect_nsfw.return_value = {
        "is_nsfw": False,
        "score": 0.01,
    }
    client.detect_objects.return_value = {
        "objects": [
            {"label": "barcode", "confidence": 0.88, "bbox": [200, 300, 400, 500]},
        ],
    }
    client.embed_image.return_value = {
        "embedding": [0.1] * 768,
    }
    client.detect_outlines.return_value = {
        "text_regions": [],
    }
    client.detect_symbols.return_value = {
        "symbols": [],
    }
    client.translate_text.return_value = {
        "translated_text": "Bonjour le monde",
        "source_lang": "en",
        "target_lang": "fr",
    }
    client.health_check.return_value = True
    return client


# ---------------------------------------------------------------------------
# Semantic model helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_semantic_doc() -> MagicMock:
    """A minimal SemanticDocument mock for AI analyzer tests."""
    page = MagicMock()
    page.page_num = 1
    page.media_box = MagicMock(x0=0, y0=0, x1=612, y1=792)
    page.trim_box = MagicMock(x0=10, y0=10, x1=602, y1=782)
    page.content_stream = None
    page.color_spaces = {}
    page.resources = {}
    page.fonts = {}

    doc = MagicMock()
    doc.version = "1.7"
    doc.page_count = 1
    doc.is_encrypted = False
    doc.pages = [page]
    doc.catalog = {}
    return doc
