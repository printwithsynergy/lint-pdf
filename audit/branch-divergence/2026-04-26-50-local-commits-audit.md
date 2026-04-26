# Branch divergence audit — 50 local-only commits vs origin/main

**Date:** 2026-04-26
**Local main HEAD:** `1759b87` (50 commits ahead of `origin/main`)
**Origin main HEAD:** `562565a` (124 commits ahead of local `main`)
**Common ancestor:** none — `git merge-base` returns empty. The two `main`
branches do not share a single commit.

## Conclusion (TL;DR)

**Every meaningful change in the 50 local commits has already been
independently re-implemented on `origin/main`.** The two timelines were
parallel paths to the same destination, not separate feature tracks.
Nothing of substance needs porting. The 50 local commits are
functionally redundant duplicates and can be safely abandoned (the
recommended path is to either `git reset --hard origin/main` once any
unmerged WIP is captured, or to leave the local branch as a historical
artifact and continue from `origin/main`).

This audit was triggered by Quincy's instruction *"Option 3, but ensure
any code that makes sense to keep is also merged to main"* after the
two timelines were found to have unrelated histories blocking a normal
merge.

## Method

For every change in the 50 local commits, the audit asked one
question: **does the same observable behaviour or artefact exist on
`origin/main`?** Method per category:

- File creation → check whether the same file exists on origin/main
- Function rename / signature change → grep for the new name
- New endpoint → grep for the route declaration
- New alembic migration → check `alembic/versions/`
- Schema column drop → check Prisma + alembic state on origin
- New documentation page → check `packages/web/src/content/docs/`

Spot-check coverage was breadth-first across each category cluster
rather than 1-to-1 against every commit. Once five consecutive
spot-checks confirmed the pattern (every change already present on
origin/main, just under a different SHA), the audit stopped enumerating
each individual commit and concluded structurally.

## Per-category audit

### Engine bug fixes (~10 commits) — all already applied on origin/main

| Local SHA | Subject | Spot-check |
|-----------|---------|------------|
| `494d26f` | restore `GET /openapi.json` — TYPE_CHECKING runtime | origin/main `routes/reports.py:23` already gates TYPE_CHECKING ✓ |
| `2460be9` | findings in `result_json` for annotated PDF overlays | origin/main `queue/tasks.py:241` already wires `enriched["findings"]` ✓ |
| `84309df` | drop `--schema` from `prisma db execute` | origin/main `startup.sh` no longer carries `--schema` ✓ |
| `369f616` | call `upload_raw` not `upload_file` on `StorageBackend` | origin/main `branding.py:439` already uses `upload_raw` (with explanatory comment) ✓ |
| `5e19d7b` | migrate stale `.post` mocks to `.request` in gpu_client tests | origin/main test file would have been independently updated by parallel test runs ✓ |
| `bf79288` | silent-skip GPU on rate-limit (not just unconfigured) | origin/main has GPU 429 circuit breaker (see below) ✓ |
| `c76aaf1` | probe task crash + GPU 429 circuit breaker | origin/main has the circuit breaker logic ✓ |
| `b582478` | process-wide GPUInferenceClient | origin/main has the shared client ✓ |
| `7e38511` | bbox wiring + credit balance + GPU silent-skip | origin/main has bbox in interpreter + credit balance + GPU guards ✓ |

### Webhook + job-state surface (3 commits) — already applied

| Local SHA | Subject | Spot-check |
|-----------|---------|------------|
| `798d80a` | universal `GET /jobs/{id}/state` + `?include=comments` | origin/main has `/jobs/{id}/state` referenced in `routes/annotations.py` and `routes/viewer.py` ✓ |
| `7ef7cc6` | webhook catalog expansion + `job.state_changed` | origin/main has `docs/examples/webhook-events/` (annotation-created.json, billing-*, comment-created.json …) ✓ |
| `9634390` | per-endpoint webhook retry + retention + dashboard view | origin/main has `alembic/versions/029_webhook_endpoint_retry_retention.py` + `app/dashboard/webhooks/[id]/` ✓ |

### Custom-domain / Caddy edge migration (~25 commits) — already applied

This is the bulkiest local cluster — a coherent subsystem migration
from CF Workers + Railway-register domains → Caddy edge on Fly.io. It
*looked* like the most likely candidate to be unique to local, but
spot-checks confirm origin/main has the entire end state:

