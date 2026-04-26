# Wave V V-12 — Legacy Settings → ToggleOverride Migration

**Wave:** V (parallel with Tier-0 per Phase 0 Q1)
**Deliverable:** Idempotent script that materializes existing
`Tenant.entitlement_overrides` JSON into typed `ToggleOverride` rows
**EM estimate:** 0.5
**Design date:** 2026-04-26
**Dependency:** V-07 (toggle tables) + V-08 (audit log)

## What this delivers

Standalone CLI script that walks every active `Tenant`, reads the
legacy ``entitlement_overrides`` JSON, and emits one `ToggleOverride`
row at TENANT scope for each known knob. The script also pre-seeds the
`Toggle` registry with the canonical entry for each migrated knob so
the resolver has a default to fall back to when the override is
removed. Rerunning the script is a no-op (every insert is gated on a
"row already exists" check).

The legacy `entitlement_overrides` column is **not** modified —
backward compat is preserved for any code path still reading it
directly. Subsequent waves migrate those readers to call
`ConfigResolver.resolve()`; V-12 only seeds the new home.

## Knobs migrated

| Legacy key (Tenant.entitlement_overrides) | Toggle ID                      | Type     | Merge   |
|-------------------------------------------|--------------------------------|----------|---------|
| `ai_features` (list[str])                 | `ai_features`                  | OBJECT   | UNION   |
| `monthly_ai_credits` (int cents)          | `limits.monthly_ai_credits`    | NUMERIC  | REPLACE |
| `monthly_files` (int)                     | `limits.monthly_files`         | NUMERIC  | REPLACE |
| `rate_limit_daily` (int)                  | `limits.rate_limit_daily`      | NUMERIC  | REPLACE |
| `max_file_size_mb` (int)                  | `limits.max_file_size_mb`      | NUMERIC  | REPLACE |
| `default_profile_id` (str)                | `defaults.profile_id`          | STRING   | REPLACE |
| `unbranded_by_default` (bool)             | `defaults.unbranded`           | BOOLEAN  | REPLACE |

Only these 7 keys are handled in v2.0. Future Path A work (Wave A
dieline knobs, EPM Core thresholds) ships its own toggles directly
into the registry — those don't need migration because they had no
prior storage.

## Script

`packages/engine/src/lintpdf/scripts/v12_migrate_legacy.py`

```bash
python -m lintpdf.scripts.v12_migrate_legacy --dry-run
python -m lintpdf.scripts.v12_migrate_legacy        # apply
python -m lintpdf.scripts.v12_migrate_legacy --tenant-id <uuid>  # one tenant
```

Output:
```
tenant aaaa…: created 3 overrides, skipped 0 (already present), 4 keys absent
tenant bbbb…: created 0 overrides, skipped 5 (already present), 2 keys absent
done — 12 overrides created across 8 tenants
```

## Audit trail

Every migration insert writes one `ToggleAuditLog` row with
`actor="v12_migration"`, `surface="script"`, so the introduction of
each override is forensically recoverable.

## Test plan

* `tests/scripts/test_v12_migrate_legacy.py` — unit tests:
  - mapping fidelity (each legacy key → correct toggle id + type)
  - idempotency (running twice creates no duplicate rows)
  - dry-run mode emits no DB writes
  - per-tenant filter
  - skips tenants with no `entitlement_overrides`
  - auto-creates missing Toggle registry rows
  - audit row is written per inserted override

## Rollback

Two paths:
1. `DELETE FROM toggle_overrides WHERE set_by = 'v12_migration'` —
   the audit log preserves the before/after, so the inserts can be
   safely undone with no data loss.
2. Re-running the script after editing the legacy column updates the
   override to match (the script treats existing v12_migration rows as
   editable; manually-set rows with `set_by != 'v12_migration'` are
   never touched).

## Read-only / no-stub

- ✓ No PDF mutation; pure config migration
- ✓ Idempotent; safe to re-run
- ✓ Dry-run mode for production verification
- ✓ Tests cover create / skip / audit-trail / dry-run
