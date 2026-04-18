# scripts/ — end-to-end smoke tests against the live API

Two stdlib-only Python scripts that exercise the entire LintPDF API
surface against a throwaway tenant they provision themselves. Both
print every request inline (✓ / ✗ + status + payload snippet) and end
with a summary block listing every URL you can click into.

## Bootstrap (shared)

Both scripts:

1. `POST /api/v1/admin/tenants` to create a fresh `endpoint-suite-...` /
   `preflight-suite-...` tenant on the `scale` plan.
2. `POST /api/v1/admin/tenants/{id}/keys` to mint a tenant API key.
3. `PUT  /api/v1/admin/tenants/{id}/ai?ai_enabled=true` so AI routes
   don't 403.
4. `POST /api/v1/admin/tenants/{id}/ai/credits` and
   `.../files/packages` to grant generous quota.
5. Run their workload.
6. `PATCH /api/v1/admin/tenants/{id}/status {is_active: false}` at the
   end (skip via `LINTPDF_KEEP=1`).

## Required env

| Var | Required? | Default | Purpose |
|---|---|---|---|
| `LINTPDF_ADMIN_KEY` | ✅ | — | The engine's `X-Admin-Key`. The scripts cannot run without it. |
| `LINTPDF_API_BASE` | optional | `https://api.lintpdf.com` | Engine base URL. Set to `http://localhost:8000` for local. |
| `LINTPDF_APP_BASE` | optional | `https://app.lintpdf.com` | Used for "interactive viewer" URLs in the summary. |
| `LINTPDF_KEEP` | optional | unset | Set to `1` to leave the throwaway tenant active so you can click into the summary URLs. |

---

## `test_preflight.py` — preflight engine end-to-end

Prompts for a PDF path (Enter accepts the default 10-page sample at
`packages/web/public/lintpdf_preflight_test_final.pdf`), then exercises:

* **Variant 1** — vanilla preflight with `lintpdf-default`
* **Variant 2** — same PDF with AI enabled
  (`ai_enabled=true&ai_categories=brand_consistency,regulatory`)
* **Variant 3** — every `external_format` (one job per parser):
  pitstop_xml, callas_xml, callas_json, acrobat_xml, lintpdf_json
* **Reports** — one POST per format so each is independently visible:
  html, pdf, json, xml, annotated_pdf, annotated_pdf_markup
* **Viewer surface** — config, page list, on-demand capabilities
  (separations, fonts, images, tac), one annotation per kind (rect,
  circle, arrow, note, freehand), comment thread, verdict
  pass→fail→pass flip, every `?include=` slice of the universal
  `/state` digest
* **Share link** — mints a tenant-scoped HTML share token with
  `allow_annotations=true` + `require_visitor_email=true`, hits the
  public `/state` mirror with `X-Visitor-Email` header
* **Approval chain** — attaches a 1-step chain, decides via the
  approver access token (anonymous)
* **AI interpret** — fires `GET /captains-log/{job_id}/interpret`
  (expects 403 today; passes the test because 403 is in the
  declared `expect` tuple — Captain's Log requires Pro plan AI tier
  beyond the basic admin toggle)

**Run it:**

```sh
LINTPDF_ADMIN_KEY=... python3 scripts/test_preflight.py
```

**Output:**

```
SUMMARY  ✓ 126   ✗ 0   total 126
  tenant id       : a62820e8-...
  api key         : lpdf_Idh8xQQGFa_...
  primary job     : 2012a9b3-...
  /state digest   : https://api.lintpdf.com/api/v1/jobs/2012a9b3-.../state
  interactive     : https://app.lintpdf.com/dashboard/jobs/2012a9b3-.../viewer
  AI job          : 309f4086-...
  report URLs (every format):
    html                     https://reports.lintpdf.com/r/...
    pdf                      https://reports.lintpdf.com/r/...pdf
    json                     https://reports.lintpdf.com/r/...json
    xml                      https://reports.lintpdf.com/r/...xml
    annotated_pdf            https://reports.lintpdf.com/r/...pdf
  share-link token: KqteajkT...
  share-link page : https://api.lintpdf.com/r/...
  external-import jobs (one per parser):
    pitstop_xml    https://app.lintpdf.com/dashboard/jobs/.../viewer
    callas_xml     https://app.lintpdf.com/dashboard/jobs/.../viewer
    ...
```

