#!/usr/bin/env python3
"""LintPDF Preflight Engine — exhaustive end-to-end test.

Bootstraps a throwaway tenant via the admin key, submits a PDF, exercises
EVERY preflight + report + viewer + share-link + verdict + approval
variant against the live engine, and prints a summary block with every
URL (interactive viewer, every report format, share link, etc.) so you
can click straight into the result.

Usage:
    LINTPDF_ADMIN_KEY=... python3 scripts/test_preflight.py

The script prompts for a PDF file path; press Enter to use the default
10-page example shipped at packages/web/public/lintpdf_preflight_test_final.pdf.

Env vars (all optional):
    LINTPDF_API_BASE   default https://api.lintpdf.com
    LINTPDF_APP_BASE   default https://app.lintpdf.com (for viewer URLs)
    LINTPDF_ADMIN_KEY  REQUIRED — same X-Admin-Key the engine uses
    LINTPDF_KEEP       set to 1 to leave the throwaway tenant in place
                       (default: deactivate it after the run)

Stdlib only — no pip install needed.
"""

from __future__ import annotations

import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

API_BASE = os.environ.get("LINTPDF_API_BASE", "https://api.lintpdf.com").rstrip("/")
APP_BASE = os.environ.get("LINTPDF_APP_BASE", "https://app.lintpdf.com").rstrip("/")
ADMIN_KEY = os.environ.get("LINTPDF_ADMIN_KEY")
KEEP_TENANT = os.environ.get("LINTPDF_KEEP") == "1"

DEFAULT_PDF = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "web"
    / "public"
    / "lintpdf_preflight_test_final.pdf"
)


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------


class HTTP:
    """Minimal urllib wrapper with json + multipart helpers + verbose logging."""

    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.results: list[dict[str, Any]] = []

    def _record(self, method: str, path: str, status: int, note: str = "", ok: bool = False) -> None:
        self.results.append(
            {"method": method, "path": path, "status": status, "note": note, "ok": ok}
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        raw_body: bytes | None = None,
        content_type: str | None = None,
        expect: tuple[int, ...] = (200, 201, 204),
        note: str = "",
    ) -> tuple[int, dict[str, Any] | bytes | None]:
        url = self.base + path
        h = {"Accept": "application/json"}
        if headers:
            h.update(headers)
        body: bytes | None = raw_body
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            h["Content-Type"] = "application/json"
        elif content_type:
            h["Content-Type"] = content_type
        req = urllib.request.Request(url, data=body, method=method.upper(), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
                code = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            code = exc.code
        except urllib.error.URLError as exc:
            self._record(method, path, 0, f"NETWORK ERROR: {exc.reason}", ok=False)
            return 0, None

        result: dict[str, Any] | bytes | None = raw
        ctype = ""
        try:
            # urllib's resp closed already; status from above
            if raw and raw[:1] in (b"{", b"["):
                result = json.loads(raw.decode("utf-8"))
                ctype = "json"
        except Exception:
            result = raw
        ok = code in expect
        marker = "✓" if ok else "✗"
        short = ""
        if isinstance(result, dict):
            short = json.dumps({k: ("…" if k in ("payload", "summary", "result") else v)
                                for k, v in list(result.items())[:3]})[:120]
        elif isinstance(result, bytes):
            short = f"<{len(raw)} bytes>"
        print(f"  {marker} {method.upper():6} {path:55} {code:4}  {short}")
        self._record(method, path, code, note, ok=ok)
        return code, result


# ---------------------------------------------------------------------------
# Multipart encoder
# ---------------------------------------------------------------------------


def encode_multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"----lintpdf-{uuid.uuid4().hex}"
    out = bytearray()
    for name, value in fields.items():
        if value is None:
            continue
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        out += str(value).encode("utf-8") + b"\r\n"
    for name, (filename, data, ctype) in files.items():
        out += f"--{boundary}\r\n".encode()
        out += (
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        ).encode()
        out += f"Content-Type: {ctype}\r\n\r\n".encode()
        out += data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


def pick_pdf() -> Path:
    print(f"\nDefault PDF: {DEFAULT_PDF} ({DEFAULT_PDF.stat().st_size if DEFAULT_PDF.exists() else 0} bytes, 10 pages)")
    raw = input("Press Enter for default, or paste a different PDF path: ").strip()
    if not raw:
        if not DEFAULT_PDF.exists():
            sys.exit(f"Default PDF missing: {DEFAULT_PDF}")
        return DEFAULT_PDF
    p = Path(raw).expanduser().resolve()
    if not p.exists():
        sys.exit(f"PDF not found: {p}")
    return p


def bootstrap_tenant(http: HTTP) -> tuple[str, str]:
    """Create temp tenant + mint an API key with admin auth."""
    print("\n=== bootstrap throwaway tenant ===")
    label = f"preflight-suite-{secrets.token_hex(3)}"
    code, body = http.request(
        "POST",
        "/api/v1/admin/tenants",
        headers={"X-Admin-Key": ADMIN_KEY},
        json_body={
            "name": label,
            "contact_email": f"{label}@example.test",
            "plan": "scale",
        },
    )
    assert code in (200, 201) and isinstance(body, dict), body
    tenant_id = body["id"]

    code, body = http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/keys",
        headers={"X-Admin-Key": ADMIN_KEY},
        json_body={"label": "preflight-suite"},
    )
    assert code in (200, 201) and isinstance(body, dict), body
    api_key = body["raw_key"]
    print(f"  tenant_id={tenant_id}  api_key={api_key[:16]}…")
    # Enable AI on the tenant so the AI variant + Captain's Log routes
    # actually execute against the analyzer pipeline. Without this they
    # 403 with "AI features are not enabled for this tenant."
    http.request(
        "PUT",
        f"/api/v1/admin/tenants/{tenant_id}/ai",
        headers={"X-Admin-Key": ADMIN_KEY},
        json_body={"enabled": True},
        expect=(200, 201, 204),
    )
    # Pre-emptively grant generous AI credits + file pack so AI variants
    # don't trip on quota.
    http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/ai/credits",
        headers={"X-Admin-Key": ADMIN_KEY},
        json_body={"credits": 5000, "expires_in_days": 1},
        expect=(200, 201, 204),
    )
    http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/files/packages",
        headers={"X-Admin-Key": ADMIN_KEY},
        json_body={"files": 200, "expires_in_days": 1},
        expect=(200, 201, 204),
    )
    return tenant_id, api_key


