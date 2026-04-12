---
title: "Authentication"
description: "How to authenticate with the LintPDF API using Bearer tokens, and the permission model for tenant-admin operations."
section: "core"
order: 2
---

# Authentication

Include your API Key in the `Authorization` header as a Bearer token:

```
Authorization: Bearer lpdf_live_...
```

Production keys are prefixed `lpdf_live_`; sandbox keys are `lpdf_test_`. Both behave identically against the same API surface — sandbox traffic is billed separately and is rate-limited at a lower ceiling.

> **Keep your API Key secret.** Never expose it in client-side code, public repositories, or browser requests. Use environment variables and server-side calls only.

## Permissions

Most endpoints require only a valid API key. Tenant-admin operations require additional permission scopes, granted to the key's owner in the Dashboard.

| Permission | Covers |
|---|---|
| `branding:manage` | Custom import mappings (CRUD + preview), branding defaults, BrandProfile CRUD, on-demand viewer capability fill-in, custom domains (reports + app). |
| `webhooks:manage` | Webhook registration, update, delete, and test deliveries. |
| `tokens:manage` | API key issuance and revocation for the tenant. |
| `billing:read` | Usage headers, invoice retrieval, overage history. |

If a call is made without the required permission, LintPDF returns `403 Forbidden` with a `permission_required` error code naming the missing scope.

## Rate limits

Every authenticated response carries `X-RateLimit-*` headers. The limit is a rolling per-minute window, shared across all keys owned by the tenant. See the [API Reference — Authentication & rate limits](/docs/api-reference) for the full header list and recommended back-off pattern.

## Related

- [API Reference](/docs/api-reference)
- [Branding & Anonymous Output](/docs/branding-and-anonymous) — uses `branding:manage`
- [Custom Import Mappings](/docs/custom-mappings) — uses `branding:manage`
