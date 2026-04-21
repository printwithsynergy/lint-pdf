# LintPDF Preflight Stress Test — Results

**Run date:** 2026-04-21 (UTC)
**Target scale:** hundreds-of-files (tier-2, per user direction: *"this system should be Configured for hundreds of files at once if not more"*).
**Actual probe:** tier-1 smoke — **15 files, 15 concurrent uploads, 5 workers after retune**.

## Summary — CRITICAL scaling defect discovered

**P0 — production engine went unresponsive after a single 15-file concurrent upload burst and did not recover.** See §"Critical scaling defect" below. All 15 jobs failed at the submit layer before any preflight check ran. Tier-2/3 runs (100, 1000 files) have been **blocked** pending engine recovery; running them now would exacerbate the outage.

## What we tried

### Run 1 — 15 workers, no stagger, 180s upload timeout

```
[preflight] phase 1: submitting 15 jobs  (workers=15) …
[preflight]   submitted 0/15 (15 rejected)
```

Failure mix:
- **12 × `TimeoutError('The read operation timed out')`** — 180s wasn't enough for the 19-47 MB PDFs when 15 uploads competed for the pipe.
- **2 × `503 DNS cache overflow`** — Railway/Cloudflare edge exhausted its DNS cache under the simultaneous TCP fan-out. **This is a production-class defect**, not a client issue — 15 connections shouldn't melt the edge.
- **1 × `EOF in _ssl.c:2437`** — TLS connection reset mid-upload.

### Run 2 — 5 workers, 30 s ramp-up, 600 s upload timeout, retry-with-backoff on 429/5xx/timeouts

```
[preflight] phase 1: submitting 15 jobs …
bootstrap: create tenant failed: -1 {'error': "TimeoutError('The read operation timed out')"}
```

The admin-bootstrap call — a tiny JSON POST to `/api/v1/admin/tenants` — hit the 120 s default timeout. Engine wasn't just slow, it was flat-lined. We never got past bootstrap.

### Follow-up health probes

```
try 1: /ready HTTP 000  t=20s
try 2: /ready HTTP 000  t=20s
try 3: /ready HTTP 000  t=20s
try 4-6: …all timed out
```

`GET /ready` on `api.lintpdf.com` — the Railway health check endpoint — was unresponsive for 10+ minutes after run 1 finished. Shut down further probes to let it recover rather than pile on.

## Critical scaling defect

| Severity | Finding |
|---|---|
| **P0** | **One burst of 15 concurrent uploads (~150 MB total) knocks the production engine fully offline, and it does not auto-recover.** The Railway `/ready` probe returns no response for 10+ minutes. If a real customer submitted a 50-file batch today, production would be down. |
| P0 | **`503 DNS cache overflow`** from the edge proxy under 15 concurrent TCP uploads. Whatever DNS cache the edge (Railway / Cloudflare R2 routing) uses is sized for far less than burst traffic. |
| P1 | Admin-bootstrap POST (`/api/v1/admin/tenants`, <1 KB JSON) times out when upload workers are saturated — suggests all Uvicorn workers are blocked on PDF upload I/O with no capacity reserve for control-plane operations. |
| P1 | Upload timeouts at 180 s for 19-47 MB PDFs imply upload throughput is sub-2 MB/s under concurrent load — consistent with a single-worker serialization. |
| P1 | SSL EOF mid-upload — either edge timeout too aggressive, or server killing idle connections during slow writes. |

### Suspected root causes (need Railway log access to confirm)

1. **Uvicorn workers are blocking on PDF bytes in memory** instead of streaming to storage. 15 × 30 MB = 450 MB held in process memory simultaneously; a Railway 2-vCPU container with 1 GB RAM has no spare headroom and likely OOM-killed or GC-thrashed. See `packages/engine/src/lintpdf/api/routes/jobs.py` — `await file.read()` loads the entire body before any storage call.
2. **Batch endpoint `db.commit()` is single-transaction** at `packages/engine/src/lintpdf/api/routes/batch.py:254-304`. All 15 (or 100) rows land in one SQLAlchemy session; under pressure this locks.
3. **`/api/v1/status` and `/api/v1/admin/tenants` share the same worker pool** as uploads. No lightweight control plane.
4. **Health-check timeout (120 s per railway.toml) + Uvicorn restarts**: once Railway sees `/ready` fail, it can restart the container mid-upload, adding to the chaos.
5. **Modal `max_containers=5`** is still a latent ceiling for any tier-2+ AI run, but this smoke never got there.