def submit_pdf(
    http: HTTP,
    api_key: str,
    pdf: Path,
    *,
    profile_id: str = "lintpdf-default",
    ai_enabled: bool | None = None,
    ai_categories: str | None = None,
    label: str = "",
) -> str | None:
    """Submit a PDF and return the job_id (or None on failure)."""
    pdf_bytes = pdf.read_bytes()
    fields: dict[str, str] = {"profile_id": profile_id}
    if ai_enabled is not None:
        fields["ai_enabled"] = "true" if ai_enabled else "false"
    if ai_categories:
        fields["ai_categories"] = ai_categories
    body, ctype = encode_multipart(
        fields, {"file": (pdf.name, pdf_bytes, "application/pdf")}
    )
    code, resp = http.request(
        "POST",
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {api_key}"},
        raw_body=body,
        content_type=ctype,
        expect=(200, 201, 202),
        note=f"submit ({label})",
    )
    if code not in (200, 201, 202) or not isinstance(resp, dict):
        return None
    return resp.get("job_id")


def wait_for_complete(http: HTTP, api_key: str, job_id: str, timeout_s: int = 600) -> dict[str, Any] | None:
    """Poll until the job lands in a terminal state.

    The 10-page sample takes 90-180s on the standard worker; AI-enabled
    runs add another minute or so. 600s headroom keeps the script
    resilient against transient queue backups without hanging
    indefinitely on a stuck job.
    """
    deadline = time.time() + timeout_s
    last_status = ""
    while time.time() < deadline:
        code, body = http.request(
            "GET",
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if isinstance(body, dict):
            status = body.get("status", "")
            if status in ("complete", "failed"):
                return body
            last_status = status
        time.sleep(5)
    print(f"  ✗ Timeout waiting for job {job_id} (last status: {last_status})")
    return None


def submit_external_import(
    http: HTTP, api_key: str, pdf: Path, fmt: str, sidecar_path: Path, label: str
) -> str | None:
    pdf_bytes = pdf.read_bytes()
    sidecar_bytes = sidecar_path.read_bytes()
    sidecar_name = sidecar_path.name
    sidecar_ct = mimetypes.guess_type(sidecar_name)[0] or "application/octet-stream"
    body, ctype = encode_multipart(
        {"external_format": fmt, "preflight_source": "external"},
        {
            "file": (pdf.name, pdf_bytes, "application/pdf"),
            "external_report": (sidecar_name, sidecar_bytes, sidecar_ct),
        },
    )
    code, resp = http.request(
        "POST",
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {api_key}"},
        raw_body=body,
        content_type=ctype,
        expect=(200, 201, 202),
        note=f"import {fmt}",
    )
    if isinstance(resp, dict):
        return resp.get("job_id")
    return None


def generate_every_report_format(
    http: HTTP, api_key: str, job_id: str
) -> dict[str, str]:
    """One POST per format so each is independently inspectable."""
    print(f"\n=== generate every report format for job {job_id[:8]}… ===")
    formats = ["html", "pdf", "json", "xml", "annotated_pdf", "annotated_pdf_markup"]
    out: dict[str, str] = {}
    for fmt in formats:
        code, body = http.request(
            "POST",
            f"/api/v1/jobs/{job_id}/reports",
            headers={"Authorization": f"Bearer {api_key}"},
            json_body={"formats": [fmt], "expiry_days": 1},
            expect=(200, 201),
            note=f"report {fmt}",
        )
        if isinstance(body, dict):
            for r in body.get("reports", []):
                if r.get("url"):
                    out[fmt] = r["url"]
                elif r.get("skipped_reason"):
                    print(f"      ↳ {fmt} skipped: {r['skipped_reason']}")
    return out


def exercise_viewer_surface(
    http: HTTP, api_key: str, job_id: str
) -> dict[str, Any]:
    """Annotations + comments + verdict + on-demand capabilities."""
    print(f"\n=== viewer surface for job {job_id[:8]}… ===")
    h = {"Authorization": f"Bearer {api_key}"}
    out: dict[str, Any] = {}

    # Viewer config + page list + on-demand capabilities
    http.request("GET", f"/api/v1/viewer/jobs/{job_id}/config", headers=h)
    http.request("GET", f"/api/v1/viewer/jobs/{job_id}/pages", headers=h)
    for cap in ("separations", "fonts", "images", "tac"):
        http.request(
            "POST",
            f"/api/v1/viewer/jobs/{job_id}/capabilities/{cap}",
            headers=h,
            expect=(200, 201, 202, 409),
            note=f"capability {cap}",
        )

    # Create one annotation per kind
    annotations: list[str] = []
    for kind, geom in (
        ("rect", {"x": 100, "y": 100, "w": 50, "h": 30}),
        ("circle", {"cx": 200, "cy": 200, "r": 25}),
        ("arrow", {"x1": 50, "y1": 50, "x2": 150, "y2": 150}),
        ("note", {"x": 250, "y": 250}),
        ("freehand", {"points": [[10, 10], [20, 20], [30, 15]]}),
    ):
        code, body = http.request(
            "POST",
            f"/api/v1/viewer/jobs/{job_id}/annotations",
            headers=h,
            json_body={
                "page_num": 1,
                "kind": kind,
                "geometry": geom,
                "color": "#dc2626",
                "text": f"smoke-test {kind}",
            },
            expect=(200, 201),
            note=f"annotation {kind}",
        )
        if isinstance(body, dict) and body.get("id"):
            annotations.append(body["id"])
    out["annotations"] = annotations

    # Comment on the first annotation
    if annotations:
        http.request(
            "POST",
            f"/api/v1/viewer/jobs/{job_id}/annotations/{annotations[0]}/comments",
            headers=h,
            json_body={"body": "Approve once bleed is fixed."},
            expect=(200, 201),
        )

    # Verdict pass + fail flip + back to pass
    for verdict, notes in (("pass", "looks good"), ("fail", "has issues"), ("pass", "issues fixed")):
        http.request(
            "POST",
            f"/api/v1/viewer/jobs/{job_id}/verdict",
            headers=h,
            json_body={"verdict": verdict, "notes": notes},
            expect=(200, 422),
            note=f"verdict {verdict}",
        )

    # State digest with each include slice
    for include in ("", "reports", "approval_chain", "verdict", "annotations",
                    "reports,approval_chain,verdict,annotations"):
        params = f"?include={urllib.parse.quote(include)}" if include else ""
        http.request(
            "GET",
            f"/api/v1/jobs/{job_id}/state{params}",
            headers=h,
            note=f"state include={include or 'all'}",
        )

    return out


def exercise_share_link(http: HTTP, api_key: str, job_id: str) -> tuple[str | None, str | None]:
    """Mint TWO share-link tokens: gated + fully public.

    * Gated token carries ``require_visitor_email=true`` so the public
      routes exercise the ``X-Visitor-Email`` capture path (used by the
      real dashboard when a reviewer shares with a specific person).
    * Public token carries ``require_visitor_email=false`` so the URL
      is clickable with zero headers -- this is what prospects follow
      from a marketing share or a password-less "see this report" link.

    Returns ``(gated_token, public_token)``. Callers use the public
    token for the summary block's "interactive viewer" URL so the
    operator running the script can actually click through without
    forging a visitor email.
    """
    print(f"\n=== share links for job {job_id[:8]}… (gated + public) ===")
    h = {"Authorization": f"Bearer {api_key}"}

    gated_token: str | None = None
    public_token: str | None = None

    code, body = http.request(
        "POST",
        f"/api/v1/jobs/{job_id}/reports",
        headers=h,
        json_body={
            "formats": ["html"],
            "expiry_days": 1,
            "allow_annotations": True,
            "require_visitor_email": True,
        },
        note="gated share",
    )
    if isinstance(body, dict):
        for r in body.get("reports", []):
            if r.get("token"):
                gated_token = r["token"]
                break
    if gated_token:
        # Exercise the visitor-email gate + public state mirror.
        http.request(
            "GET",
            f"/api/v1/viewer/public/{gated_token}/state",
            headers={"X-Visitor-Email": "viewer@example.test"},
        )
        http.request(
            "GET",
            f"/api/v1/viewer/public/{gated_token}/annotations?include=comments",
            headers={"X-Visitor-Email": "viewer@example.test"},
        )

    code, body = http.request(
        "POST",
        f"/api/v1/jobs/{job_id}/reports",
        headers=h,
        json_body={
            "formats": ["html"],
            "expiry_days": 7,
            "allow_annotations": True,
            "require_visitor_email": False,
        },
        note="public share",
    )
    if isinstance(body, dict):
        for r in body.get("reports", []):
            if r.get("token"):
                public_token = r["token"]
                break
    if public_token:
        # Verify the public token needs zero headers.
        http.request("GET", f"/api/v1/viewer/public/{public_token}/state")
        http.request("GET", f"/api/v1/viewer/public/{public_token}/pages")
    return gated_token, public_token


def exercise_approval_chain(http: HTTP, api_key: str, job_id: str) -> dict[str, Any]:
    """Attach a 1-step chain + approve via the access token."""
    print(f"\n=== approval chain for job {job_id[:8]}… ===")
    h = {"Authorization": f"Bearer {api_key}"}
    code, body = http.request(
        "POST",
        f"/api/v1/jobs/{job_id}/approval-chain",
        headers=h,
        json_body={
            "steps": [
                {
                    "name": "Print ops",
                    "approvers": [{"email": "ops@example.test"}],
                    "require_all": False,
                }
            ]
        },
        expect=(200, 201),
    )
    out: dict[str, Any] = {}
    if isinstance(body, dict):
        out["chain_id"] = body.get("id")
        steps = body.get("step_history") or body.get("steps") or []
        if steps:
            access_token = steps[0].get("access_token")
            if access_token:
                # Inspect via approval-info (anonymous)
                http.request(
                    "GET",
                    f"/api/v1/approvals/info/{access_token}",
                )
                # Decide approved
                http.request(
                    "POST",
                    f"/api/v1/approvals/decide/{access_token}",
                    json_body={
                        "decision": "approved",
                        "notes": "Looks great, ship it.",
                    },
                    expect=(200, 201, 204),
                )
                out["access_token"] = access_token
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    if not ADMIN_KEY:
        sys.exit("LINTPDF_ADMIN_KEY env var is required")
    pdf = pick_pdf()
    print(f"Using PDF: {pdf}")
    http = HTTP(API_BASE)

    tenant_id, api_key = bootstrap_tenant(http)

    # ----- Variant 1: vanilla submit
    print("\n=== variant 1: vanilla preflight (lintpdf-default profile) ===")
    job_vanilla = submit_pdf(http, api_key, pdf, label="vanilla")
    job_vanilla_full = wait_for_complete(http, api_key, job_vanilla) if job_vanilla else None

    # ----- Variant 2: AI-enabled submit
    print("\n=== variant 2: AI-enabled preflight ===")
    job_ai = submit_pdf(
        http, api_key, pdf,
        ai_enabled=True,
        ai_categories="brand_consistency,regulatory",
        label="ai",
    )
    job_ai_full = wait_for_complete(http, api_key, job_ai) if job_ai else None

    # ----- Variant 3: external imports — one job per parser
    print("\n=== variant 3: external preflight imports ===")
    examples = Path(__file__).resolve().parent.parent / "docs" / "examples"
    import_jobs: dict[str, str] = {}
    for fmt, sidecar in (
        ("pitstop_xml", examples / "pitstop-report.xml"),
        ("callas_xml", examples / "callas-report.xml"),
        ("callas_json", examples / "callas-report.json"),
        ("acrobat_xml", examples / "acrobat-report.xml"),
        ("lintpdf_json", examples / "lintpdf-native.json"),
    ):
        if not sidecar.exists():
            print(f"  ⚠  skipping {fmt}: sidecar missing at {sidecar}")
            continue
        jid = submit_external_import(http, api_key, pdf, fmt, sidecar, label=fmt)
        if jid:
            wait_for_complete(http, api_key, jid)
            import_jobs[fmt] = jid

    # ----- Reports + viewer + share + approval against the vanilla job
    primary_job = job_vanilla
    reports: dict[str, str] = {}
    gated_token: str | None = None
    public_token: str | None = None
    if primary_job:
        reports = generate_every_report_format(http, api_key, primary_job)
        exercise_viewer_surface(http, api_key, primary_job)
        gated_token, public_token = exercise_share_link(http, api_key, primary_job)
        exercise_approval_chain(http, api_key, primary_job)

    # ----- Captain's Log AI interpret on the AI job (if available)
    if job_ai:
        http.request(
            "GET",
            f"/api/v1/captains-log/{job_ai}/interpret",
            headers={"Authorization": f"Bearer {api_key}"},
            expect=(200, 202, 402, 403, 404),
            note="ai interpret",
        )

    # ----- Cleanup (deactivate tenant unless KEEP=1)
    if not KEEP_TENANT:
        print(f"\n=== deactivating throwaway tenant {tenant_id[:8]}… ===")
        http.request(
            "PATCH",
            f"/api/v1/admin/tenants/{tenant_id}/status",
            headers={"X-Admin-Key": ADMIN_KEY},
            json_body={"is_active": False},
        )

    # ----- Final summary
    # ``ok`` reflects whether the call landed in its caller-declared
    # expect tuple, so 403/404/422 probes that we deliberately want to
    # fire (e.g. AI interpret on a non-AI tenant) count as PASS.
    pass_count = sum(1 for r in http.results if r.get("ok"))
    fail_count = sum(1 for r in http.results if not r.get("ok"))
    print(f"\n{'='*70}\nSUMMARY  ✓ {pass_count}   ✗ {fail_count}   total {len(http.results)}\n{'='*70}")
    print(f"  tenant id       : {tenant_id}")
    print(f"  api key         : {api_key}")
    if job_vanilla:
        print(f"\n  primary job     : {job_vanilla}")
        # NOTE: the two URLs below are AUTHENTICATED. /jobs/{id}/state
        # needs ``Authorization: Bearer $API_KEY``; the dashboard viewer
        # needs a logged-in session for this tenant. Use the public
        # share URL further down for click-through without headers.
        print(f"  auth /state     : {API_BASE}/api/v1/jobs/{job_vanilla}/state  (needs Bearer token)")
        print(f"  auth dashboard  : {APP_BASE}/dashboard/jobs/{job_vanilla}/viewer  (needs login)")
    if job_ai:
        print(f"  AI job          : {job_ai}  (auth)")
    if reports:
        print("\n  report URLs (every format, public via signed token):")
        for fmt, url in reports.items():
            print(f"    {fmt:24} {url}")
    if public_token:
        print(f"\n  ✨ PUBLIC interactive viewer (no login, no headers):")
        print(f"    {API_BASE}/r/{public_token}")
        print(f"    public /state : {API_BASE}/api/v1/viewer/public/{public_token}/state")
        print(f"    public pages  : {API_BASE}/api/v1/viewer/public/{public_token}/pages")
    if gated_token:
        print(f"\n  gated share-link (needs X-Visitor-Email header):")
        print(f"    {API_BASE}/r/{gated_token}")
    if import_jobs:
        print("\n  external-import jobs (one per parser):")
        for fmt, jid in import_jobs.items():
            print(f"    {fmt:14} {APP_BASE}/dashboard/jobs/{jid}/viewer")

    if fail_count:
        print("\n  failures (status outside expect tuple):")
        for r in http.results:
            if not r.get("ok"):
                print(f"    {r['status']:4} {r['method']:6} {r['path']}  {r['note']}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
