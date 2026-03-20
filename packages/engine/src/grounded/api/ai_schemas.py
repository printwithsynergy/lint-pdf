"""Pydantic schemas for AI feature API endpoints."""

from __future__ import annotations

import uuid  # noqa: TC003
from datetime import datetime  # noqa: TC003
from decimal import Decimal

from pydantic import BaseModel, Field

# --- AI Config schemas ---


class AIConfigResponse(BaseModel):
    """Tenant AI configuration."""

    ai_enabled: bool
    billing_mode: str
    credit_balance: Decimal
    overage_rate: Decimal
    monthly_spending_limit: Decimal | None = None
    enabled_categories: list[str]
    default_ai_features: list[str]
    trial_enabled: bool
    trial_expires_at: datetime | None = None
    brand_palette: list[dict[str, object]] | None = None
    reference_logos: list[dict[str, object]] | None = None
    custom_dictionary: list[str] | None = None
    industry_type: str | None = None
    regulatory_market: str | None = None
    default_safe_zone_mm: Decimal
    default_package_capacity_ml: Decimal | None = None
    default_package_surface_area_cm2: Decimal | None = None
    min_image_quality_score: int
    delta_e_squall_threshold: Decimal
    delta_e_aground_threshold: Decimal


class AIConfigUpdateRequest(BaseModel):
    """Update tenant AI config (self-service fields only)."""

    enabled_categories: list[str] | None = None
    default_ai_features: list[str] | None = None
    brand_palette: list[dict[str, object]] | None = None
    custom_dictionary: list[str] | None = None
    industry_type: str | None = None
    regulatory_market: str | None = None
    default_safe_zone_mm: Decimal | None = None
    default_package_capacity_ml: Decimal | None = None
    default_package_surface_area_cm2: Decimal | None = None
    min_image_quality_score: int | None = None
    delta_e_squall_threshold: Decimal | None = None
    delta_e_aground_threshold: Decimal | None = None
    monthly_spending_limit: Decimal | None = None


class AdminAIUpdateRequest(BaseModel):
    """Admin-level AI config update."""

    ai_enabled: bool | None = None
    billing_mode: str | None = None
    credit_balance: Decimal | None = None
    overage_rate: Decimal | None = None
    trial_enabled: bool | None = None
    trial_expires_at: datetime | None = None
    enabled_categories: list[str] | None = None
    monthly_spending_limit: Decimal | None = None


# --- Logo schemas ---


class LogoUploadResponse(BaseModel):
    """Response after uploading a reference logo."""

    id: str
    name: str
    storage_key: str
    message: str = "Logo uploaded successfully"


# --- Palette schemas ---


class PaletteUpdateRequest(BaseModel):
    """Set brand color palette."""

    colors: list[dict[str, str]] = Field(
        description="Array of color objects with 'name', 'value' (hex), and optional 'color_space'."
    )


# --- Dictionary schemas ---


class DictionaryUpdateRequest(BaseModel):
    """Set custom spell-check dictionary."""

    words: list[str] = Field(description="Array of words to add to custom dictionary.")


# --- Credit schemas ---


class CreditBalanceResponse(BaseModel):
    """Current AI credit balance."""

    credit_balance: Decimal
    billing_mode: str
    packages_active: int
    package_credits_remaining: int
    monthly_spent: Decimal
    monthly_spending_limit: Decimal | None = None


class CreditTopupRequest(BaseModel):
    """Purchase credit package."""

    credits: int = Field(ge=100, description="Number of credits to purchase.")


class CreditTopupResponse(BaseModel):
    """Response after purchasing credits."""

    package_id: uuid.UUID
    credits_purchased: int
    message: str = "Credits added successfully"


class AdminCreditGrantRequest(BaseModel):
    """Admin grants credits to a tenant."""

    credits: int = Field(ge=1, description="Number of credits to grant.")
    price_paid: Decimal = Field(default=Decimal("0"), description="Price paid (0 for grants).")
    expires_at: datetime | None = None


# --- Usage schemas ---


class AIUsageEntry(BaseModel):
    """Single AI usage log entry."""

    id: uuid.UUID
    job_id: uuid.UUID | None
    category: str
    feature: str
    credits_consumed: int
    cost: Decimal
    processing_time_ms: int
    created_at: datetime


class AIUsageResponse(BaseModel):
    """AI usage report."""

    entries: list[AIUsageEntry]
    total_credits_consumed: int
    total_cost: Decimal
    total: int
    page: int
    page_size: int


class AITrendDataPoint(BaseModel):
    """Single data point in AI trend analysis."""

    date: str
    total_jobs: int
    ai_jobs: int
    credits_consumed: int
    cost: Decimal
    avg_findings_per_job: float


class AITrendResponse(BaseModel):
    """AI usage trend data for SPC charts."""

    data_points: list[AITrendDataPoint]
    period: str


# --- Preset schemas ---


class AIPresetFeature(BaseModel):
    """Feature included in an AI preset."""

    slug: str
    category: str
    tier: str


class AIPresetResponse(BaseModel):
    """AI preset details."""

    slug: str
    name: str
    description: str
    features: list[AIPresetFeature]


class AIPresetListResponse(BaseModel):
    """List of available AI presets."""

    presets: list[AIPresetResponse]


# --- NL Voyage Plan generation schemas ---


class NLVoyagePlanRequest(BaseModel):
    """Natural language voyage plan generation."""

    description: str = Field(
        min_length=10,
        max_length=2000,
        description="Natural language description of desired preflight checks.",
    )


class NLVoyagePlanResponse(BaseModel):
    """Generated voyage plan from NL description."""

    voyage_plan: dict[str, object]
    explanation: str
    confidence: float


# --- NL Report interpretation schemas ---


class NLInterpretResponse(BaseModel):
    """Plain language interpretation of Captain's Log findings."""

    summary: str
    interpretations: list[dict[str, object]]


# --- Admin AI trial ---


class AdminTrialRequest(BaseModel):
    """Set trial period for a tenant."""

    trial_enabled: bool = True
    trial_days: int = Field(default=14, ge=1, le=90, description="Trial duration in days.")