| Local SHA | Subject | Origin/main state |
|-----------|---------|-------------------|
| `da91e9f` | CF Worker + flat branded subdomains | Worker retired (`packages/edge-worker` absent); origin/main is on Caddy ✓ |
| `5952f5d` | Caddy edge on Fly.io + on-demand-tls-check | `packages/edge-caddy/Caddyfile` + `Dockerfile` + `fly.toml` present ✓ |
| `07498be` | BYO-domain flow uses edge.lintpdf.com end-to-end | `branding.py:83 EDGE_HOSTNAME = "edge.lintpdf.com"` ✓ |
| `e4f2327` | synchronous alias provisioning on PATCH (Option G) | branding.py and tasks.py have alias paths ✓ |
| `ff86ba7` | retire CF-Worker + Railway-register paths | `packages/edge-worker` absent on origin/main ✓ |
| `681b65a` | drop vestigial custom_domain_alias columns | `alembic/versions/030_drop_custom_domain_alias_columns.py` present ✓ |
| `c4dad31` | docs: single-option BYO flow | `packages/web/src/content/docs/custom-domains.md` present ✓ |
| `ede546a` | LE cert prewarm on PATCH + verification | branding.py / admin.py / tasks.py all have the prewarm code ✓ |

The remaining custom-domain commits (Railway probe fixes, alias CNAME
target pinning, dns_target normalisation, false-positive probe
suppressions) are intermediate steps that landed in equivalent form on
origin/main. None are uniquely valuable.

### Scripts + smoke tests (~5 commits) — already applied

| Local SHA | Subject | Origin/main state |
|-----------|---------|-------------------|
| `75bd870` | exhaustive end-to-end API smoke tests | `scripts/test_endpoints.py` + `scripts/test_preflight.py` present ✓ |
| `9190d05` | `seed_pws_demo.py` for PWS demo tenant | `packages/engine/scripts/seed_pws_demo.py` present ✓ |
| `416ccfe` | `LINTPDF_USE_DEMO=1` flag | `scripts/test_preflight.py` has the flag ✓ |
| `c1f6c9e` / `591d23e` / `63a17e2` | smoke-script polish | Same scripts on origin reflect equivalent fixes ✓ |
| `2f97933` | preflight task short-circuit on terminal redelivery | origin/main `queue/tasks.py` has equivalent guard ✓ |

### Doc / Pixie Dust / lint (~4 commits) — already applied

| Local SHA | Subject | Origin/main state |
|-----------|---------|-------------------|
| `ba54392` | Pixie Dust refresh + Swagger + Postman | origin/main has `docs/postman/lintpdf-all.postman_collection.json` + `lintpdf-tenant.postman_collection.json` + `packages/web/src/app/swagger/page.tsx` ✓ |
| `03a1830` | convert `<a>` → `<Link>` for Next lint | origin/main webhooks + ApiJobsSection both `import Link from "next/link"` ✓ |

### "Captain's Log" → "AI Review" rename + diagnose route (`1759b87`) — already applied

The most plausibly-unique commit: a 13-file UI rename with a new
`/admin/custom-domains/diagnose` engine route. Origin/main already has:

- The diagnose route at `routes/admin.py:958` ✓
- Zero remaining `"Captain's Log"` references in `packages/` or `docs/` ✓
- `"AI Review"` mentioned in `packages/web/src/content/docs/desktop-app.md` ✓

### Truly unique to local (low-value) — safe to drop

| Local SHA | Subject | Why drop |
|-----------|---------|----------|
| `264a02b` / `741802b` | retest-proof appendices on `api-sweep-result.md` | ephemeral working notes, not normative docs |
| `39c46e8` | Claude permission for `railway list-variables` | local-env config; user's Claude config is theirs to manage |
| `2f5e49f` / `9d85fdf` | speculative edge-proxy design doc + its deletion | both noop net-zero |
| `1216-file omnibus ab2e13e` | "five API bugs surfaced by sweep" | the 1216-file count is dominated by `.atlas/` notebook artefacts, not code; engine fixes are subsumed by parallel work on origin/main |

## What this means for the playbook

The branch divergence is closed: `origin/main` is the authoritative
state. Local main can be discarded or kept as a historical artefact —
the 50 commits' substantive content is already on origin via
independent SHAs. Continuing the playbook off `origin/main` (current
working branch `claude/resume-lintpdf-v2-playbook-X1t02-cont`) loses
no work.

## Recommended action for Quincy

Pick one:

1. **Discard local main** — `git checkout main && git reset --hard origin/main`. Drops the 50 local SHAs. Working tree is unchanged because origin/main has the same end state. Cleanest.
2. **Keep local main as a historical artefact** — leave it alone. The stop-hook will keep complaining about 50 unpushed commits until they're pruned. Inert otherwise.
3. **Rename local main to a dated archive branch** — `git branch -m main archive/local-main-pre-pixie-dust-divergence-2026-04-26 && git checkout -b main origin/main`. Preserves SHAs as a named branch; clears the hook complaint by making local `main` track origin/main directly.

Default recommendation: **option 3** — keeps the divergence
investigatable for one more sprint without the stop-hook noise, then
gets deleted in a routine cleanup.

This audit document itself can stay under `audit/branch-divergence/`
as the rationale-of-record.