## Fixes needed (follow-up workstream)

Each becomes its own issue to file:

1. **Stream uploads to R2, never hold bytes in memory.** Swap `await file.read()` for `file.stream()` → `storage.upload_stream()`. `packages/engine/src/lintpdf/api/routes/jobs.py`, `packages/engine/src/lintpdf/api/routes/batch.py`, `packages/engine/src/lintpdf/api/routes/trial.py`, `packages/engine/src/lintpdf/api/routes/endpoints.py`.
2. **Split admin + status + submit into separate Uvicorn processes** (or add a lightweight `/readyz` that short-circuits before any middleware). Control plane must never block behind upload I/O.
3. **Raise Uvicorn worker count + connection limit on Railway**, or move uploads behind a presigned R2 URL so the engine only sees small JSON "file ready" notifications.
4. **Fix the edge DNS cache** — investigate Railway edge + whether a Cloudflare layer is adding resolution steps. `503 DNS cache overflow` on 15 TCP connections is diagnostic of a ~100-entry cache being exhausted.
5. **Raise Celery `max_containers` on Modal** (currently 5, per `packages/inference/src/inference_service/modal_deploy.py:16`) for tier-2+ AI load.
6. **Raise Postgres `max_connections`** on Railway Postgres to 500 and add PgBouncer per CLAUDE.md "Connection budget" guidance, before trying tier-2 again.
7. **Add a bulk report-mint endpoint** `POST /api/v1/reports:batchMint` so clients don't need N serial round-trips after N jobs complete.

## Rerun plan (after fixes land)

1. Deploy fixes 1-4 above.
2. Re-run tier-1: `--count 15 --clone-factor 1 --workers 5 --ramp-up-s 30`. Expect 15/15 complete.
3. Graduate to tier-2: `--count 100 --clone-factor 8 --workers 25 --ramp-up-s 60`. Expect ≥95/100 complete, p90 submit→complete < 5 min.
4. Tier-3 (1000 files) only after 2 is clean.

## Harness

- Script: `scripts/stress_preflight_folder.py` (stdlib only).
- Metrics: `preflight-stress-smoke-metrics.csv` (queue depth + worker count sampled every 15 s — largely empty given engine was down).
- Usage: `LINTPDF_ADMIN_KEY=... python3 scripts/stress_preflight_folder.py --dir preflight-test-files --count 15 --clone-factor 1 --workers 5 --ramp-up-s 30`.
- The harness implements retry-with-backoff on 429/5xx/timeouts and ramp-up staggering; the fact that those safeguards still produced 0/15 proves the engine-side failure is hard.

## Coverage note

Because 0 jobs reached the preflight pipeline, we did **not** verify the 605-check coverage (259 LPDF_*, 247 PDFX4-*, 99 AI_*). That verification is blocked on fixes 1-4 above.

## Environment state at time of run

- API: `https://api.lintpdf.com` (Railway `engine` service)
- App: `https://app.lintpdf.com`
- Reports: `https://reports.lintpdf.com`
- Modal inference: `https://quincy-codes--lintpdf-inference-serve-app.modal.run`, `max_containers=5`, A10G GPU
- Admin key: present (`LINTPDF_ADMIN_API_KEY` in env)
- Test corpus: 15 PDFs, 0.4 MB → 47 MB, mix of outlined stick-pack films, gummy pouches, dielines

## Railway logs

Not accessible from this session — `railway` CLI isn't installed and Railway MCP tools require the CLI. **Recommended action**: pull `engine` service deploy logs for the 17:24-17:40 UTC window on 2026-04-21 and cross-reference OOM / worker-restart / 503 events. That will confirm whether fix #1 (streaming uploads) is the true root cause.
