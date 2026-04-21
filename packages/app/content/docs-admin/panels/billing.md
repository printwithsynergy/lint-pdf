---
title: "Billing panel"
description: "Per-tenant overrides for AI credits + file quotas; grant + revoke metered packages."
---

# Billing

**Path:** `/dashboard/admin/billing` · **Who:** Super admin · **Scope:** Per-tenant (select from dropdown)

Override a tenant's monthly plan defaults without changing their plan, and grant or revoke individual metered packages (extra AI credits, file packs). Used when a customer needs a one-off bump or when support grants goodwill credits.

## What you see

- Tenant picker at the top (live-filter by name).
- "Plan defaults" card: read-only display of the current plan's monthly AI credits + file quotas.
- "Overrides" card: editable inputs for `monthly_ai_credits_override` and `monthly_files_override`. Leave blank = use plan default.
- "Metered packages" table: every grant/purchase on the tenant's account, with revoke buttons.

## Actions

| Action | API | Notes |
|---|---|---|
| Save override | `PATCH /api/v1/admin/tenants/{id}/overrides` | Takes effect at the next `invoice.paid` — the current billing cycle's allotment is already minted. |
| Grant package | `POST /api/v1/admin/tenants/{id}/metered-packages` | Creates a `MeteredPackage` row immediately, no Stripe charge. Shows up in the tenant's next balance refresh (~10s). |
| Revoke package | `DELETE /api/v1/admin/tenants/{id}/metered-packages/{pkg-id}` | Only removes the LintPDF-side balance. **Doesn't issue a Stripe refund** — do that separately in the Stripe dashboard. |

## Gotchas

- `monthly_ai_credits_override` + `monthly_files_override` are **additive replacements**, not deltas. Setting `files_override = 500` means the tenant gets exactly 500 files/month starting next invoice, regardless of what their plan says.
- Granting a package of `source=adjustment` is free. `source=purchase` packages should only be created by Stripe webhooks — avoid using this UI for those.
- Revoke is soft: the `MeteredPackage` row stays with `revoked_at` set; the customer just can't spend it. Useful for audit trails.

## Related

- Stripe webhook handler lives at `/api/v1/stripe/webhook` (engine) → triggers `invoice.paid` fulfilment.
