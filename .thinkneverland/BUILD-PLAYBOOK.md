# BUILD-PLAYBOOK.md — LintPDF
# Module-by-module engineering playbook for AI-assisted development.
# Each phase maps to Linear cards. Read ATLAS-CONTEXT.md before starting.

---

## BUILD SEQUENCE OVERVIEW

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9
Parser    Semantic   Content    Analyzers  Conform.   Rules     API       Deploy    Launch
Layer     Model      Stream     (5 modules) Standards  + Plans   + Queue   + Docker  Prep
                     Interp.
```

| Phase | Modules | Est. Week | Complexity | Cards |
|-------|---------|-----------|------------|-------|
| 1 | ParserAdapter + PikePDFAdapter | Wk 1 | M | 3-4 |
| 2 | SemanticModel | Wk 2 | L | 4-5 |
| 3 | ContentStreamInterpreter | Wk 2-3 | XL | 6-8 |
| 4 | FontAnalyzer, ImageAnalyzer, ColorAnalyzer, TransparencyAnalyzer, OverprintAnalyzer, PageGeometryAnalyzer | Wk 3-5 | L | 10-12 |
| 5 | PDFXValidator, PDFAValidator (veraPDF) | Wk 5-6 | L | 4-5 |
| 6 | RuleEngine, RulesetLoader, ProfileRegistry | Wk 6-7 | L | 5-6 |
| 7 | FastAPI + Celery + TenantManager + Radio | Wk 7-9 | L | 8-10 |
| 8 | Docker + Railway + CI/CD | Wk 9-10 | M | 4-5 |
| 9 | Docs + SDKs + QA | Wk 10-12 | M | 5-7 |

---

## PHASE 0: PROJECT SCAFFOLD

### Before any module work

**Card: GRD-001 — Project scaffold and CI setup**

Acceptance Criteria:
1. Python package at `src/grounded/` with `__init__.py`, `py.typed`
2. `pyproject.toml` with dependencies: pikepdf, fastapi, celery, redis, psycopg2-binary, weasyprint, jinja2, pydantic, httpx
3. Dev dependencies: pytest, pytest-asyncio, ruff, mypy, coverage
4. `docker-compose.yml` with redis, postgres, verapdf services
5. `Dockerfile` for the API/worker
6. `.github/workflows/ci.yml` — lint, typecheck, test
7. `src/grounded/exceptions.py` — base exception hierarchy
8. `tests/` directory with `conftest.py` and fixtures
9. `ruff.toml` and `mypy.ini` config
10. `pytest` runs green with 0 tests collected

```
src/grounded/
├── __init__.py
├── py.typed
├── exceptions.py           # PDFStructureError, PDFParseError, etc.
├── parser/
├── semantic/
├── analyzers/
├── conformance/
├── rules/
├── profiles/
├── reports/
├── api/
├── queue/
├── tenants/
└── webhooks/
```

**Exception hierarchy:**
```python
class GroundedError(Exception): ...
class PDFStructureError(GroundedError): ...
class PDFParseError(GroundedError): ...
class PDFStreamEncodingError(GroundedError): ...
class PDFObjectNotFound(GroundedError): ...
class InvalidBoxError(GroundedError): ...
class InvalidPageError(GroundedError): ...
class FlightPlanValidationError(GroundedError): ...
class RuleRegistrationError(GroundedError): ...
```

---

## PHASE 1: PARSER LAYER

### Module 1a: ParserAdapter (Abstract Interface)

**Card: GRD-002 — ParserAdapter abstract base class**

File: `src/grounded/parser/adapter.py`

Acceptance Criteria:
1. `ParserAdapter` ABC with methods: `open()`, `get_page()`, `get_catalog()`, `get_content_stream()`, `get_resources()`, `resolve_reference()`, `get_page_tree()`
2. Dataclasses: `PdfStream`, `PdfObject`, `PdfDocument`, `PdfPage`
3. All methods have type hints and docstrings with ISO references
4. Tests: interface contract tests using mock implementation
5. `mypy src/grounded/parser/ --strict` passes

Reference: `lintpdf-research/implementation-plan.md` Module 1 for interface definition.

### Module 1b: PikePDFAdapter (Concrete Implementation)

**Card: GRD-003 — PikePDFAdapter implementation**

File: `src/grounded/parser/pikepdf_adapter.py`

Acceptance Criteria:
1. `PikePDFAdapter` implements all `ParserAdapter` methods
2. Opens PDFs from bytes using `pikepdf.Pdf.open(BytesIO(...))`
3. Extracts page metadata: MediaBox, CropBox, TrimBox, BleedBox, ArtBox, Rotate, UserUnit
4. Extracts and decompresses content streams
5. Resolves indirect references
6. Raises LintPDF-specific exceptions for all failure modes
7. Object graph traversal with memoization
8. Tests against veraPDF corpus (10+ files minimum), Isartor malformed set (5+ files)
9. Tests against linearized, incremental update, and object stream PDFs
10. Benchmark: 100MB PDF parses in <3 seconds

Dependencies: pikepdf

**Key implementation notes:**
- Use `pikepdf.Pdf.open()` not `pikepdf.open()` (the latter is deprecated)
- Access pages via `pdf.pages[index]` (0-indexed, but our PdfPage is 1-indexed)
- Content stream: `page.get('/Contents')` — may be array or single stream
- Box values: `page.get('/MediaBox')` returns pikepdf.Array → convert to tuple
- Handle missing boxes gracefully (CropBox defaults to MediaBox per spec)

### Module 1c: Test corpus setup

**Card: GRD-004 — Test corpus download and fixtures**

Acceptance Criteria:
1. `tests/fixtures/download_corpus.py` script to fetch veraPDF test suite + Isartor files
2. `tests/conftest.py` fixtures: `sample_pdf_bytes`, `malformed_pdf_bytes`, `linearized_pdf_bytes`
3. `tests/corpus/` directory (gitignored) with downloaded test files
4. CI downloads corpus in setup step
5. `pytest -m corpus` marker for slow corpus tests
6. At least 20 test PDFs covering: valid, malformed, encrypted, linearized, incremental, object-stream, 100+ pages

---

## PHASE 2: SEMANTIC MODEL

### Module 2: SemanticModel

**Card: GRD-005 — SemanticModel dataclasses**

File: `src/grounded/semantic/model.py`

Acceptance Criteria:
1. Dataclasses: `PdfBox`, `PdfFont`, `PdfColorSpace`, `PdfImage`, `PdfPage` (enriched), `PdfDocument` (enriched)
2. `PdfBox` with validation (`x0 < x1`, `y0 < y1`), `contains_point()`, `area()`
3. `PdfFont.is_standard_14()` method
4. `PdfPage.effective_width` and `effective_height` properties (rotation-aware)
5. Tests: box validation, font Standard 14 detection, page dimensions with rotation

Reference: `lintpdf-research/implementation-plan.md` Module 2 for class definitions.

**Card: GRD-006 — SemanticModel builder**

File: `src/grounded/semantic/builder.py`

Acceptance Criteria:
1. `SemanticModelBuilder` class with `build(ParserAdapter, PdfDocument) → PdfDocument` (enriched)
2. Resolves resource inheritance by walking page tree ancestors
3. Extracts and normalizes fonts (embedding status, subsetting, encoding)
4. Extracts color spaces (Device, CIE, ICC, Indexed, Separation, DeviceN)
5. Validates box hierarchy (MediaBox ≥ CropBox ≥ BleedBox ≥ TrimBox)
6. Resolves Rotate and UserUnit
7. Tests: 3-level page tree inheritance, box hierarchy validation, font extraction from resources

**Inheritance algorithm** (ISO 32000-2 §7.7.3.4):
- Inheritable properties: Resources, MediaBox, CropBox, Rotate
- Walk `/Parent` chain until property found or root reached
- MediaBox MUST exist somewhere in chain — raise `InvalidPageError` if missing
- CropBox defaults to MediaBox; BleedBox/TrimBox/ArtBox default to CropBox

---

## PHASE 3: CONTENT STREAM INTERPRETER

This is the most complex module. Split into multiple cards.

### Module 3a: GraphicsState + TransformationMatrix

**Card: GRD-007 — GraphicsState and TransformationMatrix**

File: `src/grounded/semantic/graphics_state.py`

Acceptance Criteria:
1. `TransformationMatrix` with `multiply()` and `extract_scale()` methods
2. Matrix multiplication matches ISO 32000-2 §8.3.4 formula
3. `GraphicsState` dataclass with all fields (CTM, color, opacity, blend mode, overprint, font, clipping)
4. `GraphicsState.copy()` deep copies mutable fields
5. Tests: identity matrix, known scale/rotation/skew matrices, multiply correctness, extract_scale accuracy

### Module 3b: Semantic Events

**Card: GRD-008 — Content stream semantic events**

File: `src/grounded/semantic/events.py`

Acceptance Criteria:
1. Base class `ContentStreamEvent` with `operator`, `page_num`, `operator_index`
2. Event dataclasses: `ImagePlacedEvent`, `TextRenderedEvent`, `ColorChangedEvent`, `OpacityChangedEvent`, `OverprintModeChangedEvent`, `TransparencyGroupEnteredEvent`, `FormXObjectEnteredEvent`, `PathPaintingEvent`, `ClippingPathSetEvent`
3. All events are frozen dataclasses (immutable after creation)
4. Tests: event construction, field validation

### Module 3c: Content Stream Interpreter Core

**Card: GRD-009 — ContentStreamInterpreter core (CRITICAL operators)** `opus`

File: `src/grounded/semantic/interpreter.py`

Acceptance Criteria:
1. `ContentStreamInterpreter` class with `interpret(page, resources) → List[ContentStreamEvent]`
2. Uses `pikepdf.parse_content_stream()` for tokenization (MVP approach)
3. Implements all 18 CRITICAL operators: q, Q, cm, gs, Do, Tf, Tj, TJ, BT, ET, Tm, sc/scn, SC/SCN, cs/CS, rg/RG, k/K, g/G, BI/ID/EI
4. State stack: q pushes copy, Q pops
5. CTM tracking: cm concatenates matrix
6. gs handler: reads ExtGState dict for ca, CA, BM, OP, op, OPM
7. Do handler: distinguishes Image XObject vs Form XObject, emits appropriate event
8. Font tracking: Tf sets current font name and size
9. Text operators: emit TextRenderedEvent with current graphics state
10. Color operators: update state AND emit ColorChangedEvent
11. Inline image: delegate to pikepdf's inline image handling
12. Graceful error handling: continue on unrecognized operators, log warnings
13. State stack balance validation at end of stream
14. Tests: one test per CRITICAL operator, state stack balance, CTM math

**Operator dispatch pattern:**
```python
OPERATOR_HANDLERS = {
    'q': self.handle_q,
    'Q': self.handle_Q,
    'cm': self.handle_cm,
    'gs': self.handle_gs,
    'Do': self.handle_Do,
    'Tf': self.handle_Tf,
    'Tj': self.handle_Tj,
    'TJ': self.handle_TJ,
    # ... etc
}
```

### Module 3d: Form XObject Recursion

**Card: GRD-010 — Form XObject recursion with cycle detection** `opus`

Acceptance Criteria:
1. When `Do` references Form XObject: save state (q), apply form Matrix to CTM, interpret form stream, restore state (Q)
2. Merge form Resources with page Resources (form overrides page)
3. Cycle detection via visited set of `(obj_number, gen_number)` tuples
4. Depth limit: 32 levels (emit warning and stop recursion)
5. Events from nested forms include absolute page coordinates (CTM fully resolved)
6. Tests: 2-level nesting, cycle detection (self-referencing form), depth limit, CTM multiplication through nesting

### Module 3e: IMPORTANT Operators

**Card: GRD-011 — ContentStreamInterpreter IMPORTANT operators**

Acceptance Criteria:
1. Path construction: m, l, c, v, y, h, re — track current path points for bounding box
2. Path painting: S, s, f, F, f*, B, B*, b, b*, n — emit PathPaintingEvent with fill/stroke flags
3. Clipping: W, W* — emit ClippingPathSetEvent
4. Text positioning: Td, TD, T* — update text matrix
5. Text showing: ', " — emit TextRenderedEvent (same as Tj but with line advance)
6. Tests: path bounding box calculation, clipping event, text position tracking

---

## PHASE 4: ANALYZERS

### Module 4a: ImageAnalyzer

**Card: GRD-012 — ImageAnalyzer with DPI calculation**

File: `src/grounded/analyzers/image.py`

Acceptance Criteria:
1. `ImageAnalyzer` processes `ImagePlacedEvent` list from interpreter
2. DPI calculation: `EffectiveDPI = pixels / (sqrt(a²+c²) / 72)` for width, `pixels / (sqrt(b²+d²) / 72)` for height
3. Handles degenerate CTM (zero scale) gracefully
4. Checks generated: GRD_IMG_001 (low DPI), GRD_IMG_002 (excessive DPI), GRD_IMG_003 (color space mismatch), GRD_IMG_004 (compression efficiency), GRD_IMG_005 (inline image detected)
5. DPI thresholds configurable per Ruleset
6. Tests: known CTM → known DPI, rotated images, nested form images, degenerate matrix

### Module 4b: FontAnalyzer

**Card: GRD-013 — FontAnalyzer (10-point check list)**

File: `src/grounded/analyzers/font.py`

Acceptance Criteria:
1. 10 checks: GRD_FONT_001 through GRD_FONT_010
2. Embedding detection via FontDescriptor → FontFile/FontFile2/FontFile3
3. Subsetting detection via 6-char prefix + "+"
4. Standard 14 font identification
5. Type3 font flagging
6. CID font encoding validation (CIDSystemInfo, ToUnicode, CIDToGIDMap)
7. Tests: embedded font, non-embedded font, subsetted font, Standard 14, Type3, CID font

### Module 4c: ColorAnalyzer

**Card: GRD-014 — ColorAnalyzer with TAC calculation**

File: `src/grounded/analyzers/color.py`

Acceptance Criteria:
1. TAC (Total Area Coverage) calculation for CMYK: sum of C+M+Y+K percentages
2. Prohibited color space detection (Lab, CalGray, CalRGB in PDF/X-4 context)
3. ICC profile presence validation
4. DeviceRGB in CMYK workflow detection
5. Spot color backing color validation
6. Checks: GRD_COLOR_001 (prohibited spaces), GRD_COLOR_002 (DeviceRGB requires ICC), GRD_COLOR_003 (spot color backing), GRD_COLOR_004 (TAC exceeds limit)
7. TAC limit configurable per Ruleset (330 for sheetfed, 260 for web, etc.)
8. Tests: known CMYK values → known TAC, prohibited spaces, ICC profile present/absent

### Module 4d: TransparencyAnalyzer

**Card: GRD-015 — TransparencyAnalyzer**

File: `src/grounded/analyzers/transparency.py`

Acceptance Criteria:
1. Risky blend mode detection (8 safe: Normal, Multiply, Screen, Overlay, Darken, Lighten, ColorDodge, ColorBurn; 8 risky: HardLight, SoftLight, Difference, Exclusion, Hue, Saturation, Color, Luminosity)
2. Transparency + overprint conflict detection
3. Soft mask validation
4. Transparency group color space validation
5. Checks: GRD_TRANS_001 (risky blend modes), GRD_TRANS_002 (transparency + overprint conflict), GRD_TRANS_003 (soft mask issues)
6. Tests: each blend mode classification, conflict scenarios

### Module 4e: OverprintAnalyzer

**Card: GRD-016 — OverprintAnalyzer**

File: `src/grounded/analyzers/overprint.py`

Acceptance Criteria:
1. OPM interaction analysis: OP, op, OPM flag combinations
2. Overprint on non-CMYK color space detection (potential rendering differences)
3. Overprint with transparency interaction flagging
4. Checks: GRD_OVER_001 (overprint on RGB), GRD_OVER_002 (OPM=0 with DeviceCMYK), GRD_OVER_003 (overprint + transparency)
5. Tests: OP/op/OPM combinations, CMYK vs RGB overprint scenarios

### Module 4f: PageGeometryAnalyzer

**Card: GRD-017 — PageGeometryAnalyzer**

File: `src/grounded/analyzers/page_geometry.py`

Acceptance Criteria:
1. Box presence validation: TrimBox and BleedBox required for print
2. Box hierarchy: BleedBox ≥ TrimBox, all within MediaBox
3. Bleed distance calculation (BleedBox - TrimBox on each side)
4. Page dimension validation
5. Checks: GRD_BOX_001 (TrimBox/BleedBox present), GRD_BOX_002 (hierarchy valid), GRD_BOX_003 (bleed distance adequate)
6. Tests: missing boxes, inverted boxes, adequate/inadequate bleed

---

## PHASE 5: CONFORMANCE VALIDATORS

### Module 5a: PDFXValidator

**Card: GRD-018 — PDF/X-4 validator (92 checks)**

File: `src/grounded/conformance/pdfx_validator.py`

Acceptance Criteria:
1. Implements checks organized by category (see `lintpdf-research/09-10-11-conformance-standards.md`)
2. File Structure & Metadata (11), Output Intent (8), Color Spaces (9), Fonts (6), Transparency (4), Page Boxes (8), Annotations (4), Encryption (2), Optional Content (3), Restricted Features (5), Graphics & Images (6), Image Compression (6), Resource Dictionaries (4), Reader & Validation (7), Variants (4)
3. Each check has inspection ID (GRD_COMP_*), ISO clause reference, severity
4. Reuses data from SemanticModel and ContentStreamInterpreter — does NOT re-parse
5. Tests against veraPDF validation corpus, Isartor test suite

Reference: `lintpdf-research/specs/iso15930-7-pdfx4.md` for full check catalog.

**Card scope warning:** This card is large (92 checks). Consider splitting into sub-cards by category if it exceeds 400 lines per PR.

### Module 5b: PDFAValidator (veraPDF delegation)

**Card: GRD-019 — PDF/A validator via veraPDF sidecar**

File: `src/grounded/conformance/pdfa_validator.py` + `src/grounded/conformance/verapdf_client.py`

Acceptance Criteria:
1. `VeraPDFClient` sends PDF bytes to veraPDF REST API (`POST /api/validate`)
2. Supports PDF/A-1b, 1a, 2b, 2a, 2u, 3b, 3a, 3u, 4, 4e, 4f
3. Parses veraPDF machine-readable XML response
4. Maps veraPDF violations to LintPDF `Finding` objects with GRD_PDFA_* IDs
5. Docker health check: verify veraPDF container is running before validation
6. Timeout handling: 60-second timeout for veraPDF calls
7. Graceful degradation: if veraPDF unavailable, report error finding (not crash)
8. Tests: mock veraPDF responses, timeout handling, response parsing

Reference: `lintpdf-research/09-10-11-conformance-standards.md` veraPDF integration section.

---

## PHASE 6: RULE ENGINE + RULESETS

### Module 6a: Rule Engine

**Card: GRD-020 — RuleRegistry and @rule decorator**

Files: `src/grounded/rules/registry.py`, `src/grounded/rules/decorators.py`, `src/grounded/rules/finding.py`

Acceptance Criteria:
1. `Finding` dataclass: inspection_id, severity (no-fly/delay/advisory), message, page_num, bbox, details, iso_clause
2. `@rule(analyzer=..., name=..., iso_clause=...)` decorator
3. `RuleRegistry` with `register()`, `get_rules_for_analyzer()`, `get_all_rules()`
4. Auto-discovery: scan `rules/builtin/` package on import
5. Dependency validation: ensure required analyzers exist for each rule
6. Tests: register rule, retrieve by analyzer, duplicate name rejection

### Module 6b: Built-in Rules (MVP 17 checks)

**Card: GRD-021 — Built-in rule functions (17 MVP checks)**

Files: `src/grounded/rules/builtin/*.py`

Acceptance Criteria:
1. All 17 MVP checks implemented as pure functions (see synthesis.md §6)
2. Each function: receives analyzer output, returns `List[Finding]`
3. No imports from api/, queue/, or tenants/
4. Each function includes `iso_clause` in decorator metadata
5. Tests: one test per rule with both passing and failing inputs

### Module 6c: Rulesets

**Card: GRD-022 — RulesetLoader and ProfileRegistry**

Files: `src/grounded/profiles/loader.py`, `src/grounded/profiles/registry.py`, `src/grounded/profiles/schema.py`

Acceptance Criteria:
1. Ruleset JSON schema with validation (Pydantic model)
2. `RulesetLoader` loads JSON file → Profile object
3. Profile: rule selection, severity overrides, threshold overrides
4. Profile inheritance (`extends` field): child overrides parent
5. `ProfileRegistry`: register built-in profiles, look up by ID
6. Built-in profiles: `pdfx4-standard`, at least 3 GWG 2022 variants
7. Tests: valid profile loading, inheritance, invalid schema rejection, severity override

Reference: `lintpdf-research/09-10-11-conformance-standards.md` Ruleset JSON schema section.

---

## PHASE 7: API + QUEUE + TENANTS

### Module 7a: FastAPI Application

**Card: GRD-023 — FastAPI app with core endpoints**

Files: `src/grounded/api/app.py`, `src/grounded/api/routes/*.py`

Acceptance Criteria:
1. `POST /api/v1/check-in`: multipart upload (pdf_file + profile_id + optional webhook_url + metadata)
2. Returns 202 Accepted with job_id, polling_url, estimated_wait
3. `GET /api/v1/report/{id}`: returns status (queued/taxiing/arrived) + findings when complete
4. `GET /api/v1/rulesets`: list available profiles
5. `GET /health`: health check (DB + Redis + veraPDF)
6. OpenAPI 3.1 auto-generated (FastAPI native)
7. Request validation with Pydantic models
8. File size limit: 500MB
9. Tests: endpoint tests with TestClient, file upload, polling flow

### Module 7b: Celery Worker

**Card: GRD-024 — Celery task queue for PDF processing**

Files: `src/grounded/queue/worker.py`, `src/grounded/queue/tasks.py`

Acceptance Criteria:
1. `inspect_pdf` Celery task: receives job_id, profile_id, pdf_path
2. Pipeline: parse → build semantic model → interpret content streams → run analyzers → evaluate rules → generate report
3. Updates job status in PostgreSQL (queued → taxiing → arrived)
4. Stores findings as JSONB in PostgreSQL
5. Triggers webhook if webhook_url provided
6. Error handling: task failure → status "error" with error message
7. Configurable time_limit (default 300 seconds)
8. Tests: mock pipeline, status transitions, error handling

### Module 7c: TenantManager

**Card: GRD-025 — Multi-tenancy with API key auth**

Files: `src/grounded/tenants/manager.py`, `src/grounded/tenants/models.py`, `src/grounded/api/auth.py`

Acceptance Criteria:
1. API key authentication via `X-API-Key` header or `api_key` query param
2. Tenant resolution from API key → tenant_id
3. All database queries scoped by tenant_id
4. Rate limiting per tenant (configurable per plan)
5. Usage tracking (checks consumed per billing period)
6. PostgreSQL models: Tenant, Subscription, ApiKey, Job
7. Tests: auth flow, tenant isolation, rate limit enforcement

### Module 7d: Webhook System (Radio)

**Card: GRD-026 — Radio webhook delivery**

Files: `src/grounded/webhooks/radio.py`, `src/grounded/webhooks/retry.py`

Acceptance Criteria:
1. POST webhook to callback URL when job completes
2. Payload: job_id, status, verdict, finding_count, report_url
3. Exponential backoff retry: 3 attempts (1s, 5s, 25s)
4. Signature: HMAC-SHA256 in `X-LintPDF-Signature` header
5. Timeout: 10-second connection timeout
6. Failed webhooks logged (not blocking)
7. Tests: successful delivery, retry on failure, signature verification

### Module 7e: Report Generation

**Card: GRD-027 — ReportGenerator (Report output)**

Files: `src/grounded/reports/generator.py`, `src/grounded/reports/*.py`

Acceptance Criteria:
1. JSON report: findings array, summary (total, by severity), metadata, profile used
2. XML report: same structure in XML format
3. PDF report: WeasyPrint + Jinja2 template with LintPDF branding
4. Verdict calculation: clear-to-fly (0 no-fly), grounded (1+ no-fly), delay (0 no-fly, 1+ delay)
5. White-label support: tenant logo and colors (Livery system)
6. Tests: each format generates valid output, verdict logic

---

## PHASE 8: DEPLOYMENT

**Card: GRD-028 — Docker + Railway deployment**

Acceptance Criteria:
1. Multi-stage Dockerfile (builder + runtime)
2. `docker-compose.yml` for local dev (api, worker, redis, postgres, verapdf)
3. Railway `railway.toml` or `Procfile` for deployment
4. Database migrations (Alembic)
5. Health check endpoint responding correctly
6. Environment variables documented in `.env.example`
7. veraPDF sidecar container configuration
8. CI: build Docker image on PR, deploy on merge to main

---

## PHASE 9: LAUNCH PREP

**Card: GRD-029 — API documentation and SDK generation**

Acceptance Criteria:
1. OpenAPI 3.1 spec auto-generated and hosted
2. Python SDK (`lintpdf-python`) generated from OpenAPI
3. Getting Started guide (5-minute onboarding)
4. Inspection ID catalog (all GRD_* IDs with descriptions)
5. Ruleset authoring guide

**Card: GRD-030 — Regression test suite**

Acceptance Criteria:
1. End-to-end test: upload PDF → poll → verify findings
2. Test corpus regression: known PDFs produce known findings
3. Performance benchmarks: 10MB PDF <10s, 100MB PDF <30s
4. All tests in CI pipeline

---

## CARD CREATION CHECKLIST

When creating Linear cards from this playbook:

1. Use card number as suggested (GRD-XXX) — Linear will assign actual numbers
2. Copy Acceptance Criteria verbatim — these are the definition of done
3. Add `opus` label to cards GRD-009 and GRD-010 (ContentStreamInterpreter — architecturally critical)
4. Add `conformance` label to GRD-018, GRD-019 (require human QA)
5. Add `api-endpoint` label to GRD-023 (require human QA)
6. Add `security` label to GRD-025 (auth/tenancy — require human QA)
7. Set Phase 1-3 cards to AI Ready first; queue later phases as predecessors complete
8. Each card should reference the specific research file for detailed specs

## RESEARCH REFERENCE MAP

| Module | Primary Research File | ADR |
|--------|----------------------|-----|
| Parser | implementation-plan.md §Module 1 | ADR-001 |
| SemanticModel | implementation-plan.md §Module 2 | — |
| ContentStreamInterpreter | implementation-plan.md §Module 3 (algorithms) | ADR-002 |
| Analyzers (all) | 03-content-streams-graphics-state.md, 04-color-spaces.md, 05-font-technology.md, 06-images.md, 07-08-transparency-overprint.md | — |
| PDF/X-4 | specs/iso15930-7-pdfx4.md (92 checks) | — |
| PDF/A | 09-10-11-conformance-standards.md §PDF/A | ADR-005 |
| GWG | 09-10-11-conformance-standards.md §GWG, specs/gwg-2022-specification.md | ADR-006 |
| Rules + Profiles | implementation-plan.md §Module 6-7, synthesis.md §5-6 | ADR-003 |
| API + Queue | synthesis.md §API, implementation-plan.md §Module 9-10 | ADR-004 |
