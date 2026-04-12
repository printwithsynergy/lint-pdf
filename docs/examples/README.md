# LintPDF Examples

Copy-pasteable payloads and curl scripts for the LintPDF API. Everything here is referenced from the customer-facing docs at [docs.lintpdf.com](https://docs.lintpdf.com) — keep this directory in sync when parsers, submit fields, or mapping grammar change.

## Contents

### External preflight reports

Submit these with `POST /api/v1/jobs` alongside a PDF to import pre-computed findings into the LintPDF viewer without re-running the engine.

| File | `external_format` | What it is |
|---|---|---|
| [`pitstop-report.xml`](./pitstop-report.xml) | `pitstop_xml` | Enfocus PitStop Server preflight export — `<Hit type="Error">`-style schema. |
| [`callas-report.json`](./callas-report.json) | `callas_json` | callas pdfToolbox JSON export. |
| [`callas-report.xml`](./callas-report.xml) | `callas_xml` | callas pdfToolbox XML export. |
| [`acrobat-report.xml`](./acrobat-report.xml) | `acrobat_xml` | Adobe Acrobat Pro Preflight XML (namespace-prefixed). |
| [`lintpdf-native.json`](./lintpdf-native.json) | `lintpdf_json` | Canonical LintPDF v1 schema — see [schemas/import/v1.json](https://lintpdf.com/schemas/import/v1.json). |

All five samples describe the **same five findings on the same hypothetical `brochure.pdf`** — low-resolution image, unembedded font, RGB-in-CMYK warning, missing TrimBox, and a white-overprint advisory. Round-trip each through the engine and the normalized output is identical.

### Custom tenant import mappings

Ready-to-POST mapping configs for tenants whose preflight tool doesn't emit any of the five built-in formats above. Target endpoint: `POST /api/v1/tenant/import-mappings` (permission: `branding:manage`).

| File | Kind | Notes |
|---|---|---|
| [`custom-mapping-xml.json`](./custom-mapping-xml.json) | XML mapping | Namespace-insensitive PitStop-lite shape with attribute + nested-element selectors. Includes an inline `sample_payload` so the editor's preview works immediately. |
| [`custom-mapping-json.json`](./custom-mapping-json.json) | JSON mapping | Dotted-path + `[*]` array expansion for a nested microservice response. Uses a `SEV1`/`SEV2`/`SEV3` severity map. |

Once created, submissions reference the returned `id` via `mapping_id=<uuid>` on the submit form. `mapping_id` and `external_format` are mutually exclusive.

### Curl scripts

Runnable examples. Every script reads `LINTPDF_API_URL` (default `https://api.lintpdf.com`) and `LINTPDF_API_KEY` (required) from the environment.

| Script | Purpose |
|---|---|
| [`submit-external.sh`](./submit-external.sh) | PDF + external report (PitStop / callas / Acrobat / LintPDF-native). Auto-detects format if you omit the third argument. |
| [`submit-minimal.sh`](./submit-minimal.sh) | Viewer-only submit (`preflight_source=minimal`). Page geometry is ready immediately; deeper analyzers load on demand. |
| [`submit-with-mapping.sh`](./submit-with-mapping.sh) | Submit with a tenant-defined custom mapping by UUID. |
| [`submit-anonymous.sh`](./submit-anonymous.sh) | Force `brand=anonymous` on a single submission — strips both tenant and LintPDF branding. |

Example:

```bash
export LINTPDF_API_KEY=lpdf_live_...
chmod +x docs/examples/*.sh
docs/examples/submit-external.sh brochure.pdf docs/examples/pitstop-report.xml pitstop_xml
```

Every script returns a `202 Accepted` with a `job_id`. Poll `GET /api/v1/jobs/{job_id}` or subscribe to a webhook to pick up the finished job.

## Validating the LintPDF-native sample

The canonical native schema is published at [`https://lintpdf.com/schemas/import/v1.json`](https://lintpdf.com/schemas/import/v1.json). Validate `lintpdf-native.json` locally:

```bash
npx ajv-cli validate \
  --spec=draft2020 \
  -s docs/import-schema.json \
  -d docs/examples/lintpdf-native.json
```

## Smoke-testing against a local engine

If you're running the LintPDF engine locally via `packages/engine/docker-compose.yml`:

```bash
export LINTPDF_API_URL=http://localhost:8000
export LINTPDF_API_KEY=lpdf_live_dev_...

# 1. External PitStop import
docs/examples/submit-external.sh brochure.pdf docs/examples/pitstop-report.xml pitstop_xml

# 2. Viewer-only
docs/examples/submit-minimal.sh brochure.pdf

# 3. Anonymous output
docs/examples/submit-anonymous.sh brochure.pdf

# 4. Custom mapping (after POSTing the mapping and capturing its UUID)
MAPPING_ID=$(curl -s -X POST http://localhost:8000/api/v1/tenant/import-mappings \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @docs/examples/custom-mapping-xml.json | jq -r '.mapping.id')

docs/examples/submit-with-mapping.sh brochure.pdf my-acme-report.xml "${MAPPING_ID}"
```

Each submit returns `{"job_id": "...", "status": "pending"}`. External and minimal submissions typically complete in under three seconds.

## Also see

- [Preflight Modes](https://docs.lintpdf.com/docs/preflight-modes)
- [External Preflight Imports](https://docs.lintpdf.com/docs/external-imports)
- [LintPDF Native Import Schema](https://docs.lintpdf.com/docs/import-schema)
- [Custom Import Mappings](https://docs.lintpdf.com/docs/custom-mappings)
- [Branded, LintPDF-Default, and Anonymous Outputs](https://docs.lintpdf.com/docs/branding-and-anonymous)
