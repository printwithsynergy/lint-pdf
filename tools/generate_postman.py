#!/usr/bin/env python3
"""Generate Postman v2.1 collections from the LintPDF engine's OpenAPI.

Produces two files under ``docs/postman/``:

* ``lintpdf-all.postman_collection.json``    — every route (admin + tenant)
* ``lintpdf-tenant.postman_collection.json`` — tenant-facing only

Usage:
    python tools/generate_postman.py \
        --full-url https://api.lintpdf.com/openapi.json \
        --tenant-url https://api.lintpdf.com/openapi.tenant.json

or pass ``--spec path/to/openapi.json`` for a local file (useful in CI).

The script is intentionally dependency-free (stdlib only) so it can run
in the deploy pipeline without a pnpm/pip install step. It regroups
routes under Postman folders keyed by the first OpenAPI tag, which
keeps the collection navigable without any manual curation.

Every request carries:

* Base URL variable ``{{BASE_URL}}`` defaulting to
  ``https://api.lintpdf.com``.
* Auth variable ``{{API_KEY}}`` / ``{{ADMIN_KEY}}`` injected as a
  Bearer / ``X-Admin-Key`` header based on the OpenAPI security
  requirement for the operation.
* Example request body derived from the JSON schema's ``example`` /
  ``default`` / generated stubs so the request is runnable immediately.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
import uuid
from pathlib import Path
from typing import Any

POSTMAN_SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"


def load_spec(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as resp:  # noqa: S310
            return json.load(resp)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _example_for_schema(
    schema: dict[str, Any], spec: dict[str, Any], seen: set[str] | None = None
) -> Any:
    """Best-effort example generator for a JSON Schema node.

    Pulls in ``example`` / ``default`` first, then recurses into
    ``properties`` / ``items`` / ``$ref``. Returns ``None`` when the
    schema is too abstract to stub.
    """
    seen = seen or set()
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen:
            return {}
        seen.add(ref)
        parts = ref.split("/")[1:]
        node: Any = spec
        for p in parts:
            if isinstance(node, dict):
                node = node.get(p, {})
        if isinstance(node, dict):
            return _example_for_schema(node, spec, seen)
        return None
    typ = schema.get("type")
    if typ == "string":
        fmt = schema.get("format")
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        if fmt == "date-time":
            return "2026-04-18T00:00:00Z"
        if fmt == "email":
            return "you@example.com"
        enum = schema.get("enum")
        if enum:
            return enum[0]
        return "string"
    if typ == "integer":
        return 0
    if typ == "number":
        return 0.0
    if typ == "boolean":
        return False
    if typ == "array":
        item = schema.get("items") or {}
        return [_example_for_schema(item, spec, seen)]
    if typ == "object" or "properties" in schema:
        props = schema.get("properties", {})
        out: dict[str, Any] = {}
        for name, sub in props.items():
            out[name] = _example_for_schema(sub, spec, seen)
        return out
    # Fall back to an empty object when the schema is unresolvable so
    # Postman still renders a valid JSON body template.
    return {}


def _build_request_body(
    operation: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any] | None:
    body = operation.get("requestBody")
    if not body:
        return None
    content = body.get("content") or {}
    if "application/json" in content:
        schema = content["application/json"].get("schema") or {}
        example = _example_for_schema(schema, spec)
        return {
            "mode": "raw",
            "raw": json.dumps(example, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    if "multipart/form-data" in content:
        return {"mode": "formdata", "formdata": [{"key": "file", "type": "file"}]}
    return None


def _auth_for_operation(
    operation: dict[str, Any], path: str
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    """Pick the right header + Postman auth block for a given op.

    Admin paths use the ``X-Admin-Key`` header (matches the engine's
    ``_verify_admin_key`` dep). Everything else uses Bearer via the
    ``{{API_KEY}}`` collection variable.
    """
    if path.startswith("/api/v1/admin/"):
        headers = [
            {"key": "X-Admin-Key", "value": "{{ADMIN_KEY}}", "type": "text"},
        ]
        auth_block = None  # Postman's auth types don't cover custom headers natively
        return headers, auth_block

    # Stripe webhook receiver doesn't take a bearer — skip auth header.
    if path.startswith("/api/v1/stripe/webhook"):
        return [], None

    headers = [
        {"key": "Authorization", "value": "Bearer {{API_KEY}}", "type": "text"},
    ]
    auth_block = {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{API_KEY}}", "type": "string"}],
    }
    return headers, auth_block


def _convert_path(path: str) -> tuple[str, list[str]]:
    """OpenAPI path template → Postman path tokens + URL string."""
    parts = [seg for seg in path.split("/") if seg]
    tokens: list[str] = []
    for seg in parts:
        if seg.startswith("{") and seg.endswith("}"):
            var = seg[1:-1]
            tokens.append(f":{var}")
        else:
            tokens.append(seg)
    url = "{{BASE_URL}}/" + "/".join(tokens)
    return url, tokens


def _operation_to_request(
    method: str, path: str, operation: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    headers, auth_block = _auth_for_operation(operation, path)
    body = _build_request_body(operation, spec)
    if body and body["mode"] == "raw":
        headers.append(
            {"key": "Content-Type", "value": "application/json", "type": "text"}
        )

    # Path + query params come from ``parameters``.
    query: list[dict[str, Any]] = []
    path_vars: list[dict[str, Any]] = []
    for param in operation.get("parameters", []) or []:
        loc = param.get("in")
        name = param.get("name")
        if not name:
            continue
        if loc == "query":
            query.append(
                {
                    "key": name,
                    "value": str(
                        _example_for_schema(param.get("schema") or {}, spec)
                        or ""
                    ),
                    "disabled": not param.get("required", False),
                    "description": param.get("description") or "",
                }
            )
        elif loc == "path":
            path_vars.append(
                {
                    "key": name,
                    "value": str(
                        _example_for_schema(param.get("schema") or {}, spec)
                        or ""
                    ),
                    "description": param.get("description") or "",
                }
            )

    url, tokens = _convert_path(path)
    req_url: dict[str, Any] = {
        "raw": url + ("?" + "&".join(f"{q['key']}=" for q in query) if query else ""),
        "host": ["{{BASE_URL}}"],
        "path": tokens,
    }
    if query:
        req_url["query"] = query
    if path_vars:
        req_url["variable"] = path_vars

    item: dict[str, Any] = {
        "name": operation.get("summary")
        or operation.get("operationId")
        or f"{method.upper()} {path}",
        "request": {
            "method": method.upper(),
            "header": headers,
            "url": req_url,
            "description": operation.get("description") or "",
        },
        "response": [],
    }
    if auth_block:
        item["request"]["auth"] = auth_block
    if body:
        item["request"]["body"] = body
    return item


def build_collection(spec: dict[str, Any], name: str, description: str) -> dict[str, Any]:
    folders: dict[str, list[dict[str, Any]]] = {}
    for path, ops in sorted(spec.get("paths", {}).items()):
        for method, op in ops.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            tags = op.get("tags") or []
            folder = tags[0] if tags else _folder_fallback(path)
            folders.setdefault(folder, []).append(
                _operation_to_request(method, path, op, spec)
            )

    items: list[dict[str, Any]] = []
    for folder_name in sorted(folders):
        items.append({"name": folder_name, "item": folders[folder_name]})

    return {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "schema": POSTMAN_SCHEMA,
        },
        "item": items,
        "variable": [
            {"key": "BASE_URL", "value": "https://api.lintpdf.com"},
            {"key": "API_KEY", "value": "lpdf_live_your_key_here"},
            {"key": "ADMIN_KEY", "value": "your_admin_key_here"},
        ],
    }


def _folder_fallback(path: str) -> str:
    parts = [seg for seg in path.split("/") if seg and not seg.startswith("{")]
    for seg in parts:
        if seg in ("api", "v1"):
            continue
        return seg.replace("-", " ").title()
    return "General"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-url", default="https://api.lintpdf.com/openapi.json")
    ap.add_argument(
        "--tenant-url", default="https://api.lintpdf.com/openapi.tenant.json"
    )
    ap.add_argument("--spec-full", help="Path to local full spec (overrides --full-url)")
    ap.add_argument(
        "--spec-tenant",
        help="Path to local tenant-slice spec (overrides --tenant-url)",
    )
    ap.add_argument("--out", default="docs/postman")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    full = load_spec(args.spec_full or args.full_url)
    tenant = load_spec(args.spec_tenant or args.tenant_url)

    full_collection = build_collection(
        full,
        name="LintPDF API (All)",
        description=(
            "Complete LintPDF API collection — every route including admin "
            "surface. Generated from https://api.lintpdf.com/openapi.json. "
            "Tenants: use the Tenant collection instead."
        ),
    )
    tenant_collection = build_collection(
        tenant,
        name="LintPDF API (Tenant)",
        description=(
            "Tenant-facing LintPDF routes only. Generated from "
            "https://api.lintpdf.com/openapi.tenant.json. Set {{API_KEY}} "
            "to your ``lpdf_live_...`` key before sending requests."
        ),
    )

    (out_dir / "lintpdf-all.postman_collection.json").write_text(
        json.dumps(full_collection, indent=2), encoding="utf-8"
    )
    (out_dir / "lintpdf-tenant.postman_collection.json").write_text(
        json.dumps(tenant_collection, indent=2), encoding="utf-8"
    )

    # Mirror into packages/app/public/postman/ so the dashboard's
    # /dashboard/admin/postman page serves the same bytes Next.js
    # static-serves. Silently skip if the dashboard workspace isn't
    # present (e.g. someone ran this against a slim checkout).
    repo_root = Path(__file__).resolve().parent.parent
    app_public_postman = repo_root / "packages" / "app" / "public" / "postman"
    if app_public_postman.parent.exists():
        app_public_postman.mkdir(parents=True, exist_ok=True)
        (app_public_postman / "lintpdf-all.postman_collection.json").write_text(
            json.dumps(full_collection, indent=2), encoding="utf-8"
        )
        (app_public_postman / "lintpdf-tenant.postman_collection.json").write_text(
            json.dumps(tenant_collection, indent=2), encoding="utf-8"
        )

    full_count = sum(len(f["item"]) for f in full_collection["item"])
    tenant_count = sum(len(f["item"]) for f in tenant_collection["item"])
    print(f"Wrote {out_dir}/lintpdf-all.postman_collection.json ({full_count} requests)")
    print(
        f"Wrote {out_dir}/lintpdf-tenant.postman_collection.json ({tenant_count} requests)"
    )
    if app_public_postman.parent.exists():
        print(f"Mirrored to {app_public_postman}/")


if __name__ == "__main__":
    main()
