# Wave V V-08 — Toggle Audit Log

**Wave:** V (parallel with Tier-0 per Phase 0 Q1)
**Deliverable:** Append-only audit log row for every override mutation
**EM estimate:** 0.4
**Design date:** 2026-04-26
**Dependency:** V-07 (toggle tables + override endpoints)

## What this delivers

A `ToggleAuditLog` row written **synchronously** before every PUT or DELETE
on a `ToggleOverride`. Captures the full before/after snapshot so a
compliance review can answer "who turned off F-22 last week?" without
reconstructing state from journal logs.

## Why an explicit logger, not middleware

Generic FastAPI middleware can't read the request body without
prematurely consuming the stream and breaks endpoints that need to
re-read it. It also fires on every request including health probes,
which would dilute the log. We instead expose a tiny helper module
that V-07's mutation handlers call directly — one function call,
typed arguments, zero ambiguity.

## New table

```python
class ToggleAuditLog(Base):
    __tablename__ = "toggle_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"))
    toggle_id: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[ToggleScope]                  # TENANT | WORKFLOW | CALL
    scope_id: Mapped[str]                       # the affected scope id
    action: Mapped[str]                         # CREATE | UPDATE | DELETE
    before_value: Mapped[object | None]         # JSONB (null on CREATE)
    after_value: Mapped[object | None]          # JSONB (null on DELETE)
    before_locked: Mapped[bool | None]
    after_locked: Mapped[bool | None]
    actor: Mapped[str]                          # api_key id, user_id, "system"
    surface: Mapped[str]                        # "api" | "sdk" | "desktop"
    created_at: Mapped[datetime]
```

Indexed on `(tenant_id, toggle_id)` for the common "show changes to F-22"
audit lookup and on `(tenant_id, created_at DESC)` for the recent-changes
view.

## API surface

`GET /api/v1/tenant/toggles/audit` — paginated audit log, filterable by
`toggle_id`, `scope`, `action`, `since` / `until` timestamps. Read-only;
write path lives entirely inside V-07's mutation handlers.

## Retention

Indefinite. Compliance reviews can reach back arbitrarily far. A cron
job (deferred to v2.1) may archive rows older than 2 years to cold
storage; out of scope here.

## Test plan

* `tests/tenants/test_toggle_audit.py` — unit tests on `record()` semantics
* `tests/api/test_toggles_audit_api.py` — endpoint integration: every
  PUT and DELETE writes exactly one log row with the right diff

## Read-only / no-stub

- ✓ No PDF mutation; pure config layer
- ✓ Append-only — no UPDATE on the audit log
- ✓ Synchronous write inside the same DB transaction as the override
- ✓ Tests cover create / update / delete and locked transitions
