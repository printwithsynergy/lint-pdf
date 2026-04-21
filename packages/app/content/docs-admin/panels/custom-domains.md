---
title: "Custom domains panel"
description: "Approve and debug whitelabel custom-domain requests."
---

# Custom domains

**Path:** `/dashboard/admin/custom-domains` · **Who:** Super admin · **Scope:** Cross-tenant

All `brand_custom_domain` and per-profile `custom_domain` requests in the system, with their CNAME verification status. Use this to unblock a customer whose DNS probe is stuck.

## What you see

- Table: tenant, domain, kind (reports / app), verified flag, requested-at, latest CNAME probe result.
- Expected CNAME target: shown inline (`edge.lintpdf.com`).

## Actions

| Action | API | Notes |
|---|---|---|
| Force re-probe | `POST /api/v1/admin/custom-domains/{id}/probe` | Bypasses the 5-minute beat interval. Returns `verified`, `resolved_cname`, any DNS error. |
| Manually approve | `PATCH /api/v1/admin/custom-domains/{id}` with `verified=true` | Use sparingly — only when DNS is correct but the probe is flaky. |
| Revoke | `DELETE /api/v1/admin/custom-domains/{id}` | Clears the column on the tenant / brand_profile row. Customer loses whitelabel until they re-register. |

## Gotchas

- The `probe_pending_custom_domains` Celery beat runs every 5 minutes. If a customer just pointed their CNAME, they'll see it flip verified within that window automatically — no action needed here.
- Caddy (the edge) issues certs on the first HTTPS request after verify flips true. It doesn't prewarm. Expect a few seconds of ACME-challenge latency on the first customer visit.

## Related

- Branding docs at [`/docs/custom-domains`](../../../docs/custom-domains) cover the customer-facing flow.
