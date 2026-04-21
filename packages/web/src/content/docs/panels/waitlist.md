---
title: "Waitlist"
description: "Collect pre-launch sign-ups for features that aren't GA yet."
section: "panels"
order: 16
---

# Waitlist

**Path:** `/dashboard/waitlist` · **Who:** Owner / Admin

Lightweight CRM for pre-launch features. Prospects sign up on your marketing page; their emails land here with a flag per feature. Use this to prioritise rollout and send "you're in the beta!" emails.

## What you see

- **Sign-ups** table: email, referral source, features interested in (comma-separated), signed-up-at.
- Filters: by feature, by date range, by country (IP-derived).
- Per-row: **Invite** — sends a templated email with an early-access link.

## Actions

| Action | API | Notes |
|---|---|---|
| Public sign-up | `POST /api/v1/waitlist/signup` | Unauthenticated — the marketing site posts here directly. |
| Filter / export | URL query + CSV | Useful for sales-team hand-off. |
| Send invite | `POST /api/v1/waitlist/{id}/invite` | Emails the templated "you're in" message with a unique signup URL that preserves the referral source. |
| Remove | `DELETE /api/v1/waitlist/{id}` | GDPR-style hard delete. |

## Gotchas

- **No identity verification.** Anyone can sign up with any email — filter spam before inviting in bulk.
- **Referral source** is populated from the UTM params on the marketing-page URL (and falls back to `document.referrer` if UTM is absent). Garbage in / garbage out.
- **Invited users aren't auto-tenants.** Clicking the invite link takes them to signup — they choose their own tenant name and plan.

## Related

- Marketing sign-up form lives at `/waitlist` on the public site.
