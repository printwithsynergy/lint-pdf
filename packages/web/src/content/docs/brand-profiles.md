---
title: "Brand Profiles"
description: "Named tenant branding configs — multiple per tenant, one default. Logo, colors, footer text, support email, optional custom domain."
section: "branding"
order: 22
---

# Brand Profiles

A **BrandProfile** is a named bundle of branding settings a tenant uses
to render reports, viewer chrome, hosted HTML, and share-link landing
pages. Each tenant can maintain **many** BrandProfiles — typically
one per client account or end-customer brand the tenant white-labels
for. Exactly one profile is marked the **tenant default** at any
time, but jobs and share-links can override that on a per-submission
basis.

This page covers the BrandProfile resource. For:

- The three-way **rendering decision** (branded / LintPDF / anonymous)
  and how it cascades, see [Branded, LintPDF, and Anonymous](/docs/branding-and-anonymous).
- Per-customer **color swatches and rich-black targets** used by
  preflight checks, see [Brand Specs](/docs/brand-specs). BrandSpec
  and BrandProfile are different primitives — BrandProfile controls
  rendering chrome, BrandSpec controls color-compliance checks.
- Attaching a **custom domain** to a BrandProfile (e.g.
  `reports.yourcustomer.com`), see [Custom Domains](/docs/custom-domains).

## What a BrandProfile carries

| Field | What it does |
|---|---|
| `name` | Display name shown in the dashboard picker. |
| `brand_name` | Renders in the report header and viewer chrome (defaults to `name`). |
| `logo_url` | URL to the logo image. PNG/SVG; transparent backgrounds preferred. |
| `primary_color`, `accent_color` | Hex colors used in the viewer chrome and report. |
| `footer_text`, `support_email` | Footer block on PDF reports + hosted HTML. |
| `custom_domain` | Optional. Attach a verified `reports.*` hostname; share links and reports render on it. |
| `app_custom_domain` | Optional. Attach a verified `app.*` hostname; the dashboard renders there for tenant users. |
| `is_archived` | Soft-delete. Archived profiles are no longer selectable as default. |

## How tenants pick which profile applies

The resolver is the same three-level chain documented in
[Branded, LintPDF, and Anonymous](/docs/branding-and-anonymous#resolution-chain),
applied to BrandProfile selection:

1. **Per-submission override** — `brand_profile_id_override` on the
   `Job`, or `branding_profile_id` set on the share link at issue time.
2. **Endpoint default** — workflow / endpoint can pin a default
   BrandProfile so submissions through that route always render
   under one customer's brand.
3. **Tenant default** — `tenants.default_brand_profile_id`. Fallback
   when neither override applies.
4. **No active profile** — fall through to LintPDF-default rendering
   (or anonymous if `unbranded_override=true`).

## Dashboard

`/dashboard/brand-specs` is **not** the right page — that lists Brand
Specs (color swatches). BrandProfiles live in
`/dashboard/admin/branding` (tenant-admin scope).

From there, tenant admins can:

- **Create** — new profile with name, logo, colors, footer copy,
  and optional custom domain.
- **Edit** — patch any subset of fields.
- **Set default** — promote one profile to the tenant-wide default;
  automatically demotes the previous default.
- **Archive / Restore** — soft-delete or revive.

## API

Full schemas are in the [API Reference — Branding section](/docs/api-reference#branding).
A short summary:

### List

```bash
curl https://api.lintpdf.com/api/v1/brand-profiles \
  -H "Authorization: Bearer lpdf_..."
```

### Create

```bash
curl -X POST https://api.lintpdf.com/api/v1/brand-profiles \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Foods",
    "brand_name": "Acme Foods",
    "logo_url": "https://cdn.acme.example/logo.svg",
    "primary_color": "#0a1f44",
    "accent_color": "#ff6f00",
    "footer_text": "Preflighted by Acme. Questions? prepress@acme.example",
    "support_email": "prepress@acme.example"
  }'
```

### Set as tenant default

```bash
curl -X POST https://api.lintpdf.com/api/v1/brand-profiles/{id}/set-default \
  -H "Authorization: Bearer lpdf_..."
```

### Override per job

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@artwork.pdf \
  -F profile_id=lintpdf-default \
  -F brand_profile_id_override={id}
```

## See also

- [Branded, LintPDF-Default, and Anonymous Outputs](/docs/branding-and-anonymous)
- [Brand Specs](/docs/brand-specs) — separate primitive for color-compliance checks
- [Custom Domains](/docs/custom-domains)
- [Share Links](/docs/share-links)
