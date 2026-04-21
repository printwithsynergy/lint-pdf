---
title: "Seed the Print-With-Synergy demo tenant"
description: "Create or refresh the PWS demo tenant used in sales demos + end-to-end tests."
---

# Seed the Print-With-Synergy (PWS) demo tenant

PWS is the recurring demo tenant we use in sales calls and end-to-end verification. It's configured as an enterprise-plan whitelabel tenant with reports served from `reports.printwithsynergy.com` and app branding at `app.printwithsynergy.com`. Running the seed script is idempotent — it'll create the tenant if it doesn't exist or refresh it to known-good state if it does.

## Prerequisites

- Local checkout of the `lint-pdf` repo.
- Python 3.11+ with the engine's deps installed (`pip install -e packages/engine`).
- Admin API key for the target environment: export as `LINTPDF_ADMIN_KEY`.

## Steps

### 1. Run the seed

```sh
LINTPDF_ADMIN_KEY=$LINTPDF_ADMIN_API_KEY \
LINTPDF_API_URL=https://api.lintpdf.com \
  python3 packages/engine/scripts/seed_pws_demo.py
```

The script:

1. Finds or creates the tenant named `"Print With Synergy (Demo Customer)"` with plan=enterprise.
2. Mints a fresh API key for it (old keys are revoked).
3. Creates or updates the `"Print with Synergy"` BrandProfile with the PWS brand colours (`#0B5B63` accent, `#0E7A84` hover) and uploads the current logo asset.
4. Attaches `reports.printwithsynergy.com` + `app.printwithsynergy.com` as custom domains (already verified in prod).
5. Writes the credentials file at `scripts/.lintpdf-demo-credentials.env`:

   ```
   LINTPDF_DEMO_TENANT_ID=df520bc7-fc77-44cf-a275-c756fbbfb618
   LINTPDF_DEMO_API_KEY=lpdf_...
   ```

### 2. Verify with the preflight script

```sh
scripts/run-preflight.sh --tenant pws
```

Expected output:

- Submitted job_id
- `status=processing → complete ✓`
- Three hosted-report URLs under `reports.printwithsynergy.com/r/<token>`

See the [Run the preflight script end-to-end](./run-preflight-script) runbook for interpreting the output.

### 3. Hand credentials to the demo driver

If someone else is running the demo, share the tenant ID but **not the raw API key** — they should open `/dashboard/api-keys` as the PWS user and mint their own. The seed's generated key is for automation, not people.

## Troubleshooting

**"LINTPDF_ADMIN_KEY env var is required"**
You forgot the env export. The script exits early so no half-finished state exists.

**Brand profile logo upload returns 422**
The logo fixture at `packages/engine/scripts/fixtures/pws-logo.png` is missing or malformed. Re-check the file exists and is a valid PNG under 2 MB.

**Custom domains still show `verified=false` after the seed**
The seed only *attaches* the domains — it doesn't force the CNAME probe. Either wait for the 5-minute `probe_pending_custom_domains` beat or force a re-probe from the [Custom domains panel](../panels/custom-domains). For the known-good PWS domains, they're already verified in production — the seed is idempotent and preserves the `verified=true` state.

## Related

- [Custom domains panel](../panels/custom-domains)
- [Run the preflight script end-to-end](./run-preflight-script)
