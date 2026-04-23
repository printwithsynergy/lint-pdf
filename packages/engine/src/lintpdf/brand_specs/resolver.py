"""Single-source-of-truth BrandSpec resolver.

Given a job (and optionally the custom endpoint it was submitted
through), pick the one :class:`BrandSpec` whose colour
constraints apply. The resolution chain:

1. ``job.brand_spec_id`` — per-submission override. Wins.
2. ``endpoint.default_brand_spec_id`` — endpoint default. Used
   when the job didn't supply an explicit spec.
3. Tenant-default spec — the non-archived row with
   ``is_default=TRUE``. Used when neither of the above applies.
4. ``None`` — the tenant has no applicable spec; the strict
   colour advisories stay suppressed. (See WS-7 — that
   behaviour was introduced to stop firing "use pure K"
   warnings on tenants who haven't committed to a brand
   palette yet.)

Archived specs are excluded from the tenant-default fallback so
tenants can retire a spec without having to remove every endpoint
and job reference first; historical jobs that captured the spec
at submit time keep resolving to it regardless of archive state.
"""

from __future__ import annotations

import uuid as uuid_mod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import BrandSpec, CustomEndpoint, Job


@dataclass(frozen=True)
class ResolvedBrandSpec:
    """Immutable view of the BrandSpec a job resolved against.

    Analyzers hold onto this instead of the SQLAlchemy object so
    they can never accidentally mutate and persist a spec in the
    middle of a Celery task.
    """

    id: uuid_mod.UUID
    name: str
    colors: list[dict[str, Any]]
    rich_black_spec: dict[str, float] | None

    @property
    def has_colors(self) -> bool:
        """True when the spec carries at least one non-empty swatch."""
        return bool(self.colors) and any(
            isinstance(c, dict) and c.get("value") for c in self.colors
        )


def _snapshot(spec: BrandSpec | None) -> ResolvedBrandSpec | None:
    """Copy the SQLAlchemy object into the frozen dataclass so the
    ORM session can go away without consumers losing the palette.
    """
    if spec is None:
        return None
    colors = list(spec.colors) if spec.colors else []
    rich_black = dict(spec.rich_black_spec) if spec.rich_black_spec else None
    return ResolvedBrandSpec(
        id=spec.id,
        name=spec.name,
        colors=colors,
        rich_black_spec=rich_black,
    )


def resolve_brand_spec_for_tenant(
    db: Session, *, tenant_id: uuid_mod.UUID
) -> ResolvedBrandSpec | None:
    """Return the tenant-default BrandSpec, or ``None`` when the
    tenant has no non-archived default row."""
    from lintpdf.api.models import BrandSpec

    spec = (
        db.query(BrandSpec)
        .filter(
            BrandSpec.tenant_id == tenant_id,
            BrandSpec.is_default.is_(True),
            BrandSpec.is_archived.is_(False),
        )
        .first()
    )
    return _snapshot(spec)


def resolve_brand_spec_for_job(
    db: Session,
    *,
    job: Job,
    endpoint: CustomEndpoint | None = None,
) -> ResolvedBrandSpec | None:
    """Walk the resolution chain for a single job.

    Order of precedence:

    1. ``job.brand_spec_id`` (submit-time override).
    2. ``endpoint.default_brand_spec_id`` (endpoint default).
    3. Tenant-default BrandSpec (``is_default=TRUE``,
       ``is_archived=FALSE``).

    Returns ``None`` when nothing in the chain resolves. The
    orchestrator turns a ``None`` into the "brand palette not
    present" gate that suppresses strict colour advisories.

    ``db.get()`` is used for the primary-key lookups so a missing
    row (e.g. the spec was hard-deleted after the job was queued)
    yields ``None`` without raising; in that case the chain
    silently falls through to the next candidate.
    """
    from lintpdf.api.models import BrandSpec

    if job.brand_spec_id is not None:
        spec = db.get(BrandSpec, job.brand_spec_id)
        if spec is not None and spec.tenant_id == job.tenant_id:
            return _snapshot(spec)

    if endpoint is not None and endpoint.default_brand_spec_id is not None:
        spec = db.get(BrandSpec, endpoint.default_brand_spec_id)
        if spec is not None and spec.tenant_id == job.tenant_id:
            return _snapshot(spec)

    return resolve_brand_spec_for_tenant(db, tenant_id=job.tenant_id)
