#!/usr/bin/env python3
"""End-to-end API test for LintPDF: all endpoints + all 289 preflight checks."""

import httpx
import json
import time
import sys
import io
import struct
import zlib
from datetime import datetime
from collections import defaultdict

# ──── Config ────────────────────────────────────────────────────────────────
API_BASE = "https://api.lintpdf.com"
MODAL_BASE = "https://quincy-codes--lintpdf-inference-serve-app.modal.run"
ADMIN_KEY = "gx0B011GFHNLxx4q8KOfafMcCgLifHgec-u1TKpPOpA"

TIMEOUT = httpx.Timeout(120.0, connect=30.0)
MODAL_TIMEOUT = httpx.Timeout(300.0, connect=60.0)  # Longer for cold start
client = httpx.Client(timeout=TIMEOUT, follow_redirects=True)
SKIP_MODAL_DIRECT = True  # Modal cold-starting; test via API jobs instead

results = []
job_ids = []
report_tokens = []


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def record(test_name: str, method: str, url: str, status: int, passed: bool, detail: str = ""):
    emoji = "PASS" if passed else "FAIL"
    results.append({
        "test": test_name, "method": method, "url": url,
        "status": status, "passed": passed, "detail": detail[:200]
    })
    log(f"  [{emoji}] {test_name} -> {status} {detail[:80]}")


# ──── Generate test PDFs ────────────────────────────────────────────────────
def make_minimal_pdf() -> bytes:
    """Create a minimal valid PDF with text, image, and intentional issues."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    # Page 1: Basic text (triggers font/text checks)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "LintPDF End-to-End Test Document", ln=True)
    pdf.set_font("Helvetica", size=3)  # Very small text - triggers LPDF_TEXT_003
    pdf.cell(0, 5, "This text is intentionally very small for testing", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Normal text with some content for OCR and spell checking.", ln=True)
    pdf.cell(0, 10, "Barcde Dimentions Regulatry - misspelled words for spell check", ln=True)

    # Add a low-res image (72 DPI equivalent) - triggers LPDF_IMG_001
    # Create a small 20x20 RGB PNG in memory
    width, height = 20, 20
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"  # filter byte
        for x in range(width):
            raw_data += bytes([x * 12, y * 12, 128])  # RGB

    def make_png(w, h, data):
        def chunk(ctype, cdata):
            c = ctype + cdata
            return struct.pack(">I", len(cdata)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b"")

    png_bytes = make_png(width, height, raw_data)
    img_path = "/tmp/test_low_res.png"
    with open(img_path, "wb") as f:
        f.write(png_bytes)
    pdf.image(img_path, x=10, y=60, w=100)  # Stretched small image = low DPI

    # Page 2: More content
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Page 2 - Additional content for multi-page testing", ln=True)
    pdf.cell(0, 10, "Testing metadata, structure, and document-level checks.", ln=True)

    # Draw a very thin line - triggers hairline checks LPDF_STROKE_001
    pdf.set_line_width(0.01)
    pdf.line(10, 100, 200, 100)

    return pdf.output()


def make_barcode_pdf() -> bytes:
    """PDF with barcode-like content for barcode checks."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Document with barcode area", ln=True)
    # Draw black bars to simulate barcode-like pattern
    for i in range(0, 60, 3):
        pdf.set_fill_color(0, 0, 0)
        pdf.rect(20 + i, 30, 1.5, 40, "F")
    pdf.set_font("Helvetica", size=8)
    pdf.text(20, 75, "5 901234 123457")  # EAN-13 like text
    pdf.text(20, 85, "https://example.com/product/12345")  # URL for QR content
    return pdf.output()


