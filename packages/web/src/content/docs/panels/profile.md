---
title: "Brand profile"
description: "Logo, colours, custom domains, and report chrome for your tenant's output."
section: "panels"
order: 14
---

# Brand profile

**Path:** `/dashboard/profile` · **Who:** Owner / Admin

Customise the look of every report this tenant produces — logo, primary colour, accent colour, footer text, and (on whitelabel plans) custom-domain report URLs.

## What you see

- **Default profile** — the one every job uses unless explicitly overridden.
- **Additional profiles** — spin up extra profiles for seasonal campaigns, multi-brand tenants, or per-customer branding.
- Per-profile editor: logo uploader (PNG/SVG up to 2 MB), colour pickers (hex or named), footer text, "hide footer" toggle.
- **Custom domains** card (whitelabel only): `reports.yourcompany.com` + `app.yourcompany.com` with CNAME instructions.

## Actions

| Action | API | Notes |
|---|---|---|
| Upload logo | `POST /api/v1/tenants/{id}/brand-profiles/{pid}/logo` | Served from the same domain as your reports. |
| Edit colours | `PATCH /api/v1/tenants/{id}/brand-profiles/{pid}` | Takes effect on the next report generated. |
| Set default | `PATCH /api/v1/tenants/{id}/default-brand-profile` | Immediate. |
| Request custom domain | `PATCH /api/v1/tenants/{id}/custom-domain` | Validates the CNAME every 5 minutes; status flips `verified=true` automatically once the DNS match is detected. |

## Gotchas

- **Whitelabel is a plan feature** — custom domains require the appropriate entitlement. Contact billing if the picker is disabled.
- **Logo uploads are cached 1 year at the CDN.** Rotating the URL (changing the profile's logo_url) breaks the cache cleanly; editing an existing logo in-place won't purge.
- **Per-request branding** (`POST /api/v1/jobs` with `brand=<profile-id>`) overrides the default. Share links mint their branding at creation time and stay immutable after — useful for preserving a specific look on a URL that's already in the wild.

## Related

- [Branding, LintPDF, and anonymous](../branding-and-anonymous)
- [Custom domains](../custom-domains)
- [Share links](../share-links) — branding immutability
