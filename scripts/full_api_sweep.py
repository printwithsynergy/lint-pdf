"""Full-API sweep driver for LintPDF engine.

Submits the bundled 10-page test PDF across every submission path,
polls until every job completes, requests every report format, then
exercises the rest of the tenant-scoped surface (viewer, annotations,
AI, billing, profiles, branding, webhooks, usage). Every response is
captured with status, latency, summary, and URL — dumped to
``api-sweep-result.json`` and ``api-sweep-result.md`` side-by-side.

Inputs come from env vars so the same driver runs locally or against
prod:

    LINTPDF_BASE_URL      https://api.lintpdf.com
    LINTPDF_ADMIN_KEY     <admin X-Admin-Key>
    LINTPDF_TENANT_KEY    <tenant bearer key; if unset, provisions one>
    LINTPDF_TRIAL_SECRET  shared secret for /trial/submit (optional)
    LINTPDF_PDF           path to 10-page test PDF
    LINTPDF_OUT_DIR       where to write results (default /tmp/lintpdf-sweep)
    LINTPDF_POLL_TIMEOUT  seconds to wait per job (default 900)
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests


BASE_URL = os.environ.get("LINTPDF_BASE_URL", "https://api.lintpdf.com").rstrip("/")
ADMIN_KEY = os.environ.get("LINTPDF_ADMIN_KEY", "")
TENANT_KEY = os.environ.get("LINTPDF_TENANT_KEY", "")
TRIAL_SECRET = os.environ.get("LINTPDF_TRIAL_SECRET", "")
PDF_PATH = os.environ.get(
    "LINTPDF_PDF",
    "/home/user/lint-pdf/packages/web/public/lintpdf_preflight_test_final.pdf",
)
OUT_DIR = Path(os.environ.get("LINTPDF_OUT_DIR", "/tmp/lintpdf-sweep"))
OUT_DIR.mkdir(parents=True, exist_ok=True)
POLL_TIMEOUT = int(os.environ.get("LINTPDF_POLL_TIMEOUT", "900"))
POLL_INTERVAL = 10

AI_PRESET = "full-ai-scan"
PROFILE_ID = "lintpdf-default"
REPORT_FORMATS = ["pdf", "annotated_pdf", "annotated_pdf_markup", "html", "json", "xml"]

RESULTS: list[dict] = []
ARTIFACTS: list[dict] = []  # all clickable URLs


def _rec(
    method: str,
    path: str,
    status_code: int,
    elapsed_ms: int,
    summary: object | None = None,
    note: str | None = None,
) -> None:
    RESULTS.append(
        {
            "method": method,
            "path": path,
            "status": status_code,
            "elapsed_ms": elapsed_ms,
            "summary": summary,
            "note": note,
        }
    )


def _artifact(kind: str, url: str, **meta: object) -> None:
    ARTIFACTS.append({"kind": kind, "url": url, **meta})


def _hit(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, object] | None = None,
    json_body: object | None = None,
    files: dict[str, tuple] | None = None,
    data: dict[str, object] | None = None,
    expect: tuple[int, ...] = (200, 201, 202, 204),
    note: str | None = None,
) -> requests.Response:
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    t0 = time.time()
    r = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_body,
        files=files,
        data=data,
        timeout=120,
    )
    elapsed_ms = int((time.time() - t0) * 1000)
    summary: object | None
    try:
        body = r.json()
        if isinstance(body, dict):
            summary = {
                k: (f"<{len(v)} items>" if isinstance(v, list) else v)
                for k, v in list(body.items())[:8]
            }
        else:
            summary = (
                f"<{type(body).__name__} len={len(body) if hasattr(body, '__len__') else '?'}>"
            )
    except Exception:
        summary = f"<non-JSON {len(r.content)} bytes>"
    _rec(method, path, r.status_code, elapsed_ms, summary, note)
    expected = r.status_code in expect
    if not expected:
        print(f"  !! {method} {path} → {r.status_code} ({r.text[:200]})")
    else:
        print(f"  ok {method} {path} → {r.status_code} ({elapsed_ms}ms)")
    return r


def _tenant_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TENANT_KEY}"}


def _admin_headers() -> dict[str, str]:
    return {"X-Admin-Key": ADMIN_KEY}


TERMINAL_STATUSES = ("complete", "completed", "failed")


def _poll_job(job_id: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        r = _hit("GET", f"/api/v1/jobs/{job_id}", headers=_tenant_headers())
        body = r.json()
        st = body.get("status")
        if st in TERMINAL_STATUSES:
            return body
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Job {job_id} did not finish within {POLL_TIMEOUT}s")


TENANT_ID = os.environ.get("LINTPDF_TENANT_ID", "")


def provision_tenant_if_needed() -> None:
    global TENANT_KEY, TENANT_ID
    if TENANT_KEY and TENANT_ID:
        return
    print("→ provisioning throwaway tenant")
    r = _hit(
        "POST",
        "/api/v1/admin/tenants",
        headers=_admin_headers(),
        json_body={
            "name": f"api-sweep-{uuid.uuid4().hex[:8]}",
            "contact_email": "sweep@siftpdf.example",
            "plan": "growth",
        },
        expect=(201,),
        note="throwaway tenant for full API sweep",
    )
    body = r.json()
    TENANT_KEY = body["api_key"]
    TENANT_ID = body["id"]
    (OUT_DIR / "tenant.json").write_text(json.dumps(body, indent=2))


def enable_ai_on_tenant() -> None:
    """Admin-enable AI + grant credits so full-ai-scan actually runs."""
    if not TENANT_ID:
        return
    print("→ enabling AI on throwaway tenant")
    _hit(
        "PUT",
        f"/api/v1/admin/tenants/{TENANT_ID}/ai",
        headers=_admin_headers(),
        params={"ai_enabled": "true", "enabled_categories": "all"},
    )
    _hit(
        "POST",
        f"/api/v1/admin/tenants/{TENANT_ID}/ai/credits",
        headers=_admin_headers(),
        params={"amount": 100000, "reason": "sweep"},
    )
    # Trial mode is the easiest way to bypass per-credit checks during a sweep.
    _hit(
        "PUT",
        f"/api/v1/admin/tenants/{TENANT_ID}/ai/trial",
        headers=_admin_headers(),
        params={"enabled": "true", "duration_days": 30},
        expect=(200, 204),
    )


def submit_jobs() -> dict[str, str]:
    """Return {source: job_id} — one per submission path."""
    pdf = Path(PDF_PATH).read_bytes()
    jobs: dict[str, str] = {}

    print("→ POST /api/v1/jobs")
    r = _hit(
        "POST",
        "/api/v1/jobs",
        headers=_tenant_headers(),
        data={"profile_id": PROFILE_ID, "ai_preset": AI_PRESET},
        files={"file": (Path(PDF_PATH).name, pdf, "application/pdf")},
        expect=(202,),
        note="primary submission path",
    )
    jobs["jobs"] = r.json()["job_id"]

    print("→ POST /api/v1/batch/submit")
    r = _hit(
        "POST",
        "/api/v1/batch/submit",
        headers=_tenant_headers(),
        data={"profile_id": PROFILE_ID, "ai_preset": AI_PRESET},
        files={"files": (Path(PDF_PATH).name, pdf, "application/pdf")},
        expect=(202,),
    )
    body = r.json()
    batch_jobs = body.get("jobs") or []
    jobs["batch"] = (batch_jobs[0].get("job_id") or batch_jobs[0].get("id")) if batch_jobs else None
    (OUT_DIR / "batch-submit.json").write_text(json.dumps(body, indent=2))

    print("→ POST /api/v1/endpoints (create vanity endpoint)")
    slug = f"sweep-{uuid.uuid4().hex[:6]}"
    r = _hit(
        "POST",
        "/api/v1/endpoints",
        headers=_tenant_headers(),
        json_body={"slug": slug, "profile_id": PROFILE_ID, "description": "sweep"},
        expect=(201,),
    )
    ep_id = r.json().get("id")

    print(f"→ POST /api/v1/endpoints/{slug}/submit")
    r = _hit(
        "POST",
        f"/api/v1/endpoints/{slug}/submit",
        headers=_tenant_headers(),
        data={"ai_preset": AI_PRESET},
        files={"file": (Path(PDF_PATH).name, pdf, "application/pdf")},
        expect=(202,),
    )
    jobs["endpoints"] = r.json().get("job_id")

    if TRIAL_SECRET:
        print("→ POST /api/v1/trial/submit")
        r = _hit(
            "POST",
            "/api/v1/trial/submit",
            headers={"X-Trial-Secret": TRIAL_SECRET},
            data={
                "name": "API Sweep",
                "email": "sweep@siftpdf.example",
                "company": "Sweep Inc",
            },
            files={"files": (Path(PDF_PATH).name, pdf, "application/pdf")},
            expect=(201,),
        )
        (OUT_DIR / "trial-submit.json").write_text(json.dumps(r.json(), indent=2))

    # save endpoint id for cleanup
    (OUT_DIR / "endpoint.json").write_text(json.dumps({"id": ep_id, "slug": slug}))

    return jobs


def wait_for_jobs(jobs: dict[str, str]) -> dict[str, dict]:
    done: dict[str, dict] = {}
    for source, jid in jobs.items():
        if not jid:
            continue
        print(f"→ polling {source} job {jid}")
        done[source] = _poll_job(jid)
    return done


def generate_reports(jobs: dict[str, dict]) -> None:
    for source, job in jobs.items():
        jid = job.get("job_id")
        st = job.get("status")
        if not jid or st not in ("complete", "completed"):
            print(f"  ! skip reports for {source} (status={st})")
            continue
        print(f"→ POST /api/v1/jobs/{jid}/reports (all six formats)")
        r = _hit(
            "POST",
            f"/api/v1/jobs/{jid}/reports",
            headers=_tenant_headers(),
            json_body={
                "formats": REPORT_FORMATS,
                "expiry_days": 30,
                "detail_level": "comprehensive",
            },
            expect=(201,),
            note=f"all six report formats for {source} job",
        )
        body = r.json()
        for info in body.get("reports", []):
            if info.get("url"):
                full = info["url"]
                if not full.startswith("http"):
                    full = f"{BASE_URL}{full}"
                _artifact(
                    kind=f"report.{info.get('format')}",
                    url=full,
                    job_source=source,
                    job_id=jid,
                    format=info.get("format"),
                    token=info.get("token"),
                    content_type=info.get("content_type"),
                )
        # fetch each URL to confirm it renders
        for info in body.get("reports", []):
            url = info.get("url")
            if not url:
                continue
            if not url.startswith("http"):
                url = f"{BASE_URL}{url}"
            t0 = time.time()
            g = requests.get(url, timeout=60)
            elapsed_ms = int((time.time() - t0) * 1000)
            _rec(
                "GET",
                url.replace(BASE_URL, ""),
                g.status_code,
                elapsed_ms,
                {
                    "format": info.get("format"),
                    "bytes": len(g.content),
                    "content_type": g.headers.get("Content-Type"),
                },
                f"fetch {source} {info.get('format')}",
            )
            print(f"    fetch {info.get('format'):22s} → HTTP {g.status_code} ({len(g.content)} B)")


def exercise_viewer(job_id: str) -> None:
    h = _tenant_headers()
    _hit("GET", f"/api/v1/viewer/jobs/{job_id}/pages", headers=h)
    _hit("GET", f"/api/v1/viewer/jobs/{job_id}/pages/1/info", headers=h)
    # tile as raw PNG - don't try to parse JSON
    t0 = time.time()
    r = requests.get(
        f"{BASE_URL}/api/v1/viewer/jobs/{job_id}/pages/1/tile",
        headers=h,
        params={"dpi": 150},
        timeout=120,
    )
    _rec(
        "GET",
        f"/api/v1/viewer/jobs/{job_id}/pages/1/tile",
        r.status_code,
        int((time.time() - t0) * 1000),
        {"bytes": len(r.content), "content_type": r.headers.get("Content-Type")},
    )
    print(f"  ok tile → {r.status_code} ({len(r.content)} B)")
    _hit("GET", f"/api/v1/viewer/jobs/{job_id}/separations", headers=h)
    _hit("GET", f"/api/v1/viewer/jobs/{job_id}/layers", headers=h)
    _hit("GET", f"/api/v1/viewer/jobs/{job_id}/config", headers=h)
    _hit("GET", f"/api/v1/viewer/jobs/{job_id}/verdict", headers=h, expect=(200, 404))


def exercise_annotations(job_id: str) -> None:
    h = _tenant_headers()
    print("→ annotations CRUD")
    _hit("GET", f"/api/v1/viewer/jobs/{job_id}/annotations", headers=h)
    created: list[str] = []
    for kind, geom in [
        ("rect", {"x": 10, "y": 10, "w": 100, "h": 50}),
        ("circle", {"cx": 200, "cy": 100, "r": 30}),
        ("arrow", {"x1": 50, "y1": 50, "x2": 150, "y2": 150}),
        ("note", {"x": 300, "y": 200}),
    ]:
        r = _hit(
            "POST",
            f"/api/v1/viewer/jobs/{job_id}/annotations",
            headers=h,
            json_body={
                "page_num": 1,
                "kind": kind,
                "geometry": geom,
                "color": "#ff0000",
                "text": f"sweep {kind}",
            },
            expect=(201,),
        )
        if r.status_code == 201:
            created.append(r.json().get("id"))
    for aid in created:
        if aid:
            _hit(
                "PATCH",
                f"/api/v1/viewer/jobs/{job_id}/annotations/{aid}",
                headers=h,
                json_body={"text": "patched"},
            )
            _hit(
                "POST",
                f"/api/v1/viewer/jobs/{job_id}/annotations/{aid}/comments",
                headers=h,
                json_body={"body": "hello"},
                expect=(201,),
            )
            _hit(
                "DELETE",
                f"/api/v1/viewer/jobs/{job_id}/annotations/{aid}",
                headers=h,
                expect=(204,),
            )


def exercise_ai() -> None:
    h = _tenant_headers()
    _hit("GET", "/api/v1/ai/presets", headers=h)
    _hit("GET", "/api/v1/ai/config", headers=h)
    r = _hit(
        "PUT",
        "/api/v1/ai/config",
        headers=h,
        json_body={"enabled": True, "industry_type": "packaging"},
    )
    _hit("GET", "/api/v1/ai/credits", headers=h)
    _hit("GET", "/api/v1/ai/credits/packages", headers=h)
    _hit("GET", "/api/v1/ai/usage", headers=h)
    _hit("GET", "/api/v1/ai/usage/trends", headers=h)


def exercise_billing() -> None:
    h = _tenant_headers()
    _hit("GET", "/api/v1/files/quota", headers=h)
    _hit("GET", "/api/v1/files/packages", headers=h)


def exercise_profiles() -> None:
    h = _tenant_headers()
    _hit("GET", "/api/v1/profiles", headers=h)
    _hit("GET", f"/api/v1/profiles/{PROFILE_ID}", headers=h)


def exercise_branding() -> None:
    h = _tenant_headers()
    _hit("GET", "/api/v1/branding", headers=h, expect=(200, 404))


def exercise_webhooks() -> None:
    h = _tenant_headers()
    _hit("GET", "/api/v1/webhooks", headers=h)
    r = _hit(
        "POST",
        "/api/v1/webhooks",
        headers=h,
        json_body={
            "url": "https://example.com/hook",
            "events": ["job.completed"],
            "description": "sweep",
        },
        expect=(201,),
    )
    wid = r.json().get("id") if r.status_code == 201 else None
    if wid:
        _hit("POST", f"/api/v1/webhooks/{wid}/test", headers=h, expect=(200, 202, 400, 503))
        _hit("DELETE", f"/api/v1/webhooks/{wid}", headers=h, expect=(204,))


def exercise_usage() -> None:
    h = _tenant_headers()
    _hit("GET", "/api/v1/usage", headers=h)


def exercise_jobs_list(jobs: dict[str, dict]) -> None:
    h = _tenant_headers()
    _hit("GET", "/api/v1/jobs", headers=h)
    for source, job in jobs.items():
        jid = job.get("job_id")
        if jid:
            _hit("GET", f"/api/v1/jobs/{jid}", headers=h)


def exercise_job_state(jobs: dict[str, dict]) -> None:
    """Exercise GET /jobs/{id}/state + the ?include=comments annotations variant."""
    h = _tenant_headers()
    for source, job in jobs.items():
        jid = job.get("job_id")
        if not jid:
            continue
        # Full digest
        r = _hit("GET", f"/api/v1/jobs/{jid}/state", headers=h)
        if r.status_code == 200:
            body = r.json()
            sections = [
                k for k in ("reports", "approval_chain", "verdict", "annotations") if k in body
            ]
            print(f"    state sections present: {sections}")
        # Filtered digest
        _hit(
            "GET",
            f"/api/v1/jobs/{jid}/state",
            headers=h,
            params={"include": "verdict,annotations"},
            note="state with include filter",
        )
        # Reject unknown include
        _hit(
            "GET",
            f"/api/v1/jobs/{jid}/state",
            headers=h,
            params={"include": "nope"},
            expect=(422,),
            note="unknown include key should 422",
        )
        # Annotations ?include=comments
        _hit(
            "GET",
            f"/api/v1/viewer/jobs/{jid}/annotations",
            headers=h,
            params={"include": "comments"},
            note="annotations with comments embedded",
        )
        break  # one job is enough to prove the surface works


def emit_markdown() -> None:
    lines = [
        f"# LintPDF API sweep — {BASE_URL}",
        "",
        f"- Run at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"- Test PDF: `{PDF_PATH}` (10 pages)",
        f"- Preflight profile: `{PROFILE_ID}` + AI preset `{AI_PRESET}`",
        "",
        "## Artifact links",
        "",
        "| Kind | Job source | Format | URL |",
        "|---|---|---|---|",
    ]
    for a in ARTIFACTS:
        lines.append(
            f"| {a.get('kind')} | {a.get('job_source', '-')} | {a.get('format', '-')} | "
            f"[{a.get('url')}]({a.get('url')}) |"
        )
    lines += [
        "",
        "## Endpoint call log",
        "",
        "| Method | Path | Status | ms | Summary |",
        "|---|---|---|---|---|",
    ]
    for r in RESULTS:
        summary = json.dumps(r.get("summary"))[:160].replace("|", "\\|")
        lines.append(
            f"| {r['method']} | `{r['path']}` | {r['status']} | {r['elapsed_ms']} | {summary} |"
        )
    (OUT_DIR / "api-sweep-result.md").write_text("\n".join(lines))


def main() -> int:
    print(f"LintPDF API sweep → {BASE_URL}")
    provision_tenant_if_needed()
    enable_ai_on_tenant()

    exercise_ai()
    exercise_billing()
    exercise_profiles()
    exercise_branding()
    exercise_webhooks()
    exercise_usage()

    jobs = submit_jobs()
    done = wait_for_jobs(jobs)
    exercise_jobs_list(done)
    generate_reports(done)
    exercise_job_state(done)

    # Pick first completed job for viewer/annotation exercise
    for source, job in done.items():
        if job.get("status") in ("complete", "completed") and job.get("job_id"):
            exercise_viewer(job["job_id"])
            exercise_annotations(job["job_id"])
            break

    out = {
        "base_url": BASE_URL,
        "tenant_key_prefix": TENANT_KEY[:12],
        "pdf": PDF_PATH,
        "jobs": done,
        "artifacts": ARTIFACTS,
        "results": RESULTS,
    }
    (OUT_DIR / "api-sweep-result.json").write_text(json.dumps(out, indent=2, default=str))
    emit_markdown()

    ok = sum(1 for r in RESULTS if 200 <= r["status"] < 300)
    bad = [r for r in RESULTS if r["status"] >= 300 or r["status"] == 0]
    print(f"\nsummary: {ok} ok / {len(bad)} non-2xx")
    for r in bad[:30]:
        print(f"  !! {r['method']} {r['path']} → {r['status']}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
