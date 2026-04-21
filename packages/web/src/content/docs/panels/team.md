---
title: "Team"
description: "Invite teammates, set roles, revoke access."
section: "panels"
order: 8
---

# Team

**Path:** `/dashboard/team` · **Who:** Owner / Admin

Invite teammates into this tenant, assign roles (Owner, Admin, Member), and revoke access when people leave.

## What you see

- Table: name, email, role, invited-at, last-active.
- **Invite teammate** button → email + role picker modal.
- Pending invites shown separately with resend / revoke buttons.

## Actions

| Action | API | Notes |
|---|---|---|
| Invite | `POST /api/v1/tenant/invites` | Sends a magic-link email; expires in 7 days. |
| Resend | `POST /api/v1/tenant/invites/{id}/resend` | |
| Revoke invite | `DELETE /api/v1/tenant/invites/{id}` | Before acceptance only. |
| Change role | `PATCH /api/v1/tenant/members/{id}` | Owner can promote/demote anyone; Admin can promote to Admin but not to Owner. |
| Remove member | `DELETE /api/v1/tenant/members/{id}` | Immediate; their session is invalidated. |

## Roles

| Role | Can do |
|---|---|
| Owner | Everything, including billing + ownership transfer + tenant deletion. Exactly one per tenant. |
| Admin | Everything except billing ownership and deleting the tenant. |
| Member | Read + submit preflights; cannot mint API keys, manage webhooks, or invite. |

## Gotchas

- **Ownership transfer is one-way and requires the current Owner's confirmation.** There is no "co-owner" role — one account holds the keys to billing.
- **Removing a member doesn't invalidate the jobs they submitted.** Their user ID stays on each job row for audit.
- **SSO** (if configured) auto-creates members at SAML/OIDC login; manual invites are only needed for users without IDP coverage.

## Related

- [Account](./account) — per-user profile + session settings
