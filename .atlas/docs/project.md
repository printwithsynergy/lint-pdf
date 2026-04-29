---
title: Project Overview
tags: [project, stack, setup]
---

# LintPDF — PDF Preflight Engine

Detection-only PDF preflight engine. API-first SaaS that inspects print-ready PDFs against PDF/X-4, PDF/A, and GWG 2022 specifications. No corrections, no side effects — pure detection.

## Team

- Linear: GRD
- GitHub: thinkneverland/lint-pdf

## Stack

- **Runtime:** Python 3.13+
- **Framework:** FastAPI (async, OpenAPI 3.1)
- **Parser:** pikepdf (QPDF C++ bindings) via ParserAdapter
- **PDF/A Validation:** veraPDF (sidecar Docker container)
- **Job Queue:** Celery + Redis
- **Database:** PostgreSQL (JSONB for findings)
- **File Storage:** Cloudflare R2
- **Deployment:** Railway (Docker)
- **Reports:** WeasyPrint + Jinja2
- **Testing:** pytest, ruff, mypy (strict)

## Dev Setup

```bash
pip install -e ".[dev]" && docker compose up -d redis postgres verapdf
```

## Commands

```
pytest                          # run tests
ruff check src/                 # lint
ruff format src/                # format
mypy src/                       # type check
```

## Brand Language

| Term     | Meaning                                  |
| -------- | ---------------------------------------- |
| Submit   | Upload endpoint (POST /api/v1/jobs)      |
| Ruleset  | Preflight profile (rule composition)     |
| Report   | Inspection report                        |
| Pass     | All checks passed                        |
| Fail     | Critical failures found                  |
| Warning  | Warnings found                           |
| Webhook  | Webhook system                           |
| Processing | Job in progress                        |
| Complete | Job complete                             |

## Inspection ID Format

`LPDF_{CATEGORY}_{NNN}` — e.g., LPDF_FONT_001, LPDF_IMG_003 (deterministic checks).
`AI_{CATEGORY}_{NNN}` — AI-tier checks (e.g., AI_BARCODE_001).

Categories: FONT, IMG, COLOR, BOX, TRANS, OVER, COMP, STRUCT, GWG, BARCODE, BRAND, etc.

## Key Constraints

- Detection-only: never modify input PDFs
- Every check traces to an ISO clause reference
- Never import from api/, queue/, or tenants/ inside rules/
- 500MB file size limit
- Multi-tenant from day one
