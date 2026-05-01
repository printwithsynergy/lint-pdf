# Extending the engine

Two extension surfaces:

1. **Service overrides** — swap the engine's defaults for email,
   entitlements, billing, auth, and more (FastAPI
   `dependency_overrides` pattern).
2. **Analyzer plugins** — ship a Python package declaring a
   `lintpdf.plugins` entry point; the engine discovers and runs
   your analyzer alongside the built-ins.

This page is the quick reference. Full Protocol details live at
[`docs/plugin-api.md`](plugin-api.md). Architectural context lives
at [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Service overrides

Every cross-boundary call from the engine goes through a Protocol
declared under `lintpdf.services.*`. SaaS hosts override at app
construction:

```python
from lintpdf.api.app import create_app
from lintpdf.services.email import get_email_service

app = create_app()
app.dependency_overrides[get_email_service] = lambda: SendgridEmailService()
```

The defaults that ship in the OSS package:

| Service | Default | Override when |
|---|---|---|
| `EmailService` | `NoOpEmailService` (logs at debug, returns `success=False`) | You want to actually send transactional email (overage, rate-limit warnings, share-link reports, annotation comments). |
| `EntitlementsService` | Forwards to `lintpdf.tenants.entitlements.resolve_entitlements` | You want flat permissive entitlements (single-user OSS deploy) or your own per-customer plan resolver. |
| `BillingService` | Forwards to `lintpdf.billing.file_quota.check_and_consume_file_quota` | You don't have billing — return `None` to always allow. |
| `get_current_tenant` | Requires API-key row in `tenants` table | You're running OSS without the SaaS tenants table — return a sentinel single-user object. |

### `EmailService` — outbound transactional email

```python
from lintpdf.services.email import EmailService, get_email_service

class SendgridEmailService:
    def send(self, to: str, subject: str, body_html: str, body_text: str) -> EmailSendResult:
        # POST to Sendgrid API
        ...
        return EmailSendResult(success=True, provider_message_id=resp["id"])

app.dependency_overrides[get_email_service] = lambda: SendgridEmailService()
```

### `EntitlementsService` — flat permissive override

```python
from lintpdf.services.entitlements import (
    EntitlementsService,
    get_entitlements_service,
)
from lintpdf.tenants.entitlements import TenantEntitlements

class PermissiveEntitlements:
    def resolve(self, tenant):
        return TenantEntitlements(
            rate_limit_daily=1_000_000,
            max_file_size_mb=4096,
            ai_enabled=True,
            annotations_enabled=True,
            capability_fillin_enabled=True,
            # …
        )

app.dependency_overrides[get_entitlements_service] = lambda: PermissiveEntitlements()
```

### `BillingService` — no-op for self-hosted

```python
from lintpdf.services.billing import BillingService, get_billing_service

class NoOpBilling:
    def check_and_consume_file_quota(self, tenant, files_requested, db):
        return None  # always allow

app.dependency_overrides[get_billing_service] = lambda: NoOpBilling()
```

### `get_current_tenant` — single-user override

```python
from lintpdf.api.auth import get_current_tenant

class _SingleUser:
    id = "00000000-0000-0000-0000-000000000001"
    name = "Self-hosted"
    is_active = True
    plan = "enterprise"
    contact_email = "ops@yourorg.example.com"

app.dependency_overrides[get_current_tenant] = lambda: _SingleUser()
```

The engine's `Tenant` model defines the full attribute surface;
your sentinel only needs the fields the routes you actually use
read.

### Combined boot snippet

```python
from fastapi import FastAPI
from lintpdf.api.app import create_app
from lintpdf.api.auth import get_current_tenant
from lintpdf.services.email import get_email_service
from lintpdf.services.entitlements import get_entitlements_service
from lintpdf.services.billing import get_billing_service

app = create_app()
app.dependency_overrides[get_current_tenant] = lambda: _SingleUser()
app.dependency_overrides[get_email_service] = lambda: SendgridEmailService()
app.dependency_overrides[get_entitlements_service] = lambda: PermissiveEntitlements()
app.dependency_overrides[get_billing_service] = lambda: NoOpBilling()
```

---

## Analyzer plugin authoring

Third-party Python packages declare analyzers via
`[project.entry-points."lintpdf.plugins"]`. The engine loads them
at startup and runs them alongside the built-ins.

### Skeleton

```python
# my_plugin/main.py
from lintpdf.plugin.protocol import Analyzer, AnalyzerContext
from lintpdf.plugin.manifest import PluginManifest, Tier
from lintpdf.plugin.findings import Finding, Severity

class HouseStyleCheck:
    manifest = PluginManifest(
        id="acme.house-style",
        version="0.1.0",
        category="branding",
        feature_slug="house_style",
        tier=Tier.CPU,
        credits_per_run=0,
    )

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # ctx.pdf_bytes        — source PDF
        # ctx.config            — resolved profile JSON (no tenant access)
        # ctx.services.*        — Protocol handles for SaaS-coupled features
        # ctx.capabilities.*    — shared work providers (page images, OCR, …)

        findings: list[Finding] = []
        # …your analysis…
        return findings
```

```toml
# my_plugin/pyproject.toml
[project.entry-points."lintpdf.plugins"]
house-style = "my_plugin.main:HouseStyleCheck"
```

After `pip install my_plugin` (alongside `lintpdf`), the engine
auto-discovers the analyzer on next boot — no engine code changes
needed.

### `PluginManifest` fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | Globally unique id (`<org>.<analyzer>`). |
| `version` | semver | Plugin version. Surfaced in the audit log. |
| `category` | string | Logical bucket (`image`, `color`, `barcode`, `regulatory`, `brand`, `structure`). |
| `feature_slug` | string | Slug used in the AI feature registry — pair with an entitlement flag if your analyzer is gated. |
| `tier` | `Tier.{CPU,GPU,EXTERNAL_AI}` | CPU runs in the orchestrator; GPU needs `gpu_client`; external-AI calls an LLM/API and is metered through `cost_cap`. |
| `credits_per_run` | int | Credits consumed per analyze call. `0` = free. |
| `requires_services` | list[str] | Optional. If listed and `ctx.services.<name>` is `None`, self-skip with `return []`. |
| `requires_capabilities` | list[str] | Same idea for shared work providers. |

### `AnalyzerContext` surface

| Attribute | Type | Notes |
|---|---|---|
| `ctx.pdf_bytes` | `bytes` | The source PDF. |
| `ctx.config` | `dict[str, Any]` | Resolved profile JSON. AI knobs are at `ctx.config["ai_config"]`. **No direct tenant or billing access** — use `ctx.services.*`. |
| `ctx.services.database` | DB session | For analyzer-managed state (cache, lookup tables). |
| `ctx.services.renderer` | Page renderer | Render a page to a PIL image at a given DPI. |
| `ctx.services.gpu_client` | GPU inference client \| None | For vision models. `None` on CPU-only deploys — self-skip if your analyzer needs it. |
| `ctx.services.llm_client` | LLM client \| None | For Claude / external LLM calls. `None` when no AI service is configured. |
| `ctx.services.cost_cap` | Cost-cap gate | Wrap LLM calls so the per-tenant cost cap fires. |
| `ctx.services.metering` | Per-call metering | Records the analyzer call in the audit log. |
| `ctx.services.verapdf_client` | veraPDF client \| None | For conformance checks. `None` when no veraPDF sidecar. |
| `ctx.capabilities.page_images` | Shared page-image provider | Wraps `services.renderer` with caching across analyzers. |
| `ctx.capabilities.ocr_text` | Shared OCR result provider | Same idea for OCR. |

### Banned imports

Code under `src/lintpdf/analyzers/**` and
`src/lintpdf/ai/analyzers/**` (and your plugin code) cannot import:

- `lintpdf.tenants.*` → use `ctx.config["ai_config"]` (for AI knobs)
  or `ctx.services.tenants` (for entitlements).
- `lintpdf.api.models.TenantAIConfig` → read from
  `ctx.config["ai_config"]` (a plain dict).
- `lintpdf.audit.metering` → `ctx.services.metering`.
- `lintpdf.audit.cost`, `lintpdf.ai.cost_cap`,
  `lintpdf.ai.credits` → `ctx.services.cost_cap`.
- `lintpdf.api.database` → `ctx.services.database`.
- `lintpdf.ai.gpu_client` → `ctx.services.gpu_client`.
- `lintpdf.conformance.verapdf_client` → `ctx.services.verapdf_client`.

The CI tripwire (`scripts/check_engine_purity.sh`) counts existing
violations and fails CI if the count goes UP. This rule is what
keeps third-party analyzers portable across OSS and SaaS hosts.

### Service-skip pattern

When a plugin lists a service in `requires_services` but
`ctx.services.<name>` is `None` (or capability in
`requires_capabilities` but `ctx.capabilities.<name>` is `None`),
self-skip with `return []` and a `logger.warning(...)`. Never raise
— missing services on OSS hosts must degrade gracefully.

```python
def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
    if ctx.services.gpu_client is None:
        logger.warning("HouseStyleCheck: gpu_client unavailable, skipping")
        return []
    # …
```

---

## Viewer plugins

The embedded React viewer
([@printwithsynergy/loupe-pdf](https://github.com/printwithsynergy/loupe-pdf))
ships its own plugin Protocol — see that repo's docs for slot
registration (`overlay.canvas`, `panel.{right,left,bottom}`,
`toolbar.{top,left,bottom}`, `annotation.source`, `dialog.modal`)
and the `ViewerServices` Protocol layer.

---

## Read more

- [`docs/plugin-api.md`](plugin-api.md) — full Protocol reference,
  capability provider authoring, advanced patterns.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — orchestrator dispatch,
  tier ordering, capability resolution.
- [`docs/CONTRIBUTING.md`](CONTRIBUTING.md) — testing your plugin,
  the engine-purity tripwire, OpenAPI-description discipline.
