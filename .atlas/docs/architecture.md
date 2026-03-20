---
title: Architecture
tags: [architecture, layers, dependencies]
---

# Grounded Architecture

## Layer Structure

```
src/
├── parser/                    # Layer 1: PDF parsing abstraction
│   ├── adapter.py             # ParserAdapter ABC
│   ├── pikepdf_adapter.py     # PikePDFAdapter concrete implementation
│
├── semantic/                  # Layer 2-3: Semantic interpretation
│   ├── model.py               # SemanticDocument, SemanticPage, PdfFont, PdfImage, PdfColorSpace, PdfBox
│   ├── builder.py             # SemanticModelBuilder (enrichment + inheritance)
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
│   └── builtin/               # Built-in rule functions
│
├── profiles/                  # Layer 4b: Flight Plans
│   ├── loader.py              # FlightPlanLoader (JSON -> Profile)
│   ├── registry.py            # ProfileRegistry
│   └── builtin/               # Built-in Flight Plan JSON files
│
├── reports/                   # Layer 5: Output generation
│   ├── generator.py           # ReportGenerator
│   └── templates/             # Jinja2 templates
│
├── api/                       # Layer 6: HTTP interface
│   ├── app.py                 # FastAPI app factory
│   └── routes/                # Endpoint modules
│
├── queue/                     # Layer 6b: Background processing
│   ├── worker.py              # Celery app
│   └── tasks.py               # inspect_pdf task
│
├── tenants/                   # Layer 6c: Multi-tenancy
│   └── manager.py             # TenantManager
│
└── webhooks/                  # Layer 6d: Notifications
    └── radio.py               # Webhook delivery
```

## Dependency Layers (strict)

```
webhooks/ <- api/ <- queue/ <- tenants/
                              |
                          reports/ <- rules/ <- profiles/
                                      |
                                  analyzers/ <- conformance/
                                      |
                                  semantic/
                                      |
                                  parser/
```

Lower layers MUST NOT import from upper layers.

## Key Patterns

- **Parser abstraction (ADR-001):** All code depends on ParserAdapter ABC, never pikepdf directly
- **Streaming events (ADR-002):** ContentStreamInterpreter emits events consumed by analyzers
- **Pure function rules (ADR-003):** Rules are stateless functions decorated with @rule
- **Async API (ADR-004):** POST returns 202 + job_id, Celery processes in background
- **veraPDF delegation (ADR-005):** PDF/A validation via sidecar container
- **GWG profiles (ADR-006):** 23 variants as parameterized Flight Plan JSON configs
