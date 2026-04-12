---
title: "SDKs & Code Examples"
description: "Runnable code samples covering engine submissions, external imports, viewer-only submissions, anonymous output, and custom import mappings."
section: "core"
order: 9
---

# SDKs & Code Examples

LintPDF is a standard REST API — use any HTTP client. The samples below cover the most-requested scenarios in Python, Node.js, and PHP/Laravel. Replace `lpdf_your_api_key` with a live or test key from the Dashboard.

## Python

```python
import httpx, time

client = httpx.Client(
    base_url="https://api.lintpdf.com",
    headers={"Authorization": "Bearer lpdf_your_api_key"},
    timeout=60.0,
)

# ── 1. Engine submission (default) ────────────────────────
with open("brochure.pdf", "rb") as f:
    job = client.post(
        "/api/v1/jobs",
        files={"file": f},
        data={"profile_id": "lintpdf-default"},
    ).json()

# Poll until complete
while True:
    job = client.get(f"/api/v1/jobs/{job['job_id']}").json()
    if job["status"] in ("complete", "failed"):
        break
    time.sleep(1.0)

print(f"Verdict: {job['status']}, findings: {job['summary']['total_findings']}")

# ── 2. External import — bring your own preflight ─────────
with open("brochure.pdf", "rb") as pdf, open("pitstop-report.xml", "rb") as rpt:
    job = client.post(
        "/api/v1/jobs",
        files={"file": pdf, "external_report": rpt},
        data={
            "preflight_source": "external",
            "external_format": "pitstop_xml",
            "profile_id": "lintpdf-default",
        },
    ).json()

# ── 3. Minimal (viewer-only) submission ───────────────────
with open("brochure.pdf", "rb") as f:
    job = client.post(
        "/api/v1/jobs",
        files={"file": f},
        data={"preflight_source": "minimal"},
    ).json()

# On-demand fill a capability (e.g. separations) after minimal submission
client.post(f"/api/v1/viewer/jobs/{job['job_id']}/capabilities/separations")

# ── 4. Anonymous output override ──────────────────────────
with open("brochure.pdf", "rb") as f:
    job = client.post(
        "/api/v1/jobs",
        files={"file": f},
        data={"brand": "anonymous", "profile_id": "lintpdf-default"},
    ).json()

# Mint an anonymous PDF share link
tokens = client.post(
    f"/api/v1/jobs/{job['job_id']}/reports",
    json={"formats": ["pdf"], "branding": "anonymous", "expiry_days": 14},
).json()
print("Anonymous share URL:", tokens["tokens"][0]["url"])

# ── 5. Create + use a custom import mapping ───────────────
mapping = client.post(
    "/api/v1/tenant/import-mappings",
    json={
        "name": "Internal QA XML",
        "format": "xml",
        "item_selector": "//Finding",
        "fields": {
            "severity": {"selector": "@level"},
            "message": {"selector": "Description"},
            "page_num": {"selector": "Page", "parse": "int"},
            "bbox": {"selector": "BBox", "format": "space_xywh"},
        },
        "severity_map": {"S": "error", "W": "warning", "N": "advisory"},
    },
).json()

with open("brochure.pdf", "rb") as pdf, open("internal-qa.xml", "rb") as rpt:
    job = client.post(
        "/api/v1/jobs",
        files={"file": pdf, "external_report": rpt},
        data={"preflight_source": "external", "mapping_id": mapping["id"]},
    ).json()
```

## Node.js

