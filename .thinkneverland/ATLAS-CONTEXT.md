# ATLAS-CONTEXT.md — LintPDF

# Project-specific knowledge for Atlas and Cyrus.

# Updated by post-merge GitHub Action and Atlas design sessions.

## Architecture

```
src/
├── parser/                    # Layer 1: PDF parsing abstraction
│   ├── adapter.py             # ParserAdapter ABC
│   ├── pikepdf_adapter.py     # PikePDFAdapter concrete implementation
│   └── exceptions.py          # PDFStructureError, PDFParseError, PDFStreamEncodingError
│
├── semantic/                  # Layer 2: Semantic interpretation
│   ├── model.py               # PdfDocument, PdfPage, PdfFont, PdfImage, PdfColorSpace, PdfBox
│   ├── interpreter.py         # ContentStreamInterpreter (state machine)
│   ├── graphics_state.py      # GraphicsState, TransformationMatrix
│   └── events.py              # ImagePlaced, TextRendered, ColorChanged, etc.
│
├── analyzers/                 # Layer 3: Detection modules
│   ├── base.py                # BaseAnalyzer ABC
│   ├── font.py                # FontAnalyzer (embedding, subsetting, Standard 14)
│   ├── image.py               # ImageAnalyzer (DPI, color space, soft mask)
│   ├── color.py               # ColorAnalyzer (TAC, prohibited spaces, ICC)
│   ├── transparency.py        # TransparencyAnalyzer (blend modes, groups)
│   ├── overprint.py           # OverprintAnalyzer (OP/op/OPM interactions)
│   └── page_geometry.py       # PageGeometryAnalyzer (boxes, dimensions)
│
├── conformance/               # Layer 3b: Standards validation
│   ├── pdfx_validator.py      # PDF/X-4 (92 checks, ISO 15930-7)
│   ├── pdfa_validator.py      # PDF/A (veraPDF sidecar delegation)
│   └── verapdf_client.py      # veraPDF REST API client
│
├── rules/                     # Layer 4: Rule engine
│   ├── registry.py            # RuleRegistry (discovery + registration)
│   ├── decorators.py          # @rule decorator
│   ├── finding.py             # Finding dataclass
│   ├── builtin/               # Built-in rule functions
│   │   ├── font_rules.py
│   │   ├── image_rules.py
│   │   ├── color_rules.py
│   │   ├── transparency_rules.py
│   │   ├── overprint_rules.py
│   │   ├── conformance_rules.py
│   │   └── structure_rules.py
│   └── gwg/                   # GWG-specific rule compositions
│       └── gwg_rules.py
│
├── profiles/                  # Layer 4b: Rulesets
│   ├── loader.py              # RulesetLoader (JSON → Profile)
│   ├── registry.py            # ProfileRegistry
│   ├── schema.py              # Ruleset JSON schema validation
│   └── builtin/               # Built-in Ruleset JSON files
│       ├── pdfx4-standard.json
│       ├── gwg-2022-sheetcmyk-cmyk.json
│       ├── gwg-2022-webcmyk-cmyk.json
│       └── ...                # 23 GWG variants
│
├── reports/                   # Layer 5: Output generation
│   ├── generator.py           # ReportGenerator
│   ├── json_report.py         # JSON Report output
│   ├── xml_report.py          # XML Report output
│   ├── pdf_report.py          # PDF Report (WeasyPrint + Jinja2)
│   └── templates/             # Jinja2 templates
│
├── api/                       # Layer 6: HTTP interface
│   ├── app.py                 # FastAPI app factory
│   ├── routes/
│   │   ├── checkin.py         # POST /api/v1/check-in
│   │   ├── report.py           # GET /api/v1/report/{id}
│   │   ├── profiles.py        # GET/POST /api/v1/rulesets
│   │   └── health.py          # GET /health
│   ├── auth.py                # API key authentication
│   ├── rate_limit.py          # Rate limiting middleware
│   └── middleware.py          # Tenant context, CORS, logging
│
├── queue/                     # Layer 6b: Background processing
│   ├── worker.py              # Celery app + task definitions
│   ├── tasks.py               # inspect_pdf task
│   └── callbacks.py           # Post-inspection hooks
│
├── tenants/                   # Layer 6c: Multi-tenancy
│   ├── manager.py             # TenantManager
│   ├── models.py              # Tenant, Subscription, ApiKey
│   └── middleware.py          # Tenant resolution from API key
│
└── webhooks/                  # Layer 6d: Notifications
    ├── radio.py               # Radio (webhook delivery)
    └── retry.py               # Exponential backoff
```

