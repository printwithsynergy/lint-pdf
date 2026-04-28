"""Single-source-of-truth BrandSpec resolver.

Phase 0.7 PR-B3b — reads brand specs from the unified-config substrate
(``ToggleOverride(toggle_id='brand', scope=TENANT)``) instead of the
legacy ``brand_specs`` table.

Given a job (and optionally the custom endpoint it was submitted
through), pick the one brand spec whose color constraints apply.
The resolution chain:

1. ``job.brand_spec_id`` — per-submission override. Wins.
2. ``endpoint.default_brand_spec_id`` — endpoint default. Used
   when the job didn't supply an explicit spec.
3. Tenant-default spec — the non-archived entry with
   ``is_default=True``. Used when neither of the above applies.
4. ``None`` — the tenant has no applicable spec; the strict
   color advisories stay suppressed. (See WS-7.)

Archived specs are excluded from the tenant-default fallback so
tenants can retire a spec without having to remove every endpoint
and job reference first; historical jobs that captured the spec
at submit time keep resolving to it regardless of archive state.

The :class:`ResolvedBrandSpec` dataclass shape is unchanged — analyzers
and viewer consumers still see exactly the same frozen view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lintpdf.brand_specs import storage

if TYPE_CHECKING:
    import uuid as uuid_mod
    from typing import Protocol

    from sqlalchemy.orm import Session

    from lintpdf.api.models import Job

    class _BrandSpecHolder(Protocol):
        """Structural type for the resolver's optional ``endpoint`` arg.

        Phase 0.7 PR-B5 — endpoints are Workflow rows now, but the
        chain-resolution logic only reads ``default_brand_spec_id``.
        Any object exposing that attribute (Workflow, an in-memory
        SimpleNamespace, etc.) is fine.
        """

        default_brand_spec_id: uuid_mod.UUID | None


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


def _snapshot_value(value: dict[str, Any] | None) -> ResolvedBrandSpec | None:
    """Copy a stored dict into the frozen dataclass.

    The dict comes from the tenant's ``brand`` ToggleOverride; we keep
    a defensive copy so callers can't mutate the on-disk snapshot.
    """
    if value is None:
        return None
    raw_id = value.get("id")
    if not raw_id:
        return None
    import uuid as _uuid

    try:
        spec_id = _uuid.UUID(raw_id) if isinstance(raw_id, str) else raw_id
    except ValueError:
        return None
    colors = list(value.get("colors") or [])
    rich_black_raw = value.get("rich_black_spec")
    rich_black = dict(rich_black_raw) if isinstance(rich_black_raw, dict) else None
    return ResolvedBrandSpec(
        id=spec_id,
        name=value.get("name") or "",
        colors=colors,
        rich_black_spec=rich_black,
    )


def resolve_brand_spec_for_tenant(
    db: Session, *, tenant_id: uuid_mod.UUID
) -> ResolvedBrandSpec | None:
    """Return the tenant-default BrandSpec, or ``None`` when the
    tenant has no non-archived default entry."""
    return _snapshot_value(storage.get_default(db, tenant_id))


def resolve_brand_spec_for_job(
    db: Session,
    *,
    job: Job,
    endpoint: _BrandSpecHolder | None = None,
) -> ResolvedBrandSpec | None:
    """Walk the resolution chain for a single job.

    Order of precedence:

    1. ``job.brand_spec_id`` (submit-time override).
    2. ``endpoint.default_brand_spec_id`` (endpoint default).
    3. Tenant-default brand spec.

    Returns ``None`` when nothing in the chain resolves. The
    orchestrator turns a ``None`` into the "brand palette not
    present" gate that suppresses strict color advisories.
    """
    specs = storage.load_specs(db, job.tenant_id)

    if job.brand_spec_id is not None:
        value = specs.get(str(job.brand_spec_id))
        if value is not None:
            return _snapshot_value(value)

    if endpoint is not None and endpoint.default_brand_spec_id is not None:
        value = specs.get(str(endpoint.default_brand_spec_id))
        if value is not None:
            return _snapshot_value(value)

    # Tenant default fallback.
    for value in specs.values():
        if value.get("is_default") and not value.get("is_archived"):
            return _snapshot_value(value)
    return None
