#!/usr/bin/env python3
"""Seed the persistent "Print With Synergy (Demo Customer)" tenant.

Idempotent end-to-end: can be re-run safely. Each run mints a fresh
API key (the secret can only be retrieved at creation time).

What this creates / ensures:

* A tenant named "Print With Synergy (Demo Customer)" on the
  ``enterprise`` plan (unlocks whitelabel + custom-domain entitlements).
* A brand profile "Print with Synergy" with the PWS brand colors
  (``#0B5B63`` accent + ``#0E7A84`` hover) pulled from their
  marketing site's ``app/globals.css``.
* The PWS feather wordmark logo uploaded to R2 under
  ``brand-logos/{tenant_id}/{profile_id}.svg`` via the self-serve
  logo upload endpoint. Source: the ``Print With Synergy.svg`` file
  in the ``thinkneverland/print-with-synergy`` GitHub repo.
* The brand profile set as default so every mint inherits PWS
  branding automatically.
* Two custom domains attached via the admin API:
  - ``reports.printwithsynergy.lintpdf.com`` (for static reports)
  - ``app.printwithsynergy.lintpdf.com`` (for interactive viewer)
  The ``probe_pending_custom_domains`` Celery beat will verify them
  within 5-10 minutes once DNS propagates.
* A credentials file at ``scripts/.lintpdf-demo-credentials.env``
  that ``scripts/test_preflight.py`` reads when ``LINTPDF_USE_DEMO=1``.

## Usage

    LINTPDF_ADMIN_KEY=… python3 packages/engine/scripts/seed_pws_demo.py

## Env vars

    LINTPDF_ADMIN_KEY   REQUIRED — X-Admin-Key for engine admin routes
    LINTPDF_API_BASE    default https://api.lintpdf.com
    GITHUB_TOKEN        REQUIRED — fetches the PWS logo from the private
                        ``thinkneverland/print-with-synergy`` repo

## Output

Writes ``scripts/.lintpdf-demo-credentials.env`` (git-ignored)
containing ``LINTPDF_DEMO_TENANT_ID`` and ``LINTPDF_DEMO_API_KEY``.
"""
from __future__ import annotations

import json
import os
import pathlib
import secrets
import sys
import urllib.error
import urllib.request

API = os.environ.get("LINTPDF_API_BASE", "https://api.lintpdf.com").rstrip("/")
ADMIN_KEY = os.environ.get("LINTPDF_ADMIN_KEY")
GH_TOKEN = os.environ.get("GITHUB_TOKEN")

REPO_PATH = (
    "repos/thinkneverland/print-with-synergy/"
    "contents/Logo/Print%20With%20Synergy.svg"
    "?ref=claude/print-synergy-site-SII0Y"
)
CRED_OUT = pathlib.Path(__file__).resolve().parents[3] / "scripts" / ".lintpdf-demo-credentials.env"
LOGO_CACHE = pathlib.Path("/tmp/pws-logo.svg")

PWS = {
    "name": "Print With Synergy (Demo Customer)",
    "contact_email": "demo@printwithsynergy.com",
    "plan": "enterprise",
    "brand_name": "Print with Synergy",
    "primary_color": "#0B5B63",
    "accent_color": "#0E7A84",
    "footer_text": "Automation that actually ships.",
    # We own printwithsynergy.com (in the same Hostinger portfolio as
    # lintpdf.com) and it's marketing-active — this gives a realistic
    # demo URL that customers would see, while also sidestepping the
    # blocked ``*.lintpdf.com`` suffix in validate_custom_domain().
    "reports_domain": "reports.printwithsynergy.com",
    "app_domain": "app.printwithsynergy.com",
}


def _fetch_logo() -> bytes:
    if LOGO_CACHE.exists() and LOGO_CACHE.stat().st_size > 300:
        return LOGO_CACHE.read_bytes()
    if not GH_TOKEN:
        sys.exit("GITHUB_TOKEN not set — can't fetch logo from private repo")
    req = urllib.request.Request(
        f"https://api.github.com/{REPO_PATH}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github.raw",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        svg = resp.read()
    LOGO_CACHE.write_bytes(svg)
    return svg


def _hit(
    method: str,
    path: str,
    *,
    api_key: str | None = None,
    admin: bool = False,
    json_body: dict | None = None,
    files: dict | None = None,
    expect: tuple[int, ...] = (200, 201),
) -> dict | str | None:
    url = f"{API}{path}"
    headers: dict[str, str] = {"Accept": "application/json"}
    if admin:
        headers["X-Admin-Key"] = ADMIN_KEY or ""
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data: bytes | None = None
    if files is not None:
        boundary = f"----pws{secrets.token_hex(8)}"
        parts: list[bytes] = []
        for field, (filename, content, ctype) in files.items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode()
            )
            parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
            parts.append(content if isinstance(content, bytes) else content.encode())
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
            code = resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        code = e.code
    parsed: dict | str
    try:
        parsed = json.loads(body)
    except Exception:
        parsed = body
    status = "OK" if code in expect else "!!"
    snippet = str(parsed)[:100]
    print(f"  {status} {method:6} {path:65} {code}  {snippet}")
    if code not in expect:
        raise SystemExit(f"{method} {path} -> {code}: {body[:300]}")
    return parsed