## Key patterns

**Parser abstraction:** All code depends on ParserAdapter interface, never pikepdf directly. The only file that imports pikepdf is `parser/pikepdf_adapter.py`. This enables future parser swaps.

**Content stream interpretation:** ContentStreamInterpreter walks PDF operators, maintains GraphicsState stack (q/Q push/pop), and emits semantic events (ImagePlaced, TextRendered, ColorChanged, etc.). Analyzers subscribe to event types. Streaming processing — never buffer full content stream.

**Form XObject recursion:** When `Do` operator references a Form XObject, interpreter descends recursively. CTM multiplication through recursion: `CTM_child = CTM_parent × form_matrix`. Cycle detection via visited set + 32-level depth limit.

**DPI calculation:** `EffectiveDPI = (image_pixels / display_points) × 72`. Display points derived from CTM scale factors: `sx = sqrt(a² + c²)`, `sy = sqrt(b² + d²)`.

**Rule functions:** Pure Python functions decorated with `@rule(analyzer=..., name=...)`. Receive analyzer output, return `List[Finding]`. Stateless, deterministic, no side effects. ISO clause reference required in metadata.

**Rulesets (profiles):** JSON files composing rules with severity overrides and thresholds. Profiles can extend base profiles. GWG 2022 has 23 variants — each is a Ruleset JSON file with parameterized thresholds (TAC limits, resolution minimums, color binding mode).

**Finding severity:** Three levels only — no-fly (spec violation), delay (warning), advisory (informational). Default from rule; Ruleset can override.

**Async processing:** POST /api/v1/check-in returns 202 + job_id. Celery worker processes in background. Client polls GET /api/v1/report/{id} or registers webhook_url for push notification.

**Multi-tenancy:** All database queries scoped by tenant_id. Tenant resolved from API key in middleware. Tenants can upload custom Rulesets but NOT custom rule code (security boundary).

**veraPDF delegation:** PDF/A validation delegated to veraPDF running as sidecar Docker container. REST API on port 8080. LintPDF calls POST /api/validate with PDF bytes + profile name, parses machine-readable XML response, maps to Finding objects.

## Design tokens

### Inspection ID format

`GRD_{CATEGORY}_{NNN}` — e.g., GRD_FONT_001, GRD_IMG_003, GRD_GWG_BASE_001

Categories: FONT, IMG, COLOR, BOX, TRANS, OVER, COMP, STRUCT, GWG

### API status values

| Status  | Meaning                          |
| ------- | -------------------------------- |
| queued  | Job accepted, waiting for worker |
| taxiing | Worker processing                |
| arrived | Processing complete              |

### Report verdict

| Verdict      | Meaning                                 |
| ------------ | --------------------------------------- |
| clear-to-fly | Zero no-fly findings                    |
| grounded     | One or more no-fly findings             |
| delay        | Zero no-fly, one or more delay findings |

## Known constraints

- pikepdf C++ dependency adds ~50MB to Docker image
- veraPDF requires Java runtime — runs as separate container, not embedded
- Content stream interpreter is CPU-bound — Celery worker concurrency limited by CPU cores
- 500MB file size limit (Railway memory constraint)
- PostgreSQL JSONB for findings storage — indexed on inspection_id and severity
- Ruleset JSON schema must be backward-compatible across versions
- Never import from api/, queue/, or tenants/ inside rules/ — rules must be pure
- Never modify input PDF bytes — detection-only philosophy is non-negotiable

## Dependency layers (strict)

```
webhooks/ ← api/ ← queue/ ← tenants/
                              ↓
                          reports/ ← rules/ ← profiles/
                                      ↓
                                  analyzers/ ← conformance/
                                      ↓
                                  semantic/
                                      ↓
                                  parser/
```

Arrows mean "depends on". Lower layers MUST NOT import from upper layers.
