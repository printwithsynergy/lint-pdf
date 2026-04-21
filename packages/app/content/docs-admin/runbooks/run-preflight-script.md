---
title: "Run the preflight script end-to-end"
description: "Submit a preflight against the default or pws tenant, poll to completion, print signed report URLs."
---

# Run the preflight script end-to-end

`scripts/run-preflight.sh` submits a preflight against the public LintPDF API, polls to completion, mints hosted-report tokens, and prints the signed `pdf` / `html` / `json` URLs. Use it as a smoke test after any engine deploy, or when you need fresh report URLs to include in a sales email.

## Prerequisites

- `bash`, `curl`, `jq` on `PATH`.
- **For `--tenant default`:** `LINTPDF_API_KEY` exported to a valid `lpdf_live_...` key.
- **For `--tenant pws`:** Run the [PWS onboarding runbook](./pws-onboarding) first; the script reads creds from `scripts/.lintpdf-demo-credentials.env`.

## Steps

### 1. Pick a tenant

```sh
# Default tenant — uses LINTPDF_API_KEY from env
LINTPDF_API_KEY=lpdf_live_... scripts/run-preflight.sh --tenant default

# PWS demo tenant — uses seeded creds
scripts/run-preflight.sh --tenant pws
```

### 2. Watch the output

```
== LintPDF preflight ==
tenant:       pws (Print With Synergy)
api_url:      https://api.lintpdf.com
profile_id:   lintpdf-default
file:         /tmp/tmp.abc123.pdf (342 bytes)

submitted: job_id=b334c69f-f3ea-4af4-83c1-84f8be96a4bd
  status=processing  …
  status=processing  …
  status=complete    ✓

== Generating hosted report tokens (pdf + html + json) ==
  pdf:	https://reports.printwithsynergy.com/r/6trOcThV...pdf
  html:	https://reports.printwithsynergy.com/r/x-Vjg9DItD...
  json:	https://reports.printwithsynergy.com/r/jBQwb-v3...json
```

The script exits non-zero if the job fails or the poll times out (default 180s).

### 3. Supply your own PDF

```sh
scripts/run-preflight.sh --tenant default --file path/to/your.pdf
```

Without `--file` the script generates a minimal one-page PDF inline — useful for pure "does the API still work?" checks without fishing around for a fixture.

### 4. Use a custom profile

```sh
scripts/run-preflight.sh --tenant default --profile-id my-custom-profile
```

The `profile_id` is either a system profile (`lintpdf-default`, etc. from the engine's profile registry) or a custom UUID from the tenant's own `CustomProfile` table. Invalid ids 404.

## What the script actually does

1. **Resolve credentials** — `LINTPDF_API_KEY` for default, `.lintpdf-demo-credentials.env` for pws.
2. **Submit** — `POST /api/v1/jobs` multipart with `file`, `profile_id`. Expects 202 + `{job_id}`.
3. **Poll** — `GET /api/v1/jobs/{id}` every 2s, up to 180s. Terminal statuses: `complete`, `completed`, `failed`.
4. **Generate reports** — `POST /api/v1/jobs/{id}/reports` with `{"formats": ["pdf", "html", "json"]}`. Completed jobs don't mint tokens automatically; this call does.
5. **Print URLs** — reads `reports` dict from the response and emits format → URL on stdout.

## Troubleshooting

**`ERROR: jq is required`**
Install: `brew install jq` (mac) or `apt-get install -y jq` (ubuntu).

**Poll timed out at `status=processing`**
Job is still running. Bump the timeout: `--poll-timeout 600`. If it still times out, check the Worker deploy logs on Railway for the job id — the Celery task may have died.

**Report URLs all point at `reports.lintpdf.com` when running with `--tenant pws`**
The PWS tenant's whitelabel custom domain isn't verified. Run the PWS onboarding script again and confirm `brand_custom_domain_verified=true`.

**Exit code 2 ("job failed")**
The engine rejected the PDF. Read the `error_message` printed alongside the failure; common causes are corrupted PDFs, encrypted/password-protected PDFs, or the tenant being out of AI credits (when running with an AI-enabled profile).

## Related

- [Seed the PWS demo tenant](./pws-onboarding)
- [Admin APIs + Swagger](../admin-api)
