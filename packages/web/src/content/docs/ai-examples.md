---
title: "AI Code Examples"
description: "Examples showing how to enable AI inspections in job submissions across different languages."
section: "ai"
order: 14
---

# AI Code Examples

Examples showing how to enable AI inspections in job submissions across different languages.

## Python — FDA Food Label Check

```python
import httpx

client = httpx.Client(
    base_url="https://api.lintpdf.com",
    headers={"Authorization": "Bearer lpdf_your_api_key"},
)

# Submit with FDA AI preset
with open("nutrition-label.pdf", "rb") as f:
    resp = client.post(
        "/api/v1/submit",
        files={"file": f},
        data={
            "ruleset": "packaging",
            "ai_preset": "fda-food",
        },
    )
    job = resp.json()

print(f"Job ID: {job['id']}")

# Retrieve Report
report = client.get(f"/api/v1/reports/{job['id']}").json()

# Separate core and AI findings
engine_findings = [f for f in report["findings"] if f.get("source") != "ai"]
ai_findings = [f for f in report["findings"] if f.get("source") == "ai"]

print(f"Core engine: {len(engine_findings)} findings")
print(f"AI: {len(ai_findings)} findings")

for finding in ai_findings:
    print(f"  [{finding['severity']}] {finding['message']}")
    print(f"    Confidence: {finding.get('confidence', 'N/A')}")
    print(f"    Credits: {finding.get('credits_consumed', 'N/A')}")
```

## Node.js — GHS Chemical Label Check

```javascript
import fs from "node:fs";

const API_BASE = "https://api.lintpdf.com";
const headers = { Authorization: "Bearer lpdf_your_api_key" };

// Check credit balance first
const credits = await fetch(`${API_BASE}/api/v1/ai/credits`, { headers })
  .then((r) => r.json());

console.log("Credit balance:", credits.balance);

if (credits.balance < 20) {
  console.warn("Low credit balance — consider topping up");
}

// Submit with GHS preset
const form = new FormData();
form.append("file", new Blob([fs.readFileSync("chemical-label.pdf")]));
form.append("ruleset", "packaging");
form.append("ai_preset", "ghs-chemical");

const job = await fetch(`${API_BASE}/api/v1/submit`, {
  method: "POST",
  headers,
  body: form,
}).then((r) => r.json());

console.log("Job:", job.id, "AI inspections:", job.ai_inspections_requested);

// Retrieve Report
const report = await fetch(`${API_BASE}/api/v1/reports/${job.id}`, {
  headers,
}).then((r) => r.json());

// Filter by regulatory findings
const ghsFindings = report.findings.filter(
  (f) => f.category === "regulatory.ghs"
);

console.log("GHS findings:", ghsFindings.length);
ghsFindings.forEach((f) => console.log(`  [${f.severity}] ${f.message}`));
```

## PHP / Laravel — Brand Compliance Check

```php
use Illuminate\Support\Facades\Http;

$apiBase = 'https://api.lintpdf.com';
$headers = ['Authorization' => 'Bearer lpdf_your_api_key'];

// Submit with brand compliance preset
$response = Http::withHeaders($headers)
    ->attach('file', file_get_contents('packaging-artwork.pdf'), 'packaging-artwork.pdf')
    ->post("$apiBase/api/v1/submit", [
        'ruleset' => 'packaging',
        'ai_preset' => 'brand-compliance',
    ]);

$job = $response->json();

// Retrieve Report
$report = Http::withHeaders($headers)
    ->get("$apiBase/api/v1/reports/{$job['id']}")
    ->json();

// Filter AI findings by brand category
$brandFindings = collect($report['findings'])
    ->filter(fn($f) => str_starts_with($f['category'] ?? '', 'brand'))
    ->values();

foreach ($brandFindings as $finding) {
    echo "[{$finding['severity']}] {$finding['message']}\n";
    echo "  Confidence: {$finding['confidence']}\n";
}
```
