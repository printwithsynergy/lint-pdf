---
title: "Approvals"
description: "Send reports for review; collect verdicts with an audit trail."
section: "panels"
order: 11
---

# Approvals

**Path:** `/dashboard/approvals` · **Who:** Owner / Admin / Member

Turn a completed report into an approval request: email reviewers a share link, collect their verdicts (approve / reject / change-request), and get a PDF-backed audit trail of who said what when.

## What you see

- **Pending approvals** table: report name, requester, reviewers assigned, responses received, deadline, status.
- **Completed approvals** tab: full history with final verdict + timestamped reviewer comments.
- **New approval** button → report picker + reviewer-email list + optional deadline.

## Actions

| Action | API | Notes |
|---|---|---|
| Request approval | `POST /api/v1/approvals` | Sends an email with a share link to each reviewer. No LintPDF account required on the reviewer side. |
| Remind reviewers | `POST /api/v1/approvals/{id}/remind` | Resends the email to anyone who hasn't responded. |
| Cancel | `DELETE /api/v1/approvals/{id}` | Invalidates outstanding reviewer links. |
| Download audit trail | `GET /api/v1/approvals/{id}/pdf` | PDF with every verdict, comment, timestamp, and IP-address. |

## Gotchas

- **Reviewers don't need a LintPDF account.** The share link they get is a single-purpose token bound to their email — clicking it authenticates them to view and vote, but nothing else.
- **Deadlines are informational**, not enforcing. An approval doesn't auto-close when the deadline passes; you get a Celery-sent reminder, that's it.
- **Final verdict = majority of received votes** by default. The API supports configurable quorum rules per request.

## Related

- [Share links](../share-links) — the link format used for reviewers
- [Webhooks](./webhooks) — subscribe to `approval.chain.completed` to drive downstream workflows
