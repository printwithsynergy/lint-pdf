"""Wave V V-07 toggle resolver.

Single hot-path resolver consumed by every endpoint, SDK call, and desktop
action that reads a configurable knob.

Resolution order (highest → lowest):

    1. per-call override
    2. workflow override (if workflow_id provided)
    3. tenant override
    4. ``Toggle.default_value``

A locked tenant override (``locked = TRUE``) cannot be replaced by lower
scopes — the locked tenant value wins and per-call/workflow overrides are
ignored for that toggle. Per Phase 1 Q4, only the TENANT scope may lock.

Per-toggle merge strategy is declared on the registry row:

    * ``REPLACE`` — per-call value replaces lower scope entirely (default)
    * ``MERGE``   — per-key merge for OBJECT toggles
    * ``UNION``   — set-union for arrays (e.g. ``ai_features``)

Caching: in-process LRU per ``(tenant_id, workflow_id)``, 60-second TTL.
Mutation endpoints invoke :meth:`ConfigResolver.invalidate` synchronously
before responding.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from siftpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleOverride,
    ToggleScope,
)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

_DEFAULT_TTL_S = 60


class _CacheEntry:
    __slots__ = ("expires_at", "value")

    def __init__(self, value: dict[str, Any], ttl_s: int):
        self.value = value
        self.expires_at = time.monotonic() + ttl_s


class ConfigResolver:
    """Tenant → workflow → per-call cascade resolver.

    Thread-safe. Cache keyed by ``(tenant_id, workflow_id)``; entries
    expire after ``cache_ttl_s`` seconds. Tests can pass ``cache_ttl_s=0``
    to disable caching (every call hits the database).
    """

    def __init__(self, session: Session, *, cache_ttl_s: int = _DEFAULT_TTL_S) -> None:
        self._session = session
        self._cache_ttl_s = cache_ttl_s
        self._cache: dict[tuple[str, str | None], _CacheEntry] = {}
        self._lock = threading.RLock()

    # ---- public API -----------------------------------------------

    def resolve(
        self,
        toggle_id: str,
        *,
        tenant_id: str | uuid.UUID,
        workflow_id: str | None = None,
        call_overrides: dict[str, Any] | None = None,
    ) -> Any:
        """Return the resolved value for a single toggle.

        Raises ``KeyError`` if no Toggle registry row exists for ``toggle_id``.
        """
        resolved = self.resolve_many(
            [toggle_id],
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            call_overrides=call_overrides,
        )
        if toggle_id not in resolved:
            raise KeyError(f"unknown toggle: {toggle_id!r}")
        return resolved[toggle_id]

    def resolve_many(
        self,
        toggle_ids: Iterable[str],
        *,
        tenant_id: str | uuid.UUID,
        workflow_id: str | None = None,
        call_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve multiple toggles in one query (preferred for hot paths)."""
        ids = list(toggle_ids)
        if not ids:
            return {}

        tenant_key = str(tenant_id)
        snapshot = self._snapshot(tenant_key, workflow_id)

        out: dict[str, Any] = {}
        for tid in ids:
            entry = snapshot.get(tid)
            if entry is None:
                continue
            out[tid] = self._cascade(
                entry,
                call_value=(call_overrides or {}).get(tid, _MISSING),
            )
        return out

    def invalidate(
        self,
        *,
        tenant_id: str | uuid.UUID | None = None,
        workflow_id: str | None = None,
        toggle_id: str | None = None,
    ) -> None:
        """Drop cache entries matching the given scope.

        Calling without args clears the entire cache. ``toggle_id`` is
        accepted for API symmetry but invalidates the parent tenant entry
        (per-toggle granularity isn't worth the bookkeeping).
        """
        with self._lock:
            if tenant_id is None:
                self._cache.clear()
                return
            tenant_key = str(tenant_id)
            keys_to_drop = [
                k
                for k in self._cache
                if k[0] == tenant_key and (workflow_id is None or k[1] == workflow_id)
            ]
            for k in keys_to_drop:
                self._cache.pop(k, None)

    # ---- snapshot loading + caching ------------------------------

    def _snapshot(self, tenant_key: str, workflow_id: str | None) -> dict[str, _ResolvedEntry]:
        """Load (or fetch from cache) the merged-tenant+workflow view."""
        cache_key = (tenant_key, workflow_id)
        if self._cache_ttl_s > 0:
            with self._lock:
                hit = self._cache.get(cache_key)
                if hit is not None and hit.expires_at > time.monotonic():
                    return hit.value
        snapshot = self._build_snapshot(tenant_key, workflow_id)
        if self._cache_ttl_s > 0:
            with self._lock:
                self._cache[cache_key] = _CacheEntry(snapshot, self._cache_ttl_s)
        return snapshot

    def _build_snapshot(
        self, tenant_key: str, workflow_id: str | None
    ) -> dict[str, _ResolvedEntry]:
        toggles = self._session.execute(select(Toggle)).scalars().all()

        scope_ids: list[tuple[ToggleScope, str]] = [
            (ToggleScope.TENANT, tenant_key),
        ]
        if workflow_id is not None:
            scope_ids.append((ToggleScope.WORKFLOW, workflow_id))

        overrides_q = select(ToggleOverride).where(
            (ToggleOverride.scope == ToggleScope.TENANT) & (ToggleOverride.scope_id == tenant_key)
        )
        if workflow_id is not None:
            overrides_q = select(ToggleOverride).where(
                (
                    (ToggleOverride.scope == ToggleScope.TENANT)
                    & (ToggleOverride.scope_id == tenant_key)
                )
                | (
                    (ToggleOverride.scope == ToggleScope.WORKFLOW)
                    & (ToggleOverride.scope_id == workflow_id)
                )
            )
        overrides = self._session.execute(overrides_q).scalars().all()

        by_id: dict[str, _ResolvedEntry] = {t.id: _ResolvedEntry(toggle=t) for t in toggles}
        for ov in overrides:
            entry = by_id.get(ov.toggle_id)
            if entry is None:
                continue
            if ov.scope == ToggleScope.TENANT:
                entry.tenant_value = ov.value
                entry.tenant_locked = ov.locked
            elif ov.scope == ToggleScope.WORKFLOW:
                entry.workflow_value = ov.value
        return by_id

    # ---- cascade --------------------------------------------------

    @staticmethod
    def _cascade(entry: _ResolvedEntry, *, call_value: Any) -> Any:
        toggle = entry.toggle
        # Locked tenant override short-circuits everything below.
        if entry.tenant_locked and entry.tenant_value is not _MISSING:
            return entry.tenant_value

        strategy = toggle.merge_strategy
        merged = toggle.default_value
        if entry.tenant_value is not _MISSING:
            merged = _apply(strategy, merged, entry.tenant_value)
        if entry.workflow_value is not _MISSING:
            merged = _apply(strategy, merged, entry.workflow_value)
        if call_value is not _MISSING:
            merged = _apply(strategy, merged, call_value)
        return merged


