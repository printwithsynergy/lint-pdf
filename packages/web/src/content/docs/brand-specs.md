---
title: "Brand Specs"
description: "Per-customer colour specifications with three-level resolution: tenant default, endpoint default, per-job override."
section: "configuration"
order: 14
---

# Brand Specs

> **What happened to "AI Brand config" / Color Palette settings?**
> The single-tenant `Settings > AI Brand > Color Palette` page is
> gone. It was replaced by the multi-customer Brand Specs primitive
> documented here. Existing palettes were auto-migrated to a
> `Default palette (migrated)` BrandSpec on Alembic 041; the old
> column is read as a fallback only.

A **Brand Spec** is a named colour specification a tenant maintains per end-customer — typically one per brand owner the tenant preflights for (e.g. "Coca-Cola", "PepsiCo", "Nestlé"). Each spec carries:

- **Swatches** — one row per approved colour, with a display name, canonical value (hex, named CSS colour, or explicit `rgb()` / `cmyk()`), optional Pantone reference, and optional notes.
- **Rich-black composition** (optional) — a target `{c, m, y, k}` percentage that print-production advisories can measure the document's rich black against, in place of the profile's default rich-black reference.
- **Flags** — `is_default` (exactly one non-archived spec per tenant may carry this; see below) and `is_archived` (soft-delete).

Brand Specs replace the single `tenant_ai_configs.brand_palette` column so tenants with multiple customers can keep each palette separate instead of toggling a shared list every submission.

## Resolution chain

When a job runs, the engine walks a three-level chain to pick the spec that applies:

1. **Per-submission override** — the `brand_spec_id` form field on `POST /api/v1/jobs`. Wins over everything else.
2. **Endpoint default** — the `default_brand_spec_id` on the custom endpoint the job was submitted through (`POST /api/v1/endpoints/{slug}/submit`). Wins when the submit call didn't supply an explicit spec.
3. **Tenant default** — the spec whose `is_default=true` (and `is_archived=false`) row the tenant maintains. Used as the catch-all when neither override applies.
4. **No spec** — when the chain dead-ends, strict colour advisories (e.g. `LPDF_COLOR_021`, `LPDF_STROKE_007`, and the pure-K gate on `LPDF_ADV_005`) stay suppressed. This is deliberate: without a palette there's no way to tell whether a pure-K fill or multi-ink stroke is intentional, and the rules would generate thousands of "might be wrong, can't tell" findings per page.

Archived specs never satisfy the tenant-default hop, so tenants can retire a spec without having to first remove every endpoint and job reference. Historical jobs that captured the spec at submit time keep resolving to it regardless of archive state.

## Dashboard

`/dashboard/brand-specs` lists every non-archived spec for the current tenant. From here you can:

- **Create** — new spec with name, customer, description, swatches, optional rich-black, and the "use as tenant default" checkbox. Setting `is_default` automatically demotes the previous default.
- **Edit** — patch any subset of fields.
- **Archive / Restore** — soft-delete or revive.

## API

### Create

```bash
curl -X POST https://api.lintpdf.com/api/v1/brand-specs \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Coca-Cola",
    "customer_name": "Coca-Cola Co.",
    "description": "Global soft-drink brand palette.",
    "colors": [
      {"name": "Coke Red", "value": "#F40009", "pantone": "PMS 185 C"},
      {"name": "White", "value": "#FFFFFF"}
    ],
    "rich_black_spec": {"c": 60, "m": 50, "y": 50, "k": 100},
    "is_default": true
  }'
```

### List

```bash
curl https://api.lintpdf.com/api/v1/brand-specs \
  -H "Authorization: Bearer lpdf_..."
```

Add `?include_archived=true` to include soft-deleted rows.

### Patch / archive / restore

- `PATCH /api/v1/brand-specs/{id}` — any subset of fields. Setting `is_default=true` demotes the previous default.
- `DELETE /api/v1/brand-specs/{id}` — soft-delete (sets `is_archived=true`, clears `is_default`).
- `POST /api/v1/brand-specs/{id}/restore` — un-archive.

### Bind to a custom endpoint

Creating or updating a custom endpoint accepts `default_brand_spec_id`:

```bash
curl -X POST https://api.lintpdf.com/api/v1/endpoints \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "coke-packaging",
    "profile_id": "gwg-2022-packaging",
    "default_brand_spec_id": "00000000-1111-2222-3333-444444444444"
  }'
```

To clear an endpoint's bound spec, `PATCH` with `"default_brand_spec_id": "null"` (the literal string). Omitting the field leaves it unchanged.

### Per-submission override

Pass `brand_spec_id` as a multipart form field on `POST /api/v1/jobs`:

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@artwork.pdf \
  -F profile_id=gwg-2022-packaging \
  -F brand_spec_id=00000000-1111-2222-3333-444444444444
```

Invalid or foreign spec IDs (i.e. belonging to a different tenant, or archived) fail fast with 404 before the upload is committed.

## Relationship to legacy `brand_palette`

The `tenant_ai_configs.brand_palette` JSONB column is the predecessor of this system and is still read as a fallback for tenants whose rows haven't been migrated yet. The Alembic 041 migration seeds a `Default palette (migrated)` BrandSpec row for every tenant with a non-empty `brand_palette`, marks it `is_default=true`, and the resolver then prefers that row over the legacy column. A follow-up migration will drop the legacy column once every tenant's rows have been captured as BrandSpecs.
