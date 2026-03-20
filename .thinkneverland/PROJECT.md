# PROJECT.md — LintPDF

## What this is

Detection-only PDF preflight engine. API-first SaaS that inspects print-ready PDFs against PDF/X-4, PDF/A, and GWG 2022 specifications. No corrections, no side effects — pure detection with clean, lint-focused brand language.

## Team

Linear: GRD | GitHub: thinkneverland/lint-pdf

LINEAR_TEAM_KEY: GRD
GITHUB_REPO: thinkneverland/lint-pdf
BASE_BRANCH: main
PRODUCT_TYPE: saas
PIXIE_DUST_BASED: true
PUBLIC_ROADMAP: false
PUBLIC_PACKAGE: false

## Stack

- **Runtime:** Python 3.12+
- **Framework:** FastAPI (async, OpenAPI 3.1 auto-gen)
- **Parser:** pikepdf (QPDF C++ bindings) via ParserAdapter abstraction
- **PDF/A Validation:** veraPDF (sidecar Docker container, REST API)
- **Job Queue:** Celery + Redis
- **Database:** PostgreSQL (ACID for job state, JSONB metadata)
- **File Storage:** Cloudflare R2 (S3-compatible)
- **Deployment:** Railway (Docker)
- **Reports:** WeasyPrint + Jinja2 (PDF), JSON, XML
- **Testing:** pytest, veraPDF corpus, Isartor, GWG test files

## Dev setup

```bash
pip install -e ".[dev]" && docker compose up -d redis postgres verapdf
```

## Commands

```
pytest                          # run tests
pytest -m "not slow"            # skip corpus tests
ruff check src/                 # lint
ruff format src/                # format
mypy src/                       # type check
celery -A grounded.worker worker --loglevel=info  # worker
uvicorn grounded.api:app --reload                 # dev server
```

## Project structure

```
src/
├── parser/           # Module 1: ParserAdapter + PikePDFAdapter
├── semantic/         # Module 2-3: SemanticModel + ContentStreamInterpreter
├── analyzers/        # Module 4: Font, Image, Color, Transparency, Overprint
├── conformance/      # Module 5: PDFXValidator, PDFAValidator (veraPDF)
├── rules/            # Module 6: Rule functions + RuleRegistry
├── profiles/         # Module 7: RulesetLoader + ProfileRegistry
├── reports/          # Module 8: ReportGenerator (Report output)
├── api/              # Module 9: FastAPI endpoints + auth + rate limiting
├── queue/            # Module 10: Celery tasks + TaskQueue
├── tenants/          # Module 11: TenantManager + multi-tenancy
└── webhooks/         # Module 12: Webhook delivery
```

## Brand language

| Term        | Meaning                               |
| ----------- | ------------------------------------- |
| Submit      | Upload endpoint (POST /api/v1/submit) |
| Ruleset     | Preflight profile (rule composition)  |
| Report      | Inspection report                     |
| Pass        | All checks passed                     |
| Fail        | Critical failures found               |
| Warning     | Warnings found                        |
| Info        | Informational findings                |
| Error       | Critical severity (blocks approval)   |
| Dashboard   | Dashboard / admin UI                  |
| White Label | White-label branding                  |
| Webhook     | Webhook system                        |
| Processing  | Job in progress                       |
| Complete    | Job complete                          |

## Key decisions (ADRs)

- **ADR-001:** pikepdf + ParserAdapter abstraction (swap parsers without touching analyzers)
- **ADR-002:** ContentStreamInterpreter state machine (streaming events, not buffered)
- **ADR-003:** Pure function rules + Ruleset JSON profiles (composable, tenant-customizable)
- **ADR-004:** Async API with Celery + Redis (POST returns 202 + job_id, poll or webhook)
- **ADR-005:** veraPDF sidecar for PDF/A (delegate to specialist, MPL 2.0 compatible)
- **ADR-006:** GWG parameterized profiles (23 variants as Ruleset JSON configs)

## Notes

- Detection-only: never modify input PDFs
- Every check traces to an ISO clause reference
- Inspection IDs follow pattern: GRD*{CATEGORY}*{NNN}
- Rulesets are JSON; tenant overrides stored in PostgreSQL
- veraPDF runs as separate Docker container (REST API on port 8080)
- 500MB file size limit; streaming interpreter for memory efficiency
- Multi-tenant from day one — all queries scoped by tenant_id