# ---- internals ------------------------------------------------------


class _Missing:
    """Sentinel — distinct from None."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING: Any = _Missing()


class _ResolvedEntry:
    """In-memory snapshot of one toggle plus tenant/workflow overrides."""

    __slots__ = ("tenant_locked", "tenant_value", "toggle", "workflow_value")

    def __init__(self, *, toggle: Toggle) -> None:
        self.toggle = toggle
        self.tenant_value: Any = _MISSING
        self.tenant_locked: bool = False
        self.workflow_value: Any = _MISSING


def _apply(strategy: MergeStrategy, base: Any, override: Any) -> Any:
    """Apply ``override`` on top of ``base`` per the merge strategy."""
    if strategy == MergeStrategy.REPLACE:
        return override
    if strategy == MergeStrategy.UNION:
        if not isinstance(base, list):
            base = (
                []
                if base is None
                else list(base)
                if isinstance(base, Iterable) and not isinstance(base, str)
                else [base]
            )
        if not isinstance(override, list):
            override = [override] if override is not None else []
        seen: dict[Any, None] = {}
        for item in [*base, *override]:
            if item not in seen:
                seen[item] = None
        return list(seen)
    if strategy == MergeStrategy.MERGE:
        if not isinstance(base, dict) or not isinstance(override, dict):
            return override
        merged = dict(base)
        merged.update(override)
        return merged
    return override


__all__ = ["ConfigResolver"]