```javascript
import fs from "node:fs";

const API = "https://api.lintpdf.com";
const H = { Authorization: "Bearer lpdf_your_api_key" };

async function submit(form) {
  const r = await fetch(`${API}/api/v1/jobs`, { method: "POST", headers: H, body: form });
  if (!r.ok) throw new Error(`submit failed ${r.status}`);
  return r.json();
}

// ── 1. Engine submission ──────────────────────────────────
const engineForm = new FormData();
engineForm.append("file", new Blob([fs.readFileSync("brochure.pdf")]), "brochure.pdf");
engineForm.append("profile_id", "lintpdf-default");
const engineJob = await submit(engineForm);

// ── 2. External import ────────────────────────────────────
const extForm = new FormData();
extForm.append("file", new Blob([fs.readFileSync("brochure.pdf")]), "brochure.pdf");
extForm.append(
  "external_report",
  new Blob([fs.readFileSync("callas-report.json")]),
  "callas-report.json",
);
extForm.append("preflight_source", "external");
extForm.append("external_format", "callas_json");
const extJob = await submit(extForm);

// ── 3. Minimal submission ─────────────────────────────────
const minForm = new FormData();
minForm.append("file", new Blob([fs.readFileSync("brochure.pdf")]), "brochure.pdf");
minForm.append("preflight_source", "minimal");
const minJob = await submit(minForm);

// ── 4. Anonymous override ─────────────────────────────────
const anonForm = new FormData();
anonForm.append("file", new Blob([fs.readFileSync("brochure.pdf")]), "brochure.pdf");
anonForm.append("brand", "anonymous");
const anonJob = await submit(anonForm);

const tokens = await fetch(`${API}/api/v1/jobs/${anonJob.job_id}/reports`, {
  method: "POST",
  headers: { ...H, "Content-Type": "application/json" },
  body: JSON.stringify({ formats: ["pdf"], branding: "anonymous", expiry_days: 14 }),
}).then((r) => r.json());

console.log("Anonymous share URL:", tokens.tokens[0].url);

// ── 5. Custom mapping ─────────────────────────────────────
const mapping = await fetch(`${API}/api/v1/tenant/import-mappings`, {
  method: "POST",
  headers: { ...H, "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "Internal QA XML",
    format: "xml",
    item_selector: "//Finding",
    fields: {
      severity: { selector: "@level" },
      message: { selector: "Description" },
      page_num: { selector: "Page", parse: "int" },
      bbox: { selector: "BBox", format: "space_xywh" },
    },
    severity_map: { S: "error", W: "warning", N: "advisory" },
  }),
}).then((r) => r.json());

const mapForm = new FormData();
mapForm.append("file", new Blob([fs.readFileSync("brochure.pdf")]), "brochure.pdf");
mapForm.append(
  "external_report",
  new Blob([fs.readFileSync("internal-qa.xml")]),
  "internal-qa.xml",
);
mapForm.append("preflight_source", "external");
mapForm.append("mapping_id", mapping.id);
const mappedJob = await submit(mapForm);
```

## PHP / Laravel

```php
use Illuminate\Support\Facades\Http;

$api = 'https://api.lintpdf.com';
$headers = ['Authorization' => 'Bearer lpdf_your_api_key'];

// ── 1. Engine submission ────────────────────────────────────
$engine = Http::withHeaders($headers)
    ->attach('file', file_get_contents('brochure.pdf'), 'brochure.pdf')
    ->post("$api/api/v1/jobs", ['profile_id' => 'lintpdf-default'])
    ->json();

// ── 2. External import ──────────────────────────────────────
$external = Http::withHeaders($headers)
    ->attach('file', file_get_contents('brochure.pdf'), 'brochure.pdf')
    ->attach('external_report', file_get_contents('acrobat-preflight.xml'), 'acrobat.xml')
    ->post("$api/api/v1/jobs", [
        'preflight_source' => 'external',
        'external_format'  => 'acrobat_xml',
        'profile_id'       => 'lintpdf-default',
    ])
    ->json();

// ── 3. Minimal submission ───────────────────────────────────
$minimal = Http::withHeaders($headers)
    ->attach('file', file_get_contents('brochure.pdf'), 'brochure.pdf')
    ->post("$api/api/v1/jobs", ['preflight_source' => 'minimal'])
    ->json();

// ── 4. Anonymous override + anonymous share link ────────────
$anon = Http::withHeaders($headers)
    ->attach('file', file_get_contents('brochure.pdf'), 'brochure.pdf')
    ->post("$api/api/v1/jobs", ['brand' => 'anonymous'])
    ->json();

$tokens = Http::withHeaders($headers)
    ->post("$api/api/v1/jobs/{$anon['job_id']}/reports", [
        'formats'     => ['pdf'],
        'branding'    => 'anonymous',
        'expiry_days' => 14,
    ])
    ->json();

echo "Anonymous share URL: {$tokens['tokens'][0]['url']}\n";

// ── 5. Custom import mapping ────────────────────────────────
$mapping = Http::withHeaders($headers)
    ->post("$api/api/v1/tenant/import-mappings", [
        'name'           => 'Internal QA XML',
        'format'         => 'xml',
        'item_selector'  => '//Finding',
        'fields'         => [
            'severity'      => ['selector' => '@level'],
            'message'       => ['selector' => 'Description'],
            'page_num'      => ['selector' => 'Page', 'parse' => 'int'],
            'bbox'          => ['selector' => 'BBox', 'format' => 'space_xywh'],
        ],
        'severity_map'   => ['S' => 'error', 'W' => 'warning', 'N' => 'advisory'],
    ])
    ->json();

$mapped = Http::withHeaders($headers)
    ->attach('file', file_get_contents('brochure.pdf'), 'brochure.pdf')
    ->attach('external_report', file_get_contents('internal-qa.xml'), 'internal-qa.xml')
    ->post("$api/api/v1/jobs", [
        'preflight_source' => 'external',
        'mapping_id'       => $mapping['id'],
    ])
    ->json();
```

## Related

- [API Reference](/docs/api-reference)
- [External Preflight Imports](/docs/external-imports)
- [Custom Import Mappings](/docs/custom-mappings)
- [Branding & Anonymous Output](/docs/branding-and-anonymous)
