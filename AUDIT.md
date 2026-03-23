# LintPDF Platform — Feature & Functionality Audit

> **Generated:** 2026-03-17
> **Scope:** 100% coverage of every feature, endpoint, module, and capability across all packages.

---

## Table of Contents

1. [Engine Package (Python/FastAPI)](#1-engine-package)
2. [Web Package (Next.js 15 / React 19)](#2-web-package)
3. [Plugin Package (TypeScript)](#3-plugin-package)
4. [Stripe Package (TypeScript)](#4-stripe-package)
5. [Inference Package (Python/FastAPI on Modal)](#5-inference-package)
6. [Infrastructure](#6-infrastructure)
7. [Security Observations](#7-security-observations)

---

## 1. Engine Package

**Location:** `packages/engine/`
**Stack:** Python 3.12+, FastAPI, SQLAlchemy, Celery, Redis, pikepdf, WeasyPrint

### 1.1 API Routes

#### Health & Status (`routes/health.py`)

| Method | Path             | Auth | Description                                      |
| ------ | ---------------- | ---- | ------------------------------------------------ |
| `GET`  | `/health`        | None | Basic health check — returns `{"status": "ok"}`  |
| `GET`  | `/api/v1/status` | None | Detailed status with DB, Redis, and queue probes |

#### Jobs — Preflight Submission (`routes/jobs.py`, prefix: `/api/v1/jobs`)

| Method   | Path                    | Auth           | Description                                      |
| -------- | ----------------------- | -------------- | ------------------------------------------------ |
| `POST`   | `/api/v1/jobs`          | Tenant API key | Submit PDF for preflight analysis (202 Accepted) |
| `GET`    | `/api/v1/jobs/{job_id}` | Tenant API key | Get job status and results                       |
| `GET`    | `/api/v1/jobs`          | Tenant API key | List jobs for current tenant (paginated)         |
| `DELETE` | `/api/v1/jobs/{job_id}` | Tenant API key | Cancel or delete a job (204)                     |

#### Profiles — Preflight Profiles (`routes/profiles.py`, prefix: `/api/v1/profiles`)

| Method   | Path                            | Auth           | Description                           |
| -------- | ------------------------------- | -------------- | ------------------------------------- |
| `GET`    | `/api/v1/profiles`              | Tenant API key | List all profiles (builtin + custom)  |
| `GET`    | `/api/v1/profiles/{profile_id}` | Tenant API key | Get detailed profile configuration    |
| `POST`   | `/api/v1/profiles`              | Tenant API key | Create custom preflight profile (201) |
| `DELETE` | `/api/v1/profiles/{profile_id}` | Tenant API key | Delete custom profile (204)           |

#### Webhooks (`routes/webhooks.py`, prefix: `/api/v1/webhooks`)

| Method   | Path                            | Auth           | Description                           |
| -------- | ------------------------------- | -------------- | ------------------------------------- |
| `POST`   | `/api/v1/webhooks`              | Tenant API key | Register new webhook endpoint (201)   |
| `GET`    | `/api/v1/webhooks`              | Tenant API key | List all registered webhook endpoints |
| `PATCH`  | `/api/v1/webhooks/{webhook_id}` | Tenant API key | Update webhook URL/events/status      |
| `DELETE` | `/api/v1/webhooks/{webhook_id}` | Tenant API key | Remove webhook endpoint (204)         |

#### Usage & Rate Limits (`routes/usage.py`, prefix: `/api/v1/usage`)

| Method | Path            | Auth           | Description                        |
| ------ | --------------- | -------------- | ---------------------------------- |
| `GET`  | `/api/v1/usage` | Tenant API key | Get current daily rate limit usage |

#### Reports (`routes/reports.py`)

| Method   | Path                                    | Auth           | Description                              |
| -------- | --------------------------------------- | -------------- | ---------------------------------------- |
| `POST`   | `/api/v1/jobs/{job_id}/reports`         | Tenant API key | Generate hosted reports (HTML/PDF) (201) |
| `GET`    | `/api/v1/jobs/{job_id}/reports`         | Tenant API key | List existing report tokens for a job    |
| `DELETE` | `/api/v1/jobs/{job_id}/reports/{token}` | Tenant API key | Revoke report token (204)                |
| `GET`    | `/r/{token}`                            | None (public)  | Serve interactive HTML report            |
| `GET`    | `/r/{token}.pdf`                        | None (public)  | Serve PDF report                         |

#### Admin (`routes/admin.py`, prefix: `/api/v1/admin`, requires `X-Admin-Key`)

**Tenant Management:**

| Method  | Path                                       | Auth      | Description                  |
| ------- | ------------------------------------------ | --------- | ---------------------------- |
| `GET`   | `/api/v1/admin/tenants`                    | Admin key | List all tenants (paginated) |
| `GET`   | `/api/v1/admin/tenants/{tenant_id}`        | Admin key | Get tenant detail            |
| `PATCH` | `/api/v1/admin/tenants/{tenant_id}/plan`   | Admin key | Update tenant plan           |
| `PATCH` | `/api/v1/admin/tenants/{tenant_id}/stripe` | Admin key | Set Stripe IDs               |
| `PATCH` | `/api/v1/admin/tenants/{tenant_id}/status` | Admin key | Activate/suspend tenant      |

**API Key Management:**

| Method   | Path                                              | Auth      | Description                       |
| -------- | ------------------------------------------------- | --------- | --------------------------------- |
| `GET`    | `/api/v1/admin/tenants/{tenant_id}/keys`          | Admin key | List API keys for tenant (masked) |
| `POST`   | `/api/v1/admin/tenants/{tenant_id}/keys`          | Admin key | Generate new API key (201)        |
| `DELETE` | `/api/v1/admin/tenants/{tenant_id}/keys/{key_id}` | Admin key | Revoke API key (204)              |

**Cross-Tenant:**

| Method | Path                 | Auth      | Description                              |
| ------ | -------------------- | --------- | ---------------------------------------- |
| `GET`  | `/api/v1/admin/jobs` | Admin key | List jobs across all tenants (paginated) |

**Entitlements:**

| Method   | Path                                             | Auth      | Description                |
| -------- | ------------------------------------------------ | --------- | -------------------------- |
| `GET`    | `/api/v1/admin/tenants/{tenant_id}/entitlements` | Admin key | Get effective entitlements |
| `PATCH`  | `/api/v1/admin/tenants/{tenant_id}/entitlements` | Admin key | Set entitlement overrides  |
| `DELETE` | `/api/v1/admin/tenants/{tenant_id}/entitlements` | Admin key | Reset to plan defaults     |

**AI Admin:**

| Method | Path                                           | Auth      | Description                 |
| ------ | ---------------------------------------------- | --------- | --------------------------- |
| `GET`  | `/api/v1/admin/tenants/{tenant_id}/ai`         | Admin key | View tenant AI config       |
| `PUT`  | `/api/v1/admin/tenants/{tenant_id}/ai`         | Admin key | Enable/disable AI features  |
| `POST` | `/api/v1/admin/tenants/{tenant_id}/ai/credits` | Admin key | Grant AI credits            |
| `PUT`  | `/api/v1/admin/tenants/{tenant_id}/ai/trial`   | Admin key | Set AI trial period         |
| `GET`  | `/api/v1/admin/ai/usage`                       | Admin key | AI usage across all tenants |

#### Beta Waitlist (`routes/waitlist.py`)

**Public:**

| Method | Path                          | Auth | Description                   |
| ------ | ----------------------------- | ---- | ----------------------------- |
| `GET`  | `/api/v1/beta/status`         | None | Check beta mode status        |
| `POST` | `/api/v1/beta/waitlist`       | None | Join beta waitlist (201)      |
| `GET`  | `/api/v1/beta/waitlist/check` | None | Check if email is on waitlist |

**Admin:**

| Method   | Path                                        | Auth      | Description                       |
| -------- | ------------------------------------------- | --------- | --------------------------------- |
| `GET`    | `/api/v1/admin/waitlist`                    | Admin key | List waitlist entries (paginated) |
| `PATCH`  | `/api/v1/admin/waitlist/{entry_id}/promote` | Admin key | Promote waitlist entry            |
| `PATCH`  | `/api/v1/admin/waitlist/{entry_id}/decline` | Admin key | Decline waitlist entry            |
| `DELETE` | `/api/v1/admin/waitlist/{entry_id}`         | Admin key | Remove waitlist entry (204)       |

#### AI Configuration (`routes/ai_config.py`, prefix: `/api/v1/ai/config`)

| Method   | Path                                | Auth               | Description                       |
| -------- | ----------------------------------- | ------------------ | --------------------------------- |
| `GET`    | `/api/v1/ai/config`                 | Tenant + AI access | Get tenant's AI configuration     |
| `PUT`    | `/api/v1/ai/config`                 | Tenant + AI access | Update AI configuration           |
| `POST`   | `/api/v1/ai/config/logos`           | Tenant + AI access | Upload reference logo (201)       |
| `DELETE` | `/api/v1/ai/config/logos/{logo_id}` | Tenant + AI access | Remove reference logo (204)       |
| `PUT`    | `/api/v1/ai/config/palette`         | Tenant + AI access | Set brand color palette           |
| `PUT`    | `/api/v1/ai/config/dictionary`      | Tenant + AI access | Set custom spell-check dictionary |

#### AI Credits (`routes/ai_credits.py`, prefix: `/api/v1/ai/credits`)

| Method | Path                       | Auth               | Description                      |
| ------ | -------------------------- | ------------------ | -------------------------------- |
| `GET`  | `/api/v1/ai/credits`       | Tenant + AI access | View credit balance and packages |
| `POST` | `/api/v1/ai/credits/topup` | Tenant + AI access | Purchase credit top-up (201)     |

#### AI Usage (`routes/ai_usage.py`, prefix: `/api/v1/ai/usage`)

| Method | Path                      | Auth               | Description                    |
| ------ | ------------------------- | ------------------ | ------------------------------ |
| `GET`  | `/api/v1/ai/usage`        | Tenant + AI access | AI usage report with filtering |
| `GET`  | `/api/v1/ai/usage/trends` | Tenant + AI access | Usage trends for SPC dashboard |

#### AI Presets (`routes/ai_presets.py`, prefix: `/api/v1/ai/presets`)

| Method | Path                        | Auth           | Description                 |
| ------ | --------------------------- | -------------- | --------------------------- |
| `GET`  | `/api/v1/ai/presets`        | Tenant API key | List available AI presets   |
| `GET`  | `/api/v1/ai/presets/{slug}` | Tenant API key | Get specific preset details |

**Built-in presets:** `fda-food-label`, `eu-food-label`, `pharma-eu`, `ghs-chemical`, `packaging-qc`, `brand-compliance`, `full-ai-scan`

#### AI Preflight Profile Generation (`routes/ai_generate.py`)

| Method | Path                                  | Auth               | Description                                      |
| ------ | ------------------------------------- | ------------------ | ------------------------------------------------ |
| `POST` | `/api/v1/preflight-profiles/generate` | Tenant + AI access | Generate Preflight Profile from natural language |

#### AI Report Interpretation (`routes/ai_interpret.py`)

| Method | Path                                      | Auth               | Description                               |
| ------ | ----------------------------------------- | ------------------ | ----------------------------------------- |
| `GET`  | `/api/v1/captains-log/{job_id}/interpret` | Tenant + AI access | Plain language interpretation of findings |

#### Dev Auth (`routes/dev_auth.py`, conditional: `GROUNDED_DEV_AUTH_ENABLED=true`)

| Method | Path                      | Auth      | Description                           |
| ------ | ------------------------- | --------- | ------------------------------------- |
| `POST` | `/api/v1/dev/impersonate` | Admin key | Generate temporary API key for tenant |
| `POST` | `/api/v1/dev/seed`        | Admin key | Seed test tenants and waitlist data   |

### 1.2 Authentication System

- **API key header:** `Authorization: Bearer grd_...`
- **Key hashing:** SHA-256
- **Multi-key support:** `ApiKey` table with rotation, label, prefix, activity tracking
- **Legacy fallback:** `Tenant.api_key_hash` column
- **Admin auth:** `X-Admin-Key` header, string comparison against `settings.admin_api_key`
- **Composite auth:** `require_any_auth()` tries multiple strategies in order
- **Optional auth:** `get_optional_tenant()` for public-facing endpoints

### 1.3 Rate Limiting

- **Backend:** Redis daily counters per tenant
- **Atomicity:** Lua script for atomic increment + expire
- **Tier limits:** Free (50), Starter (500), Growth (5,000), Scale (25,000), Enterprise (100,000)
- **Overage:** Billable overage with spending caps
- **Alerts:** Email warnings at 80% and 100% thresholds

### 1.4 Background Processing (Celery)

| Task                      | Queue                  | Description                                                         |
| ------------------------- | ---------------------- | ------------------------------------------------------------------- |
| `run_preflight`           | `default` / `priority` | PDF download, parse, orchestrate, store findings, dispatch webhooks |
| `cleanup_expired_reports` | `default` (beat)       | Daily cleanup of expired report tokens                              |
| `dispatch_webhook`        | `default`              | Async webhook delivery with retry                                   |

### 1.5 PDF Engine

| Module      | Location       | Description                                                                          |
| ----------- | -------------- | ------------------------------------------------------------------------------------ |
| Parser      | `parser/`      | pikepdf adapter for PDF parsing                                                      |
| Semantic    | `semantic/`    | PDF content stream interpreter (model, graphics state, builder, events, interpreter) |
| Conformance | `conformance/` | PDF/X-4 validation (14 sub-modules) + XMP validation                                 |
| Profiles    | `profiles/`    | Preflight Profile schema, registry, orchestrator                                     |
| Rules       | `rules/`       | Builtin + GWG rule sets                                                              |
| Reports     | `reports/`     | JSON, XML, HTML (Jinja2), PDF (WeasyPrint) generation + service layer                |

### 1.6 Legacy Analyzers (16 categories)

| #   | Analyzer               | File                         |
| --- | ---------------------- | ---------------------------- |
| 1   | BaseAnalyzer           | `analyzers/base.py`          |
| 2   | DocumentAnalyzer       | `analyzers/document.py`      |
| 3   | StructureAnalyzer      | `analyzers/structure.py`     |
| 4   | FontAnalyzer           | `analyzers/font.py`          |
| 5   | ColorAnalyzer          | `analyzers/color.py`         |
| 6   | BarcodeAnalyzer        | `analyzers/barcode.py`       |
| 7   | ImageAnalyzer          | `analyzers/image.py`         |
| 8   | TransparencyAnalyzer   | `analyzers/transparency.py`  |
| 9   | PageGeometryAnalyzer   | `analyzers/page_geometry.py` |
| 10  | OverprintAnalyzer      | `analyzers/overprint.py`     |
| 11  | PrepressAnalyzer       | `analyzers/prepress.py`      |
| 12  | HairlineAnalyzer       | `analyzers/hairline.py`      |
| 13  | AnnotationAnalyzer     | `analyzers/annotation.py`    |
| 14  | MetadataAnalyzer       | `analyzers/metadata.py`      |
| 15  | AccessibilityAnalyzer  | `analyzers/accessibility.py` |
| 16  | ProcessingStepAnalyzer | `analyzers/processing.py`    |

### 1.7 AI Analyzers (32 analyzers across 15 categories)

| #   | Category         | Analyzer                          | File                                                          |
| --- | ---------------- | --------------------------------- | ------------------------------------------------------------- |
| 1   | Barcode          | BarcodeDecode                     | `ai/analyzers/barcode/barcode_decode.py`                      |
| 2   | Barcode          | BarcodeDimensionValidation        | `ai/analyzers/barcode/barcode_dimensions.py`                  |
| 3   | Barcode          | BarcodeContentValidation          | `ai/analyzers/barcode/barcode_content.py`                     |
| 4   | Barcode          | QRValidation                      | `ai/analyzers/barcode/qr_validation.py`                       |
| 5   | Barcode          | BarcodeContentAndQRMatching       | `ai/analyzers/barcode/barcode_content_qr_match.py`            |
| 6   | Barcode          | QRHumanReadableMatching           | `ai/analyzers/barcode/qr_human_readable.py`                   |
| 7   | Barcode          | PharmaSerialization               | `ai/analyzers/barcode/pharma_serialization.py`                |
| 8   | Content Quality  | SpellCheckAnalyzer                | `ai/analyzers/content_quality/spell_check.py`                 |
| 9   | Content Quality  | LanguageDetectionAnalyzer         | `ai/analyzers/content_quality/language_detection.py`          |
| 10  | Content Quality  | DuplicateDetectionAnalyzer        | `ai/analyzers/content_quality/duplicate_detection.py`         |
| 11  | Color Compliance | BrandPaletteAnalyzer              | `ai/analyzers/color_compliance/brand_palette.py`              |
| 12  | Color Compliance | WcagContrastAnalyzer              | `ai/analyzers/color_compliance/wcag_contrast.py`              |
| 13  | Image Analysis   | ImageQualityAnalyzer              | `ai/analyzers/image_analysis/image_quality.py`                |
| 14  | Image Analysis   | NSFWDetectionAnalyzer             | `ai/analyzers/image_analysis/nsfw_detection.py`               |
| 15  | Image Analysis   | ImageSimilarityAnalyzer           | `ai/analyzers/image_analysis/image_similarity.py`             |
| 16  | Regulatory       | FdaNutritionAnalyzer              | `ai/analyzers/regulatory_compliance/fda_nutrition.py`         |
| 17  | Regulatory       | EuFir1169Analyzer                 | `ai/analyzers/regulatory_compliance/eu_fir_1169.py`           |
| 18  | Regulatory       | GhsClpAnalyzer                    | `ai/analyzers/regulatory_compliance/ghs_clp.py`               |
| 19  | Regulatory       | PharmaFontAnalyzer                | `ai/analyzers/regulatory_compliance/pharma_font.py`           |
| 20  | Dieline          | DielineByNameAnalyzer             | `ai/analyzers/dieline_detection/dieline_by_name.py`           |
| 21  | Logo             | LogoDetectionAnalyzer             | `ai/analyzers/logo_verification/logo_detection.py`            |
| 22  | Symbol           | RegulatorySymbolDetectionAnalyzer | `ai/analyzers/symbol_detection/regulatory_symbols.py`         |
| 23  | Symbol           | ProcessingStepsFallbackAnalyzer   | `ai/analyzers/symbol_detection/processing_steps_fallback.py`  |
| 24  | File Comparison  | VersionDiffAnalyzer               | `ai/analyzers/file_comparison/version_diff.py`                |
| 25  | Classification   | FileClassificationAnalyzer        | `ai/analyzers/document_classification/file_classification.py` |
| 26  | Classification   | AutoPreflightProfileAnalyzer      | `ai/analyzers/document_classification/auto_voyage_plan.py`    |
| 27  | Trend Analysis   | SubmissionQualitySPCAnalyzer      | `ai/analyzers/trend_analysis/submission_quality_spc.py`       |
| 28  | Spatial          | SafeZoneViolationsAnalyzer        | `ai/analyzers/spatial_analysis/safe_zone_violations.py`       |
| 29  | Text             | TextAsOutlinesAnalyzer            | `ai/analyzers/text_analysis/text_as_outlines.py`              |
| 30  | NLP              | NLPreflightProfileAnalyzer        | `ai/analyzers/nlp_interfaces/nl_voyage_plan.py`               |
| 31  | NLP              | NLReportInterpretAnalyzer         | `ai/analyzers/nlp_interfaces/nl_report_interpret.py`          |
| 32  | NLP              | MultiLanguageReportsAnalyzer      | `ai/analyzers/nlp_interfaces/multi_language.py`               |

**AI Support Modules:** `ai/base.py`, `ai/registry.py`, `ai/config.py`, `ai/credits.py`, `ai/access.py`, `ai/gpu_client.py`, `ai/rendering.py`

### 1.8 Conformance Validators

| Module                   | File                  | Description                                                                                                                                                                                     |
| ------------------------ | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BaseConformanceValidator | `conformance/base.py` | Abstract base for conformance validators                                                                                                                                                        |
| PdfX4Validator           | `conformance/pdfx4/`  | PDF/X-4 validation (14 sub-modules: annotations, boxes, color, file_structure, font, images, metadata, optional_content, output_intent, resources, restricted_features, security, transparency) |
| XmpMetadata              | `conformance/xmp.py`  | XMP metadata handling                                                                                                                                                                           |

### 1.9 Built-in Profiles

| Profile                  | File                                             |
| ------------------------ | ------------------------------------------------ |
| LintPDF Default          | `profiles/builtin/lintpdf-default.json`          |
| LintPDF Strict           | `profiles/builtin/lintpdf-strict.json`           |
| Advisory Only            | `profiles/builtin/lintpdf-advisory-only.json`    |
| GWG 2022 Coated Offset   | `profiles/builtin/gwg-2022-coated-offset.json`   |
| GWG 2022 Uncoated Offset | `profiles/builtin/gwg-2022-uncoated-offset.json` |
| GWG 2022 Digital Print   | `profiles/builtin/gwg-2022-digital-print.json`   |
| GWG 2022 Newspaper       | `profiles/builtin/gwg-2022-newspaper.json`       |
| GWG 2022 Packaging       | `profiles/builtin/gwg-2022-packaging.json`       |
| GWG 2022 Sign & Display  | `profiles/builtin/gwg-2022-sign-display.json`    |

### 1.10 Multi-Tenancy

- **Plans:** Free, Starter, Growth, Scale, Enterprise
- **Entitlements:** 3-layer merge (plan defaults, legacy columns, JSON overrides)
- **Service:** `tenants/service.py` — tenant CRUD and lookup

### 1.11 Webhook System

- **Signing:** HMAC-SHA256 (`X-LintPDF-Signature`)
- **SSRF protection:** HTTPS-only, blocked hostnames / private IPs
- **Delivery:** Async dispatch via Celery with retry (3 attempts, exponential backoff)
- **Filtering:** Per-tenant webhook endpoints with event type filtering
- **Format:** Pixie Dust payload formatting

### 1.12 Email Service (Resend)

| Function                       | Description                               |
| ------------------------------ | ----------------------------------------- |
| `send_api_key_issued()`        | API key notification to new tenant        |
| `send_job_complete()`          | Preflight job completion notification     |
| `send_rate_limit_warning()`    | Rate limit approaching (80%/100%)         |
| `send_overage_started()`       | Billable overage charges notification     |
| `send_report()`                | Report delivery with hosted link          |
| `send_waitlist_confirmation()` | Beta waitlist signup confirmation         |
| `send_beta_welcome()`          | Welcome email when promoted from waitlist |

### 1.13 Storage (S3/R2)

- Upload / download PDFs, result JSON, reports
- Presigned URL generation
- In-memory backend for testing

### 1.14 Report Generation

| Format | Module                   | Engine                   |
| ------ | ------------------------ | ------------------------ |
| HTML   | `reports/html_report.py` | Jinja2 (autoescape=True) |
| PDF    | `reports/pdf_report.py`  | WeasyPrint               |
| JSON   | `reports/json_report.py` | stdlib json              |
| XML    | `reports/xml_report.py`  | stdlib xml               |

- **Service layer:** `reports/service.py` — generate, store, serve via token-based access
- **Branding:** `BrandingContext` for white-label report customization

### 1.15 Database Models (11 tables)

| Table                       | Description                                                           |
| --------------------------- | --------------------------------------------------------------------- |
| `tenants`                   | Multi-tenant accounts (plan, rate limits, Stripe IDs, branding)       |
| `jobs`                      | Preflight job records (status, profile, file metadata, results)       |
| `job_findings`              | Individual findings from a job (severity, message, page, category)    |
| `api_keys`                  | API keys per tenant (hash, label, prefix, activity tracking)          |
| `webhook_endpoints`         | Webhook registrations (URL, secret, events, active flag)              |
| `custom_profiles`           | Custom Preflight Profiles (tenant-scoped JSON)                        |
| `waitlist_entries`          | Beta waitlist signups (email, company, status)                        |
| `report_tokens`             | Token-based report access (format, expiry, access count)              |
| `tenant_ai_configs`         | AI feature config per tenant (categories, palette, logos, dictionary) |
| `tenant_ai_credit_packages` | Prepaid AI credit packages                                            |
| `ai_usage_logs`             | AI feature usage tracking (category, feature, credits, cost)          |

**Enums:** `TenantPlan` (free/starter/growth/scale/enterprise), `JobStatus` (pending/processing/complete/failed), `WaitlistStatus` (pending/promoted/declined), `AIBillingMode` (pay_per_use/credit_package)

---

## 2. Web Package

**Location:** `packages/web/`
**Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS

### 2.1 Pages

| Route          | File                       | Description        |
| -------------- | -------------------------- | ------------------ |
| `/`            | `app/page.tsx`             | Landing page       |
| `/about`       | `app/about/page.tsx`       | About page         |
| `/features`    | `app/features/page.tsx`    | Features page      |
| `/pricing`     | `app/pricing/page.tsx`     | Pricing page       |
| `/compliance`  | `app/compliance/page.tsx`  | Compliance page    |
| `/ai`          | `app/ai/page.tsx`          | AI features page   |
| `/docs`        | `app/docs/page.tsx`        | Documentation page |
| `/blog`        | `app/blog/page.tsx`        | Blog listing       |
| `/blog/[slug]` | `app/blog/[slug]/page.tsx` | Blog post detail   |
| `/changelog`   | `app/changelog/page.tsx`   | Changelog          |
| `/status`      | `app/status/page.tsx`      | Service status     |
| `/beta/join`   | `app/beta/join/page.tsx`   | Beta join flow     |

**SEO:** `app/sitemap.ts`, `app/robots.ts`

### 2.2 Components

HeroSection, FeaturesSection, AIFeaturesSection, HowItWorksSection, PricingSection, CTASection, Header, Footer, DocsNav, Logo, WaitlistModal, BetaContext, ParticleField, DesktopOnly

### 2.3 Libraries

- `lib/brand` — Brand constants and theming
- `lib/navigation` — Navigation structure
- `lib/blog` — Markdown blog with rehype-sanitize
- `lib/changelog` — Changelog data

### 2.4 Testing

Playwright E2E test configuration

---

## 3. Plugin Package

**Location:** `packages/plugin/`
**Stack:** TypeScript

### 3.1 Plugins (7 Pixie Dust plugins)

`team`, `usage`, `account`, `site-admin`, `waitlist`, `api-keys`, `reports`

### 3.2 Client (`client.ts`)

HTTP client for engine API — jobs, profiles, usage, waitlist admin

### 3.3 Routes

Profile and job routes

### 3.4 Webhook Validation

HMAC-SHA256 timing-safe comparison

### 3.5 Tests

waitlist, client, webhook, config, routes, plugin

---

## 4. Stripe Package

**Location:** `packages/stripe/`
**Stack:** TypeScript

### 4.1 Plugin: `groundedBillingPlugin`

**Routes:**

| Method | Path                                 | Description                     |
| ------ | ------------------------------------ | ------------------------------- |
| `POST` | `/api/grounded/billing/checkout`     | Create Stripe Checkout session  |
| `POST` | `/api/grounded/billing/portal`       | Create Customer Portal session  |
| `GET`  | `/api/grounded/billing/subscription` | Get current subscription status |
| `GET`  | `/api/grounded/billing/invoices`     | List invoices for tenant        |

**Webhook Listeners:**

| Event                           | Action                      |
| ------------------------------- | --------------------------- |
| `customer.subscription.updated` | Sync plan changes to engine |
| `customer.subscription.deleted` | Downgrade tenant to free    |
| `invoice.payment_failed`        | Handle payment failure      |
| `invoice.payment_succeeded`     | Confirm payment             |

### 4.2 Metered Billing

`metered.ts` — Overage billing via Stripe metered usage records

---

## 5. Inference Package

**Location:** `packages/inference/`
**Stack:** Python, FastAPI, Modal (serverless GPU)

### 5.1 Endpoints

| Method | Path                         | Model          | Description                         |
| ------ | ---------------------------- | -------------- | ----------------------------------- |
| `GET`  | `/health`                    | —              | Health check with device info       |
| `POST` | `/inference/image-quality`   | MUSIQ          | Assess image quality metrics        |
| `POST` | `/inference/classify`        | DiT-base       | Classify document/print type        |
| `POST` | `/inference/detect-logo`     | YOLOv8 + CLIP  | Detect and match logos              |
| `POST` | `/inference/detect-nsfw`     | NudeNet        | Detect NSFW content                 |
| `POST` | `/inference/detect-objects`  | Grounding DINO | Detect objects matching text prompt |
| `POST` | `/inference/embed-image`     | DINOv2         | Generate image embeddings           |
| `POST` | `/inference/detect-outlines` | PaddleOCR      | Detect text regions via OCR         |
| `POST` | `/inference/detect-symbols`  | OpenCLIP       | Detect regulatory symbols           |
| `POST` | `/inference/translate`       | OPUS-MT        | Translate text between languages    |

### 5.2 Supporting Modules

- `mcp_server.py` — MCP (Model Context Protocol) server
- `modal_deploy.py` — Modal deployment configuration

---

## 6. Infrastructure

### 6.1 Docker

- **Engine:** Multi-stage build (Python 3.12), non-root user
- **Web:** Multi-stage build (Node 22 Alpine), non-root user
- **VeraPDF:** Sidecar Dockerfile for PDF/A validation
- **docker-compose:** Local dev with 7 services (API, worker, priority worker, webhook worker, beat, web, Redis, Postgres)

### 6.2 Railway

7 `railway.toml` configs: API, worker, priority worker, webhooks worker, beat scheduler, web, VeraPDF sidecar

### 6.3 CI/CD (`.github/workflows/`)

| Workflow       | Description                         |
| -------------- | ----------------------------------- |
| `security.yml` | Semgrep SAST, pip-audit, pnpm audit |
| `ci.yml`       | Build, lint, test                   |
| `deploy.yml`   | Deployment pipeline                 |

---

## 7. Security Observations

The following patterns were identified during this audit:

1. **Timing-unsafe admin key comparison** (`api/auth.py:160`): Uses Python `!=` for admin key comparison instead of `secrets.compare_digest()`. Susceptible to timing attacks.

2. **HTML injection risk in email templates** (`email/service.py`): All email functions use f-strings to interpolate `tenant_name`, `api_key`, `report_url` directly into HTML. While recipients are controlled, `tenant_name` is admin-provided and could contain HTML/JS.

3. **Inference service has no authentication**: All 9 ML inference endpoints accept unauthenticated requests with file uploads. Mitigated by Modal's internal network isolation, but no defense-in-depth.

4. **Dev seed endpoint exposes tracebacks** (`api/routes/dev_auth.py`): The `/api/v1/dev/seed` endpoint returns full Python tracebacks in error responses. Gated by `GROUNDED_DEV_AUTH_ENABLED` flag.

5. **Report HTML serving lacks CSP headers**: The `serve_html_report` endpoint returns `HTMLResponse` without `Content-Security-Policy` headers, allowing potential XSS if report content is compromised.

---

## Summary Statistics

| Category                     | Count |
| ---------------------------- | ----- |
| Total API endpoints (engine) | 55+   |
| Inference endpoints          | 10    |
| Stripe billing routes        | 4     |
| AI analyzers                 | 32    |
| Legacy analyzers             | 16    |
| Database tables              | 11    |
| Email templates              | 7     |
| Web pages                    | 12    |
| Built-in profiles            | 9     |
| AI presets                   | 7     |
| Pixie Dust plugins           | 7     |
| Report formats               | 4     |
| Celery tasks                 | 3     |
| Docker services              | 7     |
| Railway configs              | 7     |
