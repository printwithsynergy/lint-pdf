"""Phase 0.7 PR-A — per-job ResolvedConfigSnapshot writer.

Called once per job at submit time, after the cascade resolves and
before the preflight worker runs. Captures:

* ``resolved_payload`` — the merged ``{toggle_id: value}`` dict the job
  actually saw.
* ``provenance`` — parallel ``{toggle_id: scope}`` dict where scope is
  one of ``system`` / ``tenant`` / ``workflow`` / ``call``. For toggles
  with non-REPLACE merge strategies the recorded scope is the
  *highest* scope that contributed a value (call > workflow > tenant >
  system); per-key provenance for merged dicts/arrays is out of scope
  for v1 — callers needing it can re-query the override rows directly.
* ``system_default_version`` — string identifier of the shipped
  default-values bundle that fed scope=system. Bumped when the default
  payload changes; opaque to consumers.

The function flushes the snapshot row but does not commit; the caller
controls transaction boundaries so the snapshot writes atomically with
the Job row.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from siftpdf.tenants.config_resolver import ConfigResolver
from siftpdf.tenants.toggle_models import (
    ResolvedConfigSnapshot,
    Toggle,
    ToggleOverride,
    ToggleScope,
)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session


SYSTEM_DEFAULT_VERSION = "1"
"""Bump this when the seeded ``Toggle.default_value`` payload changes."""


def write_snapshot(
    db: Session,
    *,
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    workflow_id: str | None,
    call_overrides: dict[str, Any] | None = None,
    system_default_version: str = SYSTEM_DEFAULT_VERSION,
) -> ResolvedConfigSnapshot:
    """Resolve the cascade for this job, persist the snapshot row.

    Returns the ORM row (already added to the session, not committed).
    """
    resolver = ConfigResolver(db, cache_ttl_s=0)

    toggles = db.execute(select(Toggle)).scalars().all()
    toggle_ids = [t.id for t in toggles]

    resolved = resolver.resolve_many(
        toggle_ids,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        call_overrides=call_overrides,
    )

    provenance = _compute_provenance(
        db,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        call_overrides=call_overrides or {},
        resolved_keys=resolved.keys(),
    )

    row = ResolvedConfigSnapshot(
        job_id=job_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        resolved_payload=dict(resolved),
        provenance=provenance,
        system_default_version=system_default_version,
    )
    db.add(row)
    db.flush()
    return row


def _compute_provenance(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    workflow_id: str | None,
    call_overrides: dict[str, Any],
    resolved_keys: Any,
) -> dict[str, str]:
    """Return ``{toggle_id: highest_scope_that_set_a_value}``.

    A locked TENANT override always reads as ``tenant`` regardless of
    higher scopes (the lock short-circuits the cascade upstream).
    """
    tenant_str = str(tenant_id)
    overrides_q = select(ToggleOverride).where(
        (ToggleOverride.scope == ToggleScope.TENANT) & (ToggleOverride.scope_id == tenant_str)
    )
    if workflow_id is not None:
        overrides_q = select(ToggleOverride).where(
            ((ToggleOverride.scope == ToggleScope.TENANT) & (ToggleOverride.scope_id == tenant_str))
            | (
                (ToggleOverride.scope == ToggleScope.WORKFLOW)
                & (ToggleOverride.scope_id == workflow_id)
            )
        )
    rows = db.execute(overrides_q).scalars().all()

    has_tenant: set[str] = set()
    locked_tenant: set[str] = set()
    has_workflow: set[str] = set()
    for ov in rows:
        if ov.scope == ToggleScope.TENANT:
            has_tenant.add(ov.toggle_id)
            if ov.locked:
                locked_tenant.add(ov.toggle_id)
        elif ov.scope == ToggleScope.WORKFLOW:
            has_workflow.add(ov.toggle_id)

    has_call = set(call_overrides.keys())

    provenance: dict[str, str] = {}
    for tid in resolved_keys:
        if tid in locked_tenant:
            provenance[tid] = "tenant"
        elif tid in has_call:
            provenance[tid] = "call"
        elif tid in has_workflow:
            provenance[tid] = "workflow"
        elif tid in has_tenant:
            provenance[tid] = "tenant"
        else:
            provenance[tid] = "system"
    return provenance
