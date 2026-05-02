"""``AIConfigService`` — per-tenant AI configuration lookup (W6c-2f).

Used by ``lintpdf.queue.tasks`` to load the optional AI config object
that downstream analyzers consult for tenant-specific AI knobs (brand
palette, custom dictionary, severity thresholds, etc.). SaaS-only
``TenantAIConfig`` table; OSS default returns ``None`` (no AI config
on OSS-only deploys).

Hosted SaaS overrides via ``set_ai_config_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AIConfigService(Protocol):
    """Look up the tenant's AI configuration row, if any.

    The returned object is duck-typed by downstream analyzers — they
    read attributes like ``brand_palette``, ``custom_dictionary``,
    ``enabled_categories``, etc. SaaS implementations return a
    ``TenantAIConfig`` ORM instance; OSS default returns ``None``.
    """

    def get_config(self, tenant_id: uuid.UUID, db: Session) -> object | None:
        """Return the tenant's AI config, or ``None`` if not configured."""
        ...


class DefaultAIConfigService:
    """Pure no-op default. OSS engine has no AI config concept."""

    def get_config(self, tenant_id: uuid.UUID, db: Session) -> object | None:
        return None


_service: AIConfigService | None = None


def get_ai_config_service() -> AIConfigService:
    global _service
    if _service is None:
        _service = DefaultAIConfigService()
    return _service


def set_ai_config_service(service: AIConfigService | None) -> None:
    global _service
    _service = service
