---
title: "API keys"
description: "Mint, label, and revoke the keys clients use to call the API."
section: "panels"
order: 2
---

# API keys

**Path:** `/dashboard/api-keys` · **Who:** Owner / Admin (Members read-only)

Manage the `lpdf_live_...` Bearer tokens your integrations use to call the API. Every key is tied to this tenant; compromising one doesn't expose other customers' data.

## What you see

- Table of existing keys: label, prefix (`lpdf_Abc123...`), created date, last-used timestamp.
- **Create key** button at the top right.
- Per-row **Revoke** (soft-delete; key stops authenticating immediately).

## Actions

| Action | API | Notes |
|---|---|---|
| Mint a key | `POST /api/v1/tenant/keys` | Shows the raw key **exactly once** in a modal. Copy it before closing — we only store the hash. |
| Revoke | `DELETE /api/v1/tenant/keys/{id}` | Immediate. Any in-flight requests complete; new ones return 401. |
| Rename | `PATCH /api/v1/tenant/keys/{id}` | Label only — the key itself is immutable. |

## Gotchas

- **Keys are write-once.** If you lose it, mint a new one and revoke the old. Support can't retrieve it — we only store the SHA-256 hash.
- Label keys by integration name (`zapier-production`, `internal-cron`) so the last-used column helps you spot dead integrations.
- Revoking a key **doesn't cancel in-flight jobs** submitted with it — the jobs finish, report URLs stay valid, but no new submissions will authenticate.

## Related

- [Authentication](../authentication) — how Bearer auth works
- [Rate limits](../getting-started#rate-limits) — per-tenant, not per-key