def find_or_create_tenant() -> str:
    page = _hit(
        "GET", "/api/v1/admin/tenants?page=1&page_size=100", admin=True
    )
    tenants = page.get("tenants", page if isinstance(page, list) else [])
    for t in tenants:
        if t.get("name") == PWS["name"]:
            print(f"  ✓ reusing tenant {t['id']}")
            return t["id"]
    created = _hit(
        "POST",
        "/api/v1/admin/tenants",
        admin=True,
        json_body={
            "name": PWS["name"],
            "plan": PWS["plan"],
            "contact_email": PWS["contact_email"],
        },
    )
    return created["id"]


def mint_api_key(tid: str) -> str:
    """Always mint fresh — the plaintext secret is only returned at creation."""
    out = _hit(
        "POST",
        f"/api/v1/admin/tenants/{tid}/keys",
        admin=True,
        json_body={"label": "pws-demo"},
    )
    return out["raw_key"]


def ensure_brand_profile(tid: str, api_key: str) -> str:
    existing = _hit(
        "GET", f"/api/v1/tenants/{tid}/brand-profiles", api_key=api_key
    )
    profiles = existing.get("profiles", existing if isinstance(existing, list) else [])
    for p in profiles:
        if p.get("name") == PWS["brand_name"]:
            print(f"  ✓ reusing brand profile {p['id']}")
            return p["id"]
    out = _hit(
        "POST",
        f"/api/v1/tenants/{tid}/brand-profiles",
        api_key=api_key,
        json_body={
            "name": PWS["brand_name"],
            "profile_type": "custom",
            "brand_name": PWS["brand_name"],
            "primary_color": PWS["primary_color"],
            "accent_color": PWS["accent_color"],
            "footer_text": PWS["footer_text"],
        },
    )
    return out["id"]


def upload_logo(tid: str, pid: str, api_key: str) -> None:
    svg = _fetch_logo()
    _hit(
        "POST",
        f"/api/v1/tenants/{tid}/brand-profiles/{pid}/logo",
        api_key=api_key,
        files={"file": ("pws-logo.svg", svg, "image/svg+xml")},
    )


def set_default_profile(tid: str, pid: str, api_key: str) -> None:
    _hit(
        "PATCH",
        f"/api/v1/tenants/{tid}/default-brand-profile",
        api_key=api_key,
        json_body={"brand_profile_id": pid},
    )


def attach_custom_domains(tid: str) -> None:
    """Point the tenant at reports.printwithsynergy + app.printwithsynergy.

    The probe_pending_custom_domains beat task verifies + attaches to
    Railway on its next cycle (~5 min).
    """
    _hit(
        "PATCH",
        f"/api/v1/admin/tenants/{tid}/custom-domain",
        admin=True,
        json_body={"domain": PWS["reports_domain"]},
    )
    _hit(
        "PATCH",
        f"/api/v1/admin/tenants/{tid}/app-custom-domain",
        admin=True,
        json_body={"domain": PWS["app_domain"]},
    )


def main() -> int:
    if not ADMIN_KEY:
        sys.exit("LINTPDF_ADMIN_KEY env var is required")
    print("=== Print With Synergy demo seed ===")

    tid = find_or_create_tenant()
    api_key = mint_api_key(tid)
    pid = ensure_brand_profile(tid, api_key)
    upload_logo(tid, pid, api_key)
    set_default_profile(tid, pid, api_key)
    attach_custom_domains(tid)

    CRED_OUT.parent.mkdir(parents=True, exist_ok=True)
    CRED_OUT.write_text(
        f"LINTPDF_DEMO_TENANT_ID={tid}\n"
        f"LINTPDF_DEMO_API_KEY={api_key}\n"
        f"LINTPDF_DEMO_BRAND_PROFILE_ID={pid}\n"
    )
    print(f"\n  ✓ credentials written to {CRED_OUT}")
    print(f"  tenant_id       : {tid}")
    print(f"  api_key         : {api_key[:20]}…")
    print(f"  brand_profile   : {pid}")
    print(f"  reports domain  : https://{PWS['reports_domain']}")
    print(f"  app domain      : https://{PWS['app_domain']}")
    print(
        "\n  Custom domains submitted. Probe task runs every 5 min;"
        " poll /api/v1/admin/custom-domains for verified=true."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