---

## `test_endpoints.py` — everything else

Exhaustive non-preflight runner. Walks every route grouped by feature:

| Section | Endpoints exercised |
|---|---|
| Health + spec | `GET /health`, `GET /api/v1/status`, `GET /openapi.json`, `GET /openapi.tenant.json` |
| Check names | `GET /api/v1/check-names` |
| Webhooks | create/list/patch/delete + per-endpoint retry + retention overrides + test ping + delivery audit + replay |
| Approval templates | CRUD with the new `name`/`approvers[]` step shape |
| Custom endpoints | CRUD |
| Custom mappings | CRUD with a real `item_selector` + `fields` config from `docs/examples/custom-mapping-xml.json` |
| Branding | tenant defaults (mode toggle), brand profiles CRUD |
| Color config | gamut-conditions read, Pantone overrides bulk-write |
| AI | config, palette, dictionary, presets, credits, usage, usage trends |
| File packs | quota + packages list |
| Profiles | list, default profile read, custom profile create/delete |
| Usage | tenant usage |
| Admin | tenants list/get, keys, entitlements, AI grants, audit jobs, jobs, AI usage, trials config, tile-warming summary, plan PATCH, entitlements PATCH, status PATCH |

**Run it:**

```sh
LINTPDF_ADMIN_KEY=... python3 scripts/test_endpoints.py
```

**Output:**

```
SUMMARY  ✓ 68   ✗ 0   total 68
  tenant_id : 7750ccd1-...
  api_key   : lpdf_YCEWVeJ8...
  swagger   : https://lintpdf.com/swagger
  postman   : https://lintpdf.com/docs/postman
```

---

## How "every variant" is interpreted

For the preflight script, "every variant and every role" means:

* **Every preflight source**: native engine + every `external_format`.
* **Every report format**: each minted via a separate `POST /reports`
  call, so each is independently inspectable / cancellable / replayable.
* **Every viewer-surface mutation kind**: rect, circle, arrow, note,
  freehand annotations + comment threads + verdict pass/fail flip.
* **Every role on the same job**:
  - tenant API key (Bearer)
  - share-link visitor (anonymous + `X-Visitor-Email`)
  - approval-chain approver (anonymous + access token)
  - admin (`X-Admin-Key`) — used during bootstrap + cleanup

The endpoint script covers the same role coverage for every other
router (CRUD with the tenant key, admin operations with the admin key).

## When a test "fails" but the script still exits 0

Both scripts use a per-request `expect=(...)` tuple. A response is
counted as a pass when its status code is in that tuple, regardless of
2xx/4xx/5xx. The Captain's Log AI interpret endpoint, for example,
declares `expect=(200, 202, 402, 403, 404)` — a 403 means "AI
inspections aren't gated on for this tenant," which is the EXPECTED
behaviour for the bootstrap path that doesn't grant the per-job AI
inspection entitlement.

Genuine drift (e.g. a 422 from a malformed request body, a 500 from a
real server bug) still shows as a failure and pops up in the
"failures" block at the end.

## Cleanup

By default both scripts deactivate the throwaway tenant on the way
out. To leave it active so you can click the URLs in the summary:

```sh
LINTPDF_KEEP=1 LINTPDF_ADMIN_KEY=... python3 scripts/test_preflight.py
```

You can later deactivate manually:

```sh
curl -X PATCH https://api.lintpdf.com/api/v1/admin/tenants/$TENANT_ID/status \
  -H "X-Admin-Key: $LINTPDF_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```
