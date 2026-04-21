---
title: "Account"
description: "Per-user profile, password, MFA, active sessions."
section: "panels"
order: 9
---

# Account

**Path:** `/dashboard/account` · **Who:** Any signed-in user

Your personal profile and security settings. Tenant-level settings live under [Team](./team) (for membership) and [Billing](./billing) (for payment).

## What you see

- **Profile** — name, avatar, email (with "verify" flow if unverified), timezone for UI timestamps.
- **Password** — change password; shows "last changed" date.
- **Multi-factor auth** — TOTP setup + recovery codes.
- **Active sessions** — every browser currently authenticated with this account; revoke individually or sign out everywhere.
- **Connected identities** — OAuth / SSO providers linked to this account.

## Actions

| Action | API | Notes |
|---|---|---|
| Update profile | `PATCH /api/v1/me` | Name, avatar, timezone. Email requires a verify flow. |
| Change password | `POST /api/v1/me/password` | Old password required. Invalidates every session except the current one. |
| Enable MFA | `POST /api/v1/me/mfa/enroll` | Shows QR + recovery codes. Save the codes — if you lose the TOTP device without them, support can't get you back in. |
| Revoke session | `DELETE /api/v1/me/sessions/{id}` | That device is signed out immediately. |
| Sign out everywhere | `DELETE /api/v1/me/sessions` | Revokes every session including the current one. |

## Gotchas

- **Recovery codes are single-use.** Save all of them (password manager / printed copy); regenerate if any are exposed.
- **Timezone is display-only.** Server-side timestamps are always UTC; the UI converts.
- **Email changes require re-verification** — you'll keep access during the verify window.

## Related

- [Team](./team) — for managing *other people's* roles
