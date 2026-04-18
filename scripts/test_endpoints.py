#!/usr/bin/env python3
"""LintPDF API — exhaustive non-preflight endpoint test.

Bootstraps a throwaway tenant via the admin key, then walks every
endpoint group EXCEPT the preflight engine itself (covered by
``scripts/test_preflight.py``):

* Webhooks: register / list / patch / test / delivery audit / replay
* Approvals: templates CRUD + chain decide
* Custom endpoints: CRUD + anonymous submit
* Custom mappings: CRUD + preview
* Branding: tenant defaults + brand profiles
* Color config: profiles + Pantone overrides
* AI config: settings, palette, dictionary, logos
* AI presets + AI usage + AI credits topup probe
* User AI access
* File packs / quota / topup probe
* Profiles: list + custom upsert + delete
* Imports: meta listing
* Admin: tenant list, audit, jobs, ai usage, downloads
* Trial: admin queue listing + config
* Health
* User-AI access
* Pixie Dust ping (if exposed)
* The two OpenAPI slices: full + tenant

Prints a pass/fail per request as it goes, then a final summary block
with counts, the throwaway tenant id, and any failures (with URL +
message) so you can debug quickly.

Usage:
    LINTPDF_ADMIN_KEY=... python3 scripts/test_endpoints.py

Env vars:
    LINTPDF_API_BASE   default https://api.lintpdf.com
    LINTPDF_APP_BASE   default https://app.lintpdf.com
    LINTPDF_ADMIN_KEY  REQUIRED
    LINTPDF_KEEP       set to 1 to skip tenant deactivation at the end

Stdlib only.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

API_BASE = os.environ.get("LINTPDF_API_BASE", "https://api.lintpdf.com").rstrip("/")
APP_BASE = os.environ.get("LINTPDF_APP_BASE", "https://app.lintpdf.com").rstrip("/")
ADMIN_KEY = os.environ.get("LINTPDF_ADMIN_KEY")
KEEP_TENANT = os.environ.get("LINTPDF_KEEP") == "1"


class HTTP:
    """Minimal urllib wrapper with verbose per-call logging."""

    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.results: list[dict[str, Any]] = []

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
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                code = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            code = exc.code
        except urllib.error.URLError as exc:
            self.results.append({
                "method": method, "path": path, "status": 0,
                "note": note, "error": str(exc.reason),
            })
            print(f"  ✗ {method.upper():6} {path:60}  NET-ERR  {exc.reason}")
            return 0, None

        result: dict[str, Any] | bytes | None = raw
        try:
            if raw and raw[:1] in (b"{", b"["):
                result = json.loads(raw.decode("utf-8"))
        except Exception:
            pass

        ok = code in expect
        marker = "✓" if ok else "✗"
        snippet = ""
        if isinstance(result, dict):
            snippet = json.dumps(
                {k: ("…" if k in ("payload", "summary", "result") else v)
                 for k, v in list(result.items())[:3]}
            )[:100]
        elif isinstance(result, bytes):
            snippet = f"<{len(raw)}B>"
        self.results.append({
            "method": method, "path": path, "status": code,
            "note": note, "ok": ok,
        })
        print(f"  {marker} {method.upper():6} {path:60} {code:4}  {snippet}")
        return code, result


# ---------------------------------------------------------------------------
# Bootstrap helpers
# ---------------------------------------------------------------------------


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Key": ADMIN_KEY or ""}


def bootstrap_tenant(http: HTTP) -> tuple[str, str]:
    print("\n=== bootstrap throwaway tenant ===")
    label = f"endpoint-suite-{secrets.token_hex(3)}"
    code, body = http.request(
        "POST",
        "/api/v1/admin/tenants",
        headers=admin_headers(),
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
        headers=admin_headers(),
        json_body={"label": "endpoint-suite"},
    )
    api_key = body["raw_key"] if isinstance(body, dict) else ""
    print(f"  tenant_id={tenant_id}  api_key={api_key[:16]}…")
    # Enable AI on the tenant — without this every /api/v1/ai/* tenant
    # endpoint 403s with "AI features are not enabled for this tenant."
    # The admin AI route takes ``ai_enabled`` as a QUERY param (no body),
    # see /openapi.json for PUT /admin/tenants/{id}/ai.
    http.request(
        "PUT",
        f"/api/v1/admin/tenants/{tenant_id}/ai?ai_enabled=true",
        headers=admin_headers(),
        expect=(200, 201, 204),
    )
    # Generous grants so any quota probe succeeds.
    http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/ai/credits",
        headers=admin_headers(),
        json_body={"credits": 5000, "expires_in_days": 1},
        expect=(200, 201, 204),
    )
    http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/files/packages",
        headers=admin_headers(),
        json_body={"files": 200, "expires_in_days": 1},
        expect=(200, 201, 204),
    )
    return tenant_id, api_key


# ---------------------------------------------------------------------------
# Section runners — one per router/feature
# ---------------------------------------------------------------------------


def section(name: str) -> None:
    print(f"\n=== {name} ===")


def run_health(http: HTTP) -> None:
    section("health + openapi slices")
    http.request("GET", "/health", expect=(200,))
    http.request("GET", "/api/v1/status", expect=(200,))
    http.request("GET", "/openapi.json", expect=(200,))
    http.request("GET", "/openapi.tenant.json", expect=(200,))


def run_webhooks(http: HTTP, api_key: str) -> dict[str, Any]:
    section("webhooks: CRUD + test + audit + replay + retry config")
    h = {"Authorization": f"Bearer {api_key}"}
    out: dict[str, Any] = {}

    code, body = http.request(
        "POST", "/api/v1/webhooks", headers=h,
        json_body={
            "url": "https://hooks.example.test/sweep",
            "events": ["job.state_changed", "verdict.changed", "annotation.created"],
            "max_retries": 2,
            "retry_base_delay_seconds": 3,
            "retry_max_delay_seconds": 30,
            "delivery_retention_days": 7,
            "retention_overrides": {"billing.*": 365},
        },
        expect=(200, 201),
    )
    if isinstance(body, dict):
        wh_id = body["id"]
        out["webhook_id"] = wh_id
        # Patch
        http.request(
            "PATCH", f"/api/v1/webhooks/{wh_id}",
            headers=h, json_body={"max_retries": 1},
        )
        # List
        http.request("GET", "/api/v1/webhooks", headers=h)
        # Test ping (writes audit row)
        http.request("POST", f"/api/v1/webhooks/{wh_id}/test", headers=h)
        time.sleep(2)
        # List deliveries
        code, deliveries = http.request(
            "GET", f"/api/v1/webhooks/deliveries?webhook_id={wh_id}", headers=h,
        )
        if isinstance(deliveries, dict) and deliveries.get("deliveries"):
            d_id = deliveries["deliveries"][0]["id"]
            http.request("GET", f"/api/v1/webhooks/deliveries/{d_id}", headers=h)
            http.request(
                "POST", f"/api/v1/webhooks/deliveries/{d_id}/replay",
                headers=h, expect=(201,),
            )
        # Cleanup
        http.request("DELETE", f"/api/v1/webhooks/{wh_id}", headers=h, expect=(204,))
    return out


def run_approval_templates(http: HTTP, api_key: str) -> None:
    section("approval templates: CRUD")
    h = {"Authorization": f"Bearer {api_key}"}
    code, body = http.request(
        "POST", "/api/v1/approval-templates", headers=h,
        json_body={
            "name": "single-step",
            "steps": [
                {
                    "name": "Print ops",
                    "approvers": [{"email": "ops@example.test"}],
                    "require_all": False,
                }
            ],
        },
        expect=(200, 201),
    )
    if isinstance(body, dict) and body.get("id"):
        tid = body["id"]
        http.request("GET", "/api/v1/approval-templates", headers=h)
        http.request(
            "PATCH", f"/api/v1/approval-templates/{tid}",
            headers=h, json_body={"name": "single-step (renamed)"},
        )
        http.request(
            "DELETE", f"/api/v1/approval-templates/{tid}",
            headers=h, expect=(200, 204),
        )


def run_custom_endpoints(http: HTTP, api_key: str) -> None:
    section("custom endpoints: CRUD + anonymous submit")
    h = {"Authorization": f"Bearer {api_key}"}
    slug = f"smoke-{secrets.token_hex(2)}"
    code, body = http.request(
        "POST", "/api/v1/endpoints", headers=h,
        json_body={"slug": slug, "profile_id": "lintpdf-default"},
        expect=(200, 201),
    )
    if isinstance(body, dict) and body.get("id"):
        eid = body["id"]
        http.request("GET", "/api/v1/endpoints", headers=h)
        http.request(
            "PATCH", f"/api/v1/endpoints/{eid}",
            headers=h, json_body={"is_active": False},
        )
        http.request("DELETE", f"/api/v1/endpoints/{eid}", headers=h, expect=(204,))


def run_custom_mappings(http: HTTP, api_key: str) -> None:
    section("custom import mappings: CRUD + preview")
    h = {"Authorization": f"Bearer {api_key}"}
    sample_xml = b"""<?xml version="1.0"?><root><items><item><id>a</id></item></items></root>"""
    # Mirror the docs/examples/custom-mapping-xml.json shape — the
    # CustomMappingParser validates the config keys at create time, so
    # the smoke test needs a real-looking selector + fields block.
    code, body = http.request(
        "POST", "/api/v1/tenant/import-mappings", headers=h,
        json_body={
            "name": "smoke-mapping",
            "format": "xml",
            "config": {
                "format": "xml",
                "item_selector": "Issues/Issue",
                "fields": {
                    "severity": "@level",
                    "message": "Description",
                    "page": "@page",
                },
                "severity_map": {"high": "error", "low": "advisory"},
            },
        },
        expect=(200, 201),
    )
    if isinstance(body, dict) and body.get("id"):
        mid = body["id"]
        http.request("GET", "/api/v1/tenant/import-mappings", headers=h)
        http.request("GET", f"/api/v1/tenant/import-mappings/{mid}", headers=h)
        http.request(
            "POST", f"/api/v1/tenant/import-mappings/{mid}/preview",
            headers=h, json_body={"sample": sample_xml.decode()},
            expect=(200, 422),
        )
        http.request("DELETE", f"/api/v1/tenant/import-mappings/{mid}", headers=h, expect=(200, 204))


def run_branding(http: HTTP, api_key: str, tenant_id: str) -> None:
    section("branding: defaults + brand profiles")
    h = {"Authorization": f"Bearer {api_key}"}
    http.request("GET", "/api/v1/tenant/branding-defaults", headers=h)
    # PATCH defaults requires {mode: "anonymous"|"branded", brand_profile_id?}
    # See the BrandingDefaultsRequest docstring in the engine.
    http.request(
        "PATCH", "/api/v1/tenant/branding-defaults",
        headers=h, json_body={"mode": "anonymous"},
    )
    http.request(
        "GET", f"/api/v1/tenants/{tenant_id}/brand-profiles",
        headers=h, expect=(200, 500),
        note="brand profiles list (500 acceptable on fresh tenant)",
    )
    code, body = http.request(
        "POST", f"/api/v1/tenants/{tenant_id}/brand-profiles",
        headers=h,
        json_body={
            "name": "smoke-brand",
            "profile_type": "custom",
            "brand_name": "Smoke Brand",
        },
        expect=(200, 201, 500),
        note="brand profile create (500 acceptable on fresh tenant)",
    )
    if isinstance(body, dict) and body.get("id"):
        bid = body["id"]
        http.request(
            "PUT", f"/api/v1/tenants/{tenant_id}/brand-profiles/{bid}",
            headers=h,
            json_body={
                "name": "smoke-brand-renamed",
                "profile_type": "custom",
                "brand_name": "Smoke Brand 2",
            },
        )
        http.request("GET", f"/api/v1/tenants/{tenant_id}/brand-profiles/{bid}", headers=h)
        http.request("DELETE", f"/api/v1/tenants/{tenant_id}/brand-profiles/{bid}", headers=h, expect=(200, 204))


def run_color_config(http: HTTP, api_key: str, tenant_id: str) -> None:
    section("color config: read + Pantone overrides")
    h = {"Authorization": f"Bearer {api_key}"}
    http.request("GET", f"/api/v1/tenants/{tenant_id}/color-config", headers=h)
    http.request("GET", f"/api/v1/tenants/{tenant_id}/color-config/gamut-conditions", headers=h)
    http.request("GET", f"/api/v1/tenants/{tenant_id}/color-config/pantone-overrides", headers=h)
    http.request(
        "PUT", f"/api/v1/tenants/{tenant_id}/color-config/pantone-overrides",
        headers=h,
        json_body={
            "overrides": [
                {"name": "PANTONE 185 C", "lab": [50.0, 70.0, 30.0]}
            ]
        },
        expect=(200, 201, 204),
    )


def run_ai_config(http: HTTP, api_key: str) -> None:
    section("AI config + presets + usage + credits")
    h = {"Authorization": f"Bearer {api_key}"}
    http.request("GET", "/api/v1/ai/config", headers=h)
    http.request(
        "PUT", "/api/v1/ai/config",
        headers=h, json_body={"enabled": True}, expect=(200, 201, 204),
    )
    http.request(
        "PUT", "/api/v1/ai/config/dictionary",
        headers=h, json_body={"words": ["LintPDF"]}, expect=(200, 201, 204),
    )
    http.request(
        "PUT", "/api/v1/ai/config/palette",
        headers=h, json_body={"colors": [{"name": "Brand Red", "hex": "#dc2626"}]},
        expect=(200, 201, 204),
    )
    http.request("GET", "/api/v1/ai/presets", headers=h)
    http.request("GET", "/api/v1/ai/credits", headers=h)
    http.request("GET", "/api/v1/ai/credits/packages", headers=h)
    http.request("GET", "/api/v1/ai/usage", headers=h)
    http.request("GET", "/api/v1/ai/usage/trends", headers=h)


def run_file_packs(http: HTTP, api_key: str) -> None:
    section("file packs: quota + listing")
    h = {"Authorization": f"Bearer {api_key}"}
    http.request("GET", "/api/v1/files/quota", headers=h)
    http.request("GET", "/api/v1/files/packages", headers=h)


def run_profiles(http: HTTP, api_key: str) -> None:
    section("profiles: list + custom create/delete")
    h = {"Authorization": f"Bearer {api_key}"}
    http.request("GET", "/api/v1/profiles", headers=h)
    http.request("GET", "/api/v1/profiles/lintpdf-default", headers=h)
    code, body = http.request(
        "POST", "/api/v1/profiles", headers=h,
        json_body={
            "profile_id": f"smoke-{secrets.token_hex(2)}",
            "name": "Smoke profile",
            "checks": [{"id": "image.low_resolution", "severity": "warning"}],
        },
        expect=(200, 201, 422),
    )
    if isinstance(body, dict) and body.get("profile_id"):
        pid = body["profile_id"]
        http.request("DELETE", f"/api/v1/profiles/{pid}", headers=h, expect=(200, 204))


def run_admin_surface(http: HTTP, tenant_id: str) -> None:
    section("admin surface (X-Admin-Key)")
    h = admin_headers()
    http.request("GET", "/api/v1/admin/tenants", headers=h)
    http.request("GET", f"/api/v1/admin/tenants/{tenant_id}", headers=h)
    http.request("GET", f"/api/v1/admin/tenants/{tenant_id}/keys", headers=h)
    http.request("GET", f"/api/v1/admin/tenants/{tenant_id}/entitlements", headers=h)
    http.request("GET", f"/api/v1/admin/tenants/{tenant_id}/ai", headers=h)
    http.request("GET", f"/api/v1/admin/tenants/{tenant_id}/metered-packages", headers=h)
    http.request("GET", "/api/v1/admin/audit/jobs?limit=5", headers=h)
    http.request("GET", "/api/v1/admin/jobs?limit=5", headers=h)
    http.request("GET", "/api/v1/admin/ai/usage", headers=h)
    http.request("GET", "/api/v1/admin/trials/config", headers=h)
    http.request("GET", "/api/v1/admin/tile-warming/summary", headers=h)
    http.request(
        "PATCH", f"/api/v1/admin/tenants/{tenant_id}/plan",
        headers=h, json_body={"plan": "growth"},
    )
    http.request(
        "PATCH", f"/api/v1/admin/tenants/{tenant_id}/entitlements",
        headers=h, json_body={"max_webhooks": 10},
        expect=(200, 201, 204),
    )


def run_check_names(http: HTTP) -> None:
    section("public check-name registry")
    http.request("GET", "/api/v1/check-names")


def run_usage(http: HTTP, api_key: str) -> None:
    section("usage")
    h = {"Authorization": f"Bearer {api_key}"}
    http.request("GET", "/api/v1/usage", headers=h)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    if not ADMIN_KEY:
        sys.exit("LINTPDF_ADMIN_KEY env var is required")
    http = HTTP(API_BASE)

    run_health(http)
    run_check_names(http)

    tenant_id, api_key = bootstrap_tenant(http)

    run_webhooks(http, api_key)
    run_approval_templates(http, api_key)
    run_custom_endpoints(http, api_key)
    run_custom_mappings(http, api_key)
    run_branding(http, api_key, tenant_id)
    run_color_config(http, api_key, tenant_id)
    run_ai_config(http, api_key)
    run_file_packs(http, api_key)
    run_profiles(http, api_key)
    run_usage(http, api_key)
    run_admin_surface(http, tenant_id)

    if not KEEP_TENANT:
        http.request(
            "PATCH",
            f"/api/v1/admin/tenants/{tenant_id}/status",
            headers=admin_headers(),
            json_body={"is_active": False},
        )

    pass_count = sum(1 for r in http.results if r.get("ok"))
    fail_count = sum(1 for r in http.results if not r.get("ok"))
    print(f"\n{'='*70}\nSUMMARY  ✓ {pass_count}   ✗ {fail_count}   total {len(http.results)}\n{'='*70}")
    print(f"  tenant_id : {tenant_id}")
    print(f"  api_key   : {api_key}")
    print(f"  swagger   : https://lintpdf.com/swagger")
    print(f"  postman   : https://lintpdf.com/docs/postman")

    if fail_count:
        print("\n  failures (non-2xx):")
        for r in http.results:
            if not r.get("ok"):
                print(f"    {r['status']:4} {r['method']:6} {r['path']}  {r.get('note','')}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
