---
title: "SDKs & Code Examples"
description: "Code examples for integrating with the LintPDF API in Python, Node.js, and PHP/Laravel."
section: "core"
order: 9
---

# SDKs & Code Examples

LintPDF is a standard REST API — use any HTTP client. Here are examples in popular languages.

## Python

```python
import httpx

client = httpx.Client(
    base_url="https://api.lintpdf.com",
    headers={"Authorization": "Bearer lpdf_your_api_key"},
)

# Submit a PDF
with open("brochure.pdf", "rb") as f:
    resp = client.post("/api/v1/submit", files={"file": f}, data={"ruleset": "gwg-sheetfed"})
    job = resp.json()

print(f"Job ID: {job['id']}, Status: {job['status']}")

# Retrieve the Report
report = client.get(f"/api/v1/reports/{job['id']}").json()

if report["verdict"] == "pass":
    print("Pass!")
else:
    print(f"Error: {report['summary']['error']} Error findings")
    for finding in report["findings"]:
        print(f"  [{finding['severity']}] {finding['message']} (page {finding['page']})")
```

## Node.js

```javascript
import fs from "node:fs";

const API_BASE = "https://api.lintpdf.com";
const headers = { Authorization: "Bearer lpdf_your_api_key" };

// Submit a PDF
const form = new FormData();
form.append("file", new Blob([fs.readFileSync("brochure.pdf")]));
form.append("ruleset", "gwg-sheetfed");

const job = await fetch(`${API_BASE}/api/v1/submit`, {
  method: "POST",
  headers,
  body: form,
}).then((r) => r.json());

console.log("Job ID:", job.id, "Status:", job.status);

// Retrieve the Report
const report = await fetch(`${API_BASE}/api/v1/reports/${job.id}`, {
  headers,
}).then((r) => r.json());

console.log("Verdict:", report.verdict);
```

## PHP / Laravel

```php
use Illuminate\Support\Facades\Http;

$apiBase = 'https://api.lintpdf.com';
$headers = ['Authorization' => 'Bearer lpdf_your_api_key'];

// Submit a PDF
$response = Http::withHeaders($headers)
    ->attach('file', file_get_contents('brochure.pdf'), 'brochure.pdf')
    ->post("$apiBase/api/v1/submit", [
        'ruleset' => 'gwg-sheetfed',
    ]);

$job = $response->json();

// Retrieve the Report
$report = Http::withHeaders($headers)
    ->get("$apiBase/api/v1/reports/{$job['id']}")
    ->json();

if ($report['verdict'] === 'pass') {
    echo "Pass!";
} else {
    echo "Error: " . $report['summary']['error'] . " Error findings";
}
```
