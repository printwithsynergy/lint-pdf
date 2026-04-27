---
title: "Decisions Audit"
description: "Append-only audit of operator approve / waive / reject decisions on jobs and findings, with soft-revoke for audit replay."
section: "api"
order: 80
---

# Decisions Audit

Operator decisions on jobs and findings — **approve**, **reject**, **waive**, **suppress**, **annotate**, **escalate** — are stored in a tenant-scoped append-only audit table. Decisions never delete: revoking a decision stamps `revoked_at` / `revoked_by_user_id` / `revoked_reason` so audit replays stay correct after an operator changes their mind.

## Why append-only

Compliance regimes (FDA, GMP, ISO 13485) require an unchangeable history of who approved what and when. A delete-allowed model can't produce that history once a row is gone. The append-only + soft-revoke pattern keeps the original decision row intact and adds a revocation row, so a replay against any prior timestamp returns the correct verdict.

## Decision types

| `decision_type` | Meaning |
|---|---|
| `approve` | Operator approves the job / finding for downstream processing. |
| `reject` | Operator rejects — sender should re-submit. |
| `waive` | Acknowledge the finding + accept the risk; no rework needed. |
| `suppress` | Hide the finding from future renders without changing severity. |
| `annotate` | Attach a note/comment without changing approval status. |
| `escalate` | Bump to a higher reviewer in the approval chain. |

## Decision sources

Where the decision came from:

`dashboard | api | plugin | sdk | share_link | approval_chain | desktop | system | migration`

Stored on the row so audit reports can filter "what happened from the dashboard" vs "what auto-resolved via approval chain".

## Endpoints

### List decisions

```
GET /api/v1/jobs/{job_id}/decisions?include_revoked=false&limit=200
Authorization: Bearer lpdf_live_...
```

Newest first. Active by default — pass `include_revoked=true` to include revoked rows in the audit replay.

### Record a job-level decision

```
POST /api/v1/jobs/{job_id}/decisions
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{
  "decision_type": "approve",
  "decided_by_user_id": "u1",
  "source": "api",
  "notes": "Approved after operator review."
}
```

### Record a finding-level decision

```
POST /api/v1/jobs/{job_id}/findings/{finding_id}/decisions
```

Same payload, just a different path. Use the finding-scoped path to record decisions tied to specific issues.

### Revoke a decision (Q-2)

```
POST /api/v1/jobs/{job_id}/decisions/{decision_id}/revoke
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{ "revoked_by_user_id": "u2", "revoked_reason": "Mistake" }
```

Idempotent — re-revoking a revoked decision is a no-op (the original revoker wins).

## Effective decision on findings

The latest non-revoked decision per finding is also surfaced on each `FindingResponse` as `effective_decision` — a minimal projection so dashboards can render the verdict chip without a second fetch:

```json
{
  "decision_type": "waive",
  "decided_at": "2026-04-27T12:00:00Z",
  "decided_by_user_id": "u1"
}
```

Full row available via the list endpoint above.

## Where it shows up

- **Dashboard** — decision badges on each finding row plus a count next to PASS/FAIL.
- **Desktop + SDK + plugin + Postman + JSX docs** — all five ship the same endpoints with the same shape.
- **Reports** — finding cards on HTML / PDF / JSON / annotated PDF render the effective decision when present.