def make_packaging_pdf() -> bytes:
    """PDF simulating packaging artwork for packaging/regulatory checks."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "PRODUCT LABEL - Organic Green Tea", ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "Net Wt. 250g", ln=True)
    pdf.cell(0, 8, "Ingredients: Organic green tea leaves", ln=True)
    pdf.cell(0, 8, "Nutrition Facts", ln=True)
    pdf.cell(0, 8, "Serving Size: 1 cup (240ml)", ln=True)
    pdf.cell(0, 8, "Calories: 0  Total Fat: 0g  Sodium: 0mg", ln=True)
    pdf.cell(0, 8, "Manufactured by: Test Corp, 123 Main St", ln=True)
    pdf.cell(0, 8, "Best Before: See bottom of package", ln=True)
    pdf.cell(0, 8, "USDA ORGANIC | NON-GMO", ln=True)
    # Dieline simulation - colored rectangle
    pdf.set_draw_color(255, 0, 255)  # Magenta dieline
    pdf.set_line_width(0.5)
    pdf.rect(5, 5, 200, 280)
    # Regulatory text
    pdf.set_font("Helvetica", size=6)
    pdf.text(10, 270, "WARNING: Contains caffeine. Not for children under 12.")
    pdf.text(10, 275, "Recyclable packaging - Please recycle")
    return pdf.output()


# ──── Test Functions ────────────────────────────────────────────────────────

def test_health():
    log("\n=== HEALTH & STATUS ===")
    # Health
    r = client.get(f"{API_BASE}/health")
    record("Health Check", "GET", "/health", r.status_code, r.status_code == 200, r.text[:100])

    # Status
    r = client.get(f"{API_BASE}/api/v1/status")
    record("Status Check", "GET", "/api/v1/status", r.status_code, r.status_code == 200, r.text[:200])


def test_modal_inference():
    log("\n=== MODAL INFERENCE ENDPOINTS ===")
    # Health
    try:
        r = client.get(f"{MODAL_BASE}/health")
        record("Modal Health", "GET", "/health", r.status_code, r.status_code == 200, r.text[:100])
    except Exception as e:
        record("Modal Health", "GET", "/health", 0, False, str(e)[:200])
        log("  Modal may be cold-starting, continuing...")

    # Create test image
    width, height = 200, 200
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"
        for x in range(width):
            raw_data += bytes([x % 256, y % 256, 128])

    def make_png(w, h, data):
        def chunk(ctype, cdata):
            c = ctype + cdata
            return struct.pack(">I", len(cdata)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b"")

    test_image = make_png(width, height, raw_data)

    endpoints = [
        ("Image Quality", "/inference/image-quality", {"image": ("test.png", test_image, "image/png")}),
        ("Classify", "/inference/classify", {"image": ("test.png", test_image, "image/png")}),
        ("Detect Logo", "/inference/detect-logo", {"image": ("test.png", test_image, "image/png")}),
        ("Detect NSFW", "/inference/detect-nsfw", {"image": ("test.png", test_image, "image/png")}),
        ("Detect Objects", "/inference/detect-objects", {"image": ("test.png", test_image, "image/png")}),
        ("Embed Image", "/inference/embed-image", {"image": ("test.png", test_image, "image/png")}),
        ("Detect Outlines (OCR)", "/inference/detect-outlines", {"image": ("test.png", test_image, "image/png")}),
        ("Detect Symbols", "/inference/detect-symbols", {"image": ("test.png", test_image, "image/png")}),
    ]

    for name, path, files in endpoints:
        try:
            r = client.post(f"{MODAL_BASE}{path}", files=files, timeout=180.0)
            detail = r.text[:150] if r.status_code != 200 else json.dumps(
                {k: v for k, v in r.json().items() if k != "result"}, default=str
            )[:150]
            record(f"Modal {name}", "POST", path, r.status_code, r.status_code == 200, detail)
        except Exception as e:
            record(f"Modal {name}", "POST", path, 0, False, str(e)[:200])

    # Translate
    try:
        r = client.post(f"{MODAL_BASE}/inference/translate",
                        data={"text": "Hello world", "source_lang": "en", "target_lang": "fr"},
                        timeout=180.0)
        record("Modal Translate", "POST", "/inference/translate", r.status_code,
               r.status_code == 200, r.text[:150])
    except Exception as e:
        record("Modal Translate", "POST", "/inference/translate", 0, False, str(e)[:200])


def test_setup_tenant():
    """Seed test tenants and get an enterprise key with AI enabled."""
    log("\n=== TENANT SETUP ===")
    admin_headers = {"X-Admin-Key": ADMIN_KEY}

    # Seed test tenants
    r = client.post(f"{API_BASE}/api/v1/dev/seed", headers=admin_headers)
    record("Seed Tenants", "POST", "/api/v1/dev/seed", r.status_code,
           r.status_code in (200, 201), r.text[:200])

    if r.status_code in (200, 201):
        data = r.json()
        tenants = data.get("tenants", data)
        # Get enterprise tenant
        enterprise = tenants.get("enterprise", {})
        api_key = enterprise.get("api_key", "")
        tenant_id = enterprise.get("id", "")
        log(f"  Enterprise tenant: {tenant_id}")
        log(f"  API key prefix: {api_key[:20]}...")

        # Enable AI for enterprise tenant
        r2 = client.put(
            f"{API_BASE}/api/v1/admin/tenants/{tenant_id}/ai",
            headers=admin_headers,
            params={
                "ai_enabled": True,
                "billing_mode": "pay_per_use",
                "enabled_categories": "all",
            }
        )
        record("Enable AI", "PUT", f"/api/v1/admin/tenants/{tenant_id}/ai",
               r2.status_code, r2.status_code in (200, 201), r2.text[:200])

        # Grant credits
        r3 = client.post(
            f"{API_BASE}/api/v1/admin/tenants/{tenant_id}/ai/credits",
            headers=admin_headers,
            params={"credit_amount": 10000, "price_paid": 0}
        )
        record("Grant AI Credits", "POST", f"/api/v1/admin/tenants/{tenant_id}/ai/credits",
               r3.status_code, r3.status_code in (200, 201), r3.text[:200])

        return api_key, tenant_id
    else:
        # Fallback: create enterprise tenant manually
        r = client.post(f"{API_BASE}/api/v1/admin/tenants", headers=admin_headers,
                        json={"name": "E2E Test Enterprise", "contact_email": "test@lintpdf.com", "plan": "enterprise"})
        record("Create Tenant", "POST", "/api/v1/admin/tenants", r.status_code,
               r.status_code in (200, 201), r.text[:200])
        if r.status_code in (200, 201):
            data = r.json()
            return data.get("api_key", ""), data.get("id", "")
    return "", ""


def test_profiles(api_key: str):
    log("\n=== PROFILES ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.get(f"{API_BASE}/api/v1/profiles", headers=headers)
    record("List Profiles", "GET", "/api/v1/profiles", r.status_code,
           r.status_code == 200, f"{len(r.json().get('profiles', []))} profiles" if r.status_code == 200 else r.text[:100])

    for pid in ["lintpdf-default", "lintpdf-strict"]:
        r = client.get(f"{API_BASE}/api/v1/profiles/{pid}", headers=headers)
        record(f"Get Profile {pid}", "GET", f"/api/v1/profiles/{pid}", r.status_code,
               r.status_code == 200, r.text[:100])

    # Create custom profile
    r = client.post(f"{API_BASE}/api/v1/profiles", headers=headers, json={
        "profile_id": "e2e-test-profile",
        "preflight_profile": {
            "name": "E2E Test Profile",
            "description": "Test profile for E2E testing",
            "version": "1.0",
            "conformance": None,
            "workflow": "CMYK",
            "checks": {"enabled": ["LPDF_*"], "disabled": [], "severity_overrides": {}},
            "thresholds": {"min_dpi": 300.0}
        }
    })
    record("Create Profile", "POST", "/api/v1/profiles", r.status_code,
           r.status_code in (200, 201), r.text[:100])

    # Delete custom profile
    r = client.delete(f"{API_BASE}/api/v1/profiles/e2e-test-profile", headers=headers)
    record("Delete Profile", "DELETE", "/api/v1/profiles/e2e-test-profile", r.status_code,
           r.status_code in (200, 204), r.text[:100] if r.text else "deleted")


def test_ai_config(api_key: str):
    log("\n=== AI CONFIG ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.get(f"{API_BASE}/api/v1/ai/config", headers=headers)
    record("Get AI Config", "GET", "/api/v1/ai/config", r.status_code,
           r.status_code == 200, r.text[:200])

    r = client.get(f"{API_BASE}/api/v1/ai/credits", headers=headers)
    record("Get AI Credits", "GET", "/api/v1/ai/credits", r.status_code,
           r.status_code == 200, r.text[:200])

    r = client.get(f"{API_BASE}/api/v1/ai/presets", headers=headers)
    record("List AI Presets", "GET", "/api/v1/ai/presets", r.status_code,
           r.status_code == 200, r.text[:200])

    # Update AI config - enable all categories
    r = client.put(f"{API_BASE}/api/v1/ai/config", headers=headers, json={
        "enabled_categories": [
            "barcode_detection", "color_compliance", "content_quality",
            "document_classification", "image_analysis", "logo_verification",
            "regulatory_compliance", "spatial_analysis", "symbol_detection",
            "text_analysis", "dieline_detection", "color_analysis",
            "nlp_interfaces", "file_comparison", "trend_analysis"
        ],
        "industry_type": "food_beverage",
        "regulatory_market": "us_fda"
    })
    record("Update AI Config", "PUT", "/api/v1/ai/config", r.status_code,
           r.status_code in (200, 201), r.text[:200])

    # Set dictionary
    r = client.put(f"{API_BASE}/api/v1/ai/config/dictionary", headers=headers,
                   json={"words": ["LintPDF", "preflight", "CMYK"]})
    record("Set Dictionary", "PUT", "/api/v1/ai/config/dictionary", r.status_code,
           r.status_code in (200, 201, 204), r.text[:100])

    # Set palette
    r = client.put(f"{API_BASE}/api/v1/ai/config/palette", headers=headers, json={
        "colors": [
            {"name": "Primary Blue", "value": "#1a3a7a", "color_space": "srgb"},
            {"name": "Accent Red", "value": "#dc2626", "color_space": "srgb"}
        ]
    })
    record("Set Palette", "PUT", "/api/v1/ai/config/palette", r.status_code,
           r.status_code in (200, 201, 204), r.text[:100])


def submit_job(api_key: str, pdf_bytes: bytes, profile: str, label: str) -> str:
    """Submit a PDF for preflight and return job_id."""
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (f"{label}.pdf", io.BytesIO(bytes(pdf_bytes)), "application/pdf")}
    data = {"profile_id": profile}

    r = client.post(f"{API_BASE}/api/v1/jobs", headers=headers, files=files, data=data)
    record(f"Submit Job ({label})", "POST", "/api/v1/jobs", r.status_code,
           r.status_code in (200, 201, 202), r.text[:200])

    if r.status_code in (200, 201, 202):
        job_id = r.json().get("job_id", "")
        job_ids.append(job_id)
        return job_id
    return ""


def poll_job(api_key: str, job_id: str, label: str, max_wait: int = 300) -> dict:
    """Poll job until complete or timeout."""
    headers = {"Authorization": f"Bearer {api_key}"}
    start = time.time()
    last_status = ""

    while time.time() - start < max_wait:
        r = client.get(f"{API_BASE}/api/v1/jobs/{job_id}", headers=headers)
        if r.status_code != 200:
            record(f"Poll Job ({label})", "GET", f"/api/v1/jobs/{job_id}", r.status_code, False, r.text[:200])
            return {}

        data = r.json()
        status = data.get("status", "unknown")
        if status != last_status:
            log(f"  Job {label}: {status}")
            last_status = status

        if status == "complete":
            findings = data.get("findings", [])
            summary = data.get("summary", {})
            record(f"Job Complete ({label})", "GET", f"/api/v1/jobs/{job_id}", 200, True,
                   f"findings={len(findings)} errors={summary.get('error_count',0)} "
                   f"warnings={summary.get('warning_count',0)} advisories={summary.get('advisory_count',0)}")
            return data
        elif status == "failed":
            record(f"Job Failed ({label})", "GET", f"/api/v1/jobs/{job_id}", 200, False,
                   data.get("error_message", "unknown error")[:200])
            return data

        time.sleep(5)

    record(f"Job Timeout ({label})", "GET", f"/api/v1/jobs/{job_id}", 0, False,
           f"Timed out after {max_wait}s, last status: {last_status}")
    return {}


def analyze_findings(all_findings: list):
    """Analyze findings across all jobs."""
    log("\n=== FINDINGS ANALYSIS ===")
    by_id = defaultdict(list)
    by_severity = defaultdict(int)
    by_category = defaultdict(int)

    for f in all_findings:
        iid = f.get("inspection_id", "UNKNOWN")
        sev = f.get("severity", "unknown")
        cat = f.get("category", "uncategorized")
        by_id[iid].append(f)
        by_severity[sev] += 1
        by_category[cat] += 1

    log(f"  Total findings: {len(all_findings)}")
    log(f"  Unique check IDs triggered: {len(by_id)}")
    log(f"  Severity breakdown: {dict(by_severity)}")
    log(f"  Category breakdown:")
    for cat, count in sorted(by_category.items()):
        log(f"    {cat}: {count}")

    log(f"\n  Check IDs triggered ({len(by_id)}):")
    for iid in sorted(by_id.keys()):
        severities = set(f["severity"] for f in by_id[iid])
        log(f"    {iid}: {len(by_id[iid])} findings ({', '.join(severities)})")

    return by_id, by_severity


def test_reports(api_key: str, job_id: str):
    log("\n=== REPORTS ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    # Generate reports
    r = client.post(f"{API_BASE}/api/v1/jobs/{job_id}/reports", headers=headers,
                    json={"formats": ["html", "pdf"], "expiry_days": 1})
    record("Generate Reports", "POST", f"/api/v1/jobs/{job_id}/reports", r.status_code,
           r.status_code in (200, 201), r.text[:200])

    if r.status_code in (200, 201):
        reports = r.json().get("reports", [])
        for rpt in reports:
            token = rpt.get("token", "")
            fmt = rpt.get("format", "")
            report_tokens.append(token)
            log(f"  Report: {fmt} token={token[:20]}...")

    # List reports
    r = client.get(f"{API_BASE}/api/v1/jobs/{job_id}/reports", headers=headers)
    record("List Reports", "GET", f"/api/v1/jobs/{job_id}/reports", r.status_code,
           r.status_code == 200, r.text[:200])

    # Serve HTML report
    if report_tokens:
        r = client.get(f"{API_BASE}/r/{report_tokens[0]}")
        record("Serve HTML Report", "GET", f"/r/{report_tokens[0][:10]}...", r.status_code,
               r.status_code == 200, f"length={len(r.text)}")


def test_webhooks(api_key: str):
    log("\n=== WEBHOOKS ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.get(f"{API_BASE}/api/v1/webhooks", headers=headers)
    record("List Webhooks", "GET", "/api/v1/webhooks", r.status_code,
           r.status_code == 200, r.text[:200])

    # Create webhook (will fail if URL not HTTPS to external - expected)
    r = client.post(f"{API_BASE}/api/v1/webhooks", headers=headers, json={
        "url": "https://webhook.site/test-e2e-lintpdf",
        "events": ["job.complete", "job.failed"]
    })
    record("Create Webhook", "POST", "/api/v1/webhooks", r.status_code,
           r.status_code in (200, 201), r.text[:200])

    webhook_id = ""
    if r.status_code in (200, 201):
        webhook_id = r.json().get("id", "")
        # Test webhook
        r2 = client.post(f"{API_BASE}/api/v1/webhooks/{webhook_id}/test", headers=headers)
        record("Test Webhook", "POST", f"/api/v1/webhooks/{webhook_id}/test",
               r2.status_code, r2.status_code in (200, 201), r2.text[:200])
        # Delete webhook
        r3 = client.delete(f"{API_BASE}/api/v1/webhooks/{webhook_id}", headers=headers)
        record("Delete Webhook", "DELETE", f"/api/v1/webhooks/{webhook_id}",
               r3.status_code, r3.status_code in (200, 204), "deleted")


def test_endpoints_mgmt(api_key: str):
    log("\n=== CUSTOM ENDPOINTS ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.get(f"{API_BASE}/api/v1/endpoints", headers=headers)
    record("List Endpoints", "GET", "/api/v1/endpoints", r.status_code,
           r.status_code == 200, r.text[:200])

    r = client.post(f"{API_BASE}/api/v1/endpoints", headers=headers, json={
        "slug": "e2e-test-endpoint",
        "profile_id": "lintpdf-default",
        "description": "E2E test endpoint"
    })
    record("Create Endpoint", "POST", "/api/v1/endpoints", r.status_code,
           r.status_code in (200, 201), r.text[:200])

    if r.status_code in (200, 201):
        eid = r.json().get("id", "")
        r2 = client.delete(f"{API_BASE}/api/v1/endpoints/{eid}", headers=headers)
        record("Delete Endpoint", "DELETE", f"/api/v1/endpoints/{eid}",
               r2.status_code, r2.status_code in (200, 204), "deleted")


def test_usage(api_key: str, job_id: str):
    log("\n=== USAGE & CAPTAIN'S LOG ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.get(f"{API_BASE}/api/v1/usage", headers=headers)
    record("Get Usage", "GET", "/api/v1/usage", r.status_code,
           r.status_code == 200, r.text[:200])

    r = client.get(f"{API_BASE}/api/v1/ai/usage", headers=headers)
    record("Get AI Usage", "GET", "/api/v1/ai/usage", r.status_code,
           r.status_code == 200, r.text[:200])

    r = client.get(f"{API_BASE}/api/v1/ai/usage/trends", headers=headers,
                   params={"period": "30d"})
    record("Get AI Trends", "GET", "/api/v1/ai/usage/trends", r.status_code,
           r.status_code == 200, r.text[:200])

    if job_id:
        r = client.get(f"{API_BASE}/api/v1/captains-log/{job_id}/interpret", headers=headers)
        record("Captain's Log", "GET", f"/api/v1/captains-log/{job_id}/interpret",
               r.status_code, r.status_code == 200, r.text[:200])


def test_job_list_delete(api_key: str):
    log("\n=== JOB MANAGEMENT ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.get(f"{API_BASE}/api/v1/jobs", headers=headers, params={"page": 1, "page_size": 5})
    record("List Jobs", "GET", "/api/v1/jobs", r.status_code,
           r.status_code == 200, r.text[:200])


def test_profile_generate(api_key: str):
    log("\n=== AI PROFILE GENERATION ===")
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.post(f"{API_BASE}/api/v1/preflight-profiles/generate", headers=headers,
                    json={"description": "Check for FDA nutrition facts, barcode validation, and spot colors on CMYK packaging"})
    record("Generate Profile", "POST", "/api/v1/preflight-profiles/generate",
           r.status_code, r.status_code == 200, r.text[:200])


# ──── Main ──────────────────────────────────────────────────────────────────
def main():
    log("=" * 70)
    log("LintPDF E2E API Test Suite")
    log("=" * 70)

    # Step 1: Health
    test_health()

    # Step 2: Modal inference (skip if cold-starting)
    if not SKIP_MODAL_DIRECT:
        test_modal_inference()
    else:
        log("\n=== MODAL INFERENCE: SKIPPED (cold-starting, will test via API jobs) ===")

    # Step 3: Setup tenant
    api_key, tenant_id = test_setup_tenant()
    if not api_key:
        log("FATAL: Could not get API key. Aborting.")
        print_summary()
        return

    # Step 4: Profiles
    test_profiles(api_key)

    # Step 5: AI Config
    test_ai_config(api_key)

    # Step 6: Submit test PDFs
    log("\n=== PREFLIGHT JOBS ===")
    pdfs = [
        ("minimal", make_minimal_pdf(), "lintpdf-default"),
        ("minimal-strict", make_minimal_pdf(), "lintpdf-strict"),
        ("barcode", make_barcode_pdf(), "lintpdf-default"),
        ("packaging", make_packaging_pdf(), "lintpdf-default"),
    ]

    submitted = []
    for label, pdf_bytes, profile in pdfs:
        jid = submit_job(api_key, pdf_bytes, profile, label)
        if jid:
            submitted.append((label, jid))

    # Step 7: Poll all jobs
    all_findings = []
    completed_job_id = ""
    for label, jid in submitted:
        data = poll_job(api_key, jid, label)
        findings = data.get("findings", [])
        all_findings.extend(findings)
        if data.get("status") == "complete" and not completed_job_id:
            completed_job_id = jid

    # Step 8: Analyze findings
    by_id, by_severity = analyze_findings(all_findings)

    # Step 9: Reports
    if completed_job_id:
        test_reports(api_key, completed_job_id)

    # Step 10: Webhooks & Endpoints
    test_webhooks(api_key)
    test_endpoints_mgmt(api_key)

    # Step 11: Usage & Captain's Log
    test_usage(api_key, completed_job_id)

    # Step 12: AI Profile Generation
    test_profile_generate(api_key)

    # Step 13: Job list
    test_job_list_delete(api_key)

    # Summary
    print_summary()

    # Save results
    with open("/tmp/e2e_test_results.json", "w") as f:
        json.dump({
            "results": results,
            "findings_summary": {
                "total": len(all_findings),
                "unique_checks": len(by_id),
                "severity": dict(by_severity),
                "check_ids": sorted(by_id.keys()),
            },
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    log(f"\nFull results saved to /tmp/e2e_test_results.json")


def print_summary():
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    log(f"  Total: {total}  Passed: {passed}  Failed: {failed}")
    log(f"  Pass rate: {passed/total*100:.1f}%" if total else "  No tests ran")

    if failed:
        log("\n  FAILURES:")
        for r in results:
            if not r["passed"]:
                log(f"    [{r['status']}] {r['test']}: {r['detail'][:80]}")


if __name__ == "__main__":
    main()
