---
title: Project Overview
tags: [project, stack, setup]
---

# LintPDF — PDF Preflight Engine

Detection-only PDF preflight engine. API-first SaaS that inspects print-ready PDFs against PDF/X-4, PDF/A, and GWG 2022 specifications. No corrections, no side effects — pure detection.

## Team

- Linear: GRD
- GitHub: thinkneverland/grounded

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

| Term | Meaning |
|------|---------|
| Check-In | Upload endpoint (POST /api/v1/check-in) |
| Flight Plan | Preflight profile (rule composition) |
| Flight Log | Inspection report |
| Clear to Fly | All checks passed |
| Failed | Critical failures found |
| No-Fly | Critical severity |
| Radio | Webhook system |
| Taxiing | Job in progress |
| Arrived | Job complete |

## Inspection ID Format

`GRD_{CATEGORY}_{NNN}` — e.g., GRD_FONT_001, GRD_IMG_003

Categories: FONT, IMG, COLOR, BOX, TRANS, OVER, COMP, STRUCT, GWG

## Key Constraints

- Detection-only: never modify input PDFs
- Every check traces to an ISO clause reference
- Never import from api/, queue/, or tenants/ inside rules/
- 500MB file size limit
- Multi-tenant from day one
