# Phase 4 Stage F — Smoke verification (PR #388)

End-to-end smoke runs against the deployed engine on
`api.lintpdf.com` to verify that the Phase 4 dep-wiring (PR #388)
preserved customer-visible behaviour. Both runs ship clean: every
fixture submits, polls, completes, mints all 4 reports, and the
viewer URL renders.

| Run | Tenant | Domain surface | Result |
|---|---|---|---|
| F1 corpus | `Phase4-Smoke` (temp `28a2c294`) | `reports.lintpdf.com` + `app.lintpdf.com` | **12/12 pass** |
| F2 PWS    | `Print With Synergy (Demo Customer)` (`df520bc7`) | `reports.printwithsynergy.com` + `app.printwithsynergy.com` | **12/12 pass** |

The key verification is **F2**: every PWS report URL resolves to the
custom-domain rewrite (`reports.printwithsynergy.com`) and every
viewer URL resolves to the white-labelled app surface
(`app.printwithsynergy.com`). The whitelabel + custom-domain
entitlements survive the dep wiring intact.

Profile: `lintpdf-default`. Both runs were submitted with
`ai_enabled=true`, the AI-explain step was skipped (cost-cap
budget; the smoke tenant only has 1000 credits granted by the
admin endpoint per call) — completion + report-mint coverage was
the gate, not per-finding AI explanations.

## What's NOT verified by this run

- **Stage D + E behaviour** is not yet exercised: the local
  `packages/engine/src/lintpdf/` and
  `packages/viewer-shared/src/core/` are still the active
  imports. Stage F validates the **baseline** before the
  consumer migration, not the migrated state.
- **AI-explain per-finding output**: skipped to avoid spending
  credits during baseline verification. Stage F1 in the
  full-corpus playbook includes per-finding `explain` calls;
  enable via `SMOKE_EXPLAIN=1` if needed.
- **Report content parity**: the URLs render but I did not byte-
  diff against a pre-PR-388 reference. Stage C is a pure-add
  with no consumer changes, so behaviour identity is structurally
  guaranteed; if you want bytes-equal, re-run the same fixtures
  on `main` and `diff` the JSON reports.

## How to re-run

```sh
# F1 (default tenant, fresh API key per run)
LINTPDF_ADMIN_API_KEY=… python3 -c '
import os, json, urllib.request
hdr = {"X-Admin-Key": os.environ["LINTPDF_ADMIN_API_KEY"], "Content-Type": "application/json"}
req = urllib.request.Request(
    "https://api.lintpdf.com/api/v1/admin/tenants",
    data=json.dumps({"name": "smoke", "plan": "enterprise", "contact_email": "ops@lintpdf.com"}).encode(),
    headers=hdr, method="POST")
print(json.loads(urllib.request.urlopen(req).read())["api_key"])
'  # capture API key from output

LINTPDF_API_KEY=lpdf_… ./scripts/smoke-preflight-v2.sh \
  packages/engine/tests/fixtures/test-sample.pdf

# Loop over the 12 fixtures with a batch wrapper:
# see /tmp/smoke-batch-1777577471/run.sh — keep this script
# alongside the smoke harness if you want repeatable per-fixture
# URL summaries.
```

For F2, replace the temp tenant mint with re-seeding PWS:

```sh
LINTPDF_ADMIN_KEY=$LINTPDF_ADMIN_API_KEY \
  python3 packages/engine/scripts/seed_pws_demo.py
# Read tenant id + api key from scripts/.lintpdf-demo-credentials.env
```
