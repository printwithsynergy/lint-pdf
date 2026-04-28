---
title: "Appearance panel"
description: "Platform-wide branding defaults for the LintPDF dashboard itself."
---

# Appearance

**Path:** `/dashboard/admin/appearance` · **Who:** Super admin · **Scope:** Global (edits `AppSettings` row — singleton)

Controls the branding of the LintPDF dashboard itself (login page, email templates, dashboard chrome). Not tenant branding — this is the *LintPDF* look that non-whitelabel tenants see.

## What you see

- Primary color + accent color pickers.
- Login page: background color, heading, subheading.
- Email templates: button color, dark-mode logo URL.
- Favicon + app name overrides.

## Actions

| Action | API | Notes |
|---|---|---|
| Save | `PATCH /api/lintpdf/admin/app-settings` | Writes to the singleton `AppSettings` row. All color values are hex strings. |

## Gotchas

- This panel exists mostly for Pixie Dust demos. In the LintPDF production deploy you usually want the defaults.
- Changes apply to **every** non-whitelabel tenant. Don't edit this to solve a single-customer request — use the [Tenants panel](./tenants) + `BrandProfile` overrides instead.
- Some Pixie Dust packages cache `AppSettings` in-memory for ~5 minutes; a hard reload of the dashboard picks up changes faster.

## Related

- [`getBranding()` in pixie-dust-auth](../admin-api) is the consumer.
