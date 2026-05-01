# LintPDF

> **Detection-only PDF preflight engine** — analyze packaging, label,
> and commercial-print PDFs against 500+ checks (image DPI, total
> area coverage, bleed, fonts, barcodes, color spaces, conformance,
> AI-assisted regulatory rules, …) and surface findings as
> structured JSON, HTML reports, or annotated PDFs.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

LintPDF is the OSS preflight engine that powers the hosted SaaS at
[lintpdf.com](https://lintpdf.com). The hosted product layers
multi-tenancy, billing, white-label reports, and an admin console on
top of this engine; the OSS package is the engine plus a narrow HTTP
surface for submitting jobs and fetching results. You can self-host
the OSS engine standalone.

This repository is licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE) — see
[the licensing notes below](#licensing) for what that means in
practice when you embed or modify the engine.

---

## Table of contents

- [What it does](#what-it-does)
- [Quick start (Docker)](#quick-start-docker)
- [Quick start (Python)](#quick-start-python)
- [Submit your first PDF](#submit-your-first-pdf)
- [Documentation](#documentation)
- [Licensing](#licensing)
- [Contributing](#contributing)
- [Support](#support)

---

## What it does

LintPDF answers one question: **"is this PDF print-ready?"**

You POST a file. The engine analyzes it across 500+ checks grouped
into categories (image quality, color, fonts, packaging, barcodes,
regulatory compliance, conformance, …) and returns:

- A **verdict** — `pass`, `pass_with_warnings`, or `fail`.
- A list of **findings** — each with an inspection id, severity,
  page number, bounding box, and a human-readable message.
- A **rendered report** — HTML, PDF, JSON, or annotated PDF.
- A **viewer payload** — separations, TAC heatmap, font list,
  layer toggles for the embedded React viewer
  ([@printwithsynergy/loupe-pdf](https://github.com/printwithsynergy/loupe-pdf)).

The engine ships built-in profiles for GWG 2022 (sheetfed +
digital), PDF/X-4, and packaging — and supports custom rulesets
authored as JSON. AI-assisted features (Claude-driven audit,
explanations, dieline detection, regulatory checks) are optional
and self-skip cleanly when no AI inference service is configured.

For the deeper architectural picture see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Quick start (Docker)

```bash
# Clone + boot the full stack (engine + Postgres + Redis + ClamAV)
git clone https://github.com/thinkneverland/lint-pdf.git
cd lint-pdf
docker compose up -d

# Wait for /ready to return 200
curl http://localhost:8000/ready
# {"status":"ok","database":"connected","redis":"connected"}
```

The compose stack is a single-node OSS deploy with Celery worker +
beat + ClamAV sidecar. For production / HA topology see
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Quick start (Python)

```bash
# 3.11+ required
pip install "lintpdf @ git+https://github.com/thinkneverland/lint-pdf.git@main"

# Minimum env (production refuses to boot without these)
export LINTPDF_SAAS_MODE=false
export LINTPDF_SECRET_KEY=$(openssl rand -hex 32)
export LINTPDF_DATABASE_URL=postgresql://user:pass@localhost/lintpdf
export LINTPDF_REDIS_URL=redis://localhost:6379/0

# Boot the API
uvicorn lintpdf.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

A complete environment-variable reference and the OSS-mode hard
fails (production secret key + CORS wildcard) live in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Submit your first PDF

```bash
# 1. Submit
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "file=@artwork.pdf" \
  -F "profile_id=lintpdf-default"
# { "job_id": "job_abc…", "status": "queued" }

# 2. Poll
curl http://localhost:8000/api/v1/jobs/job_abc…
# { "id": "job_abc…", "status": "completed", "verdict": "pass_with_warnings", … }

# 3. One-call snapshot (job + reports + annotations + verdicts)
curl http://localhost:8000/api/v1/jobs/job_abc…/state | jq .
```

The OSS engine boots without multi-tenant auth out of the box — see
[`docs/DEPLOYMENT.md#auth-in-oss-mode`](docs/DEPLOYMENT.md#auth-in-oss-mode)
to wire in your own auth (single-user, OIDC, basic auth, or a custom
tenant resolver).

---

## Documentation

| Doc | Covers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Component layout, request flow, the three-scope toggle cascade, snapshots, AI tier model. |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Self-hosting reference: env vars, services, Docker / Railway / single-node, OSS-mode toggle, security gates, backups. |
| [`docs/EXTENDING.md`](docs/EXTENDING.md) | Service overrides (email / entitlements / billing / auth) and analyzer plugin authoring quick reference. |
| [`docs/plugin-api.md`](docs/plugin-api.md) | Full plugin Protocol reference — manifest fields, `AnalyzerContext`, banned imports, capability providers. |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Dev environment setup, test conventions, commit / PR style, the engine-purity tripwire. |
| [`docs/audit-phase1.md`](docs/audit-phase1.md) | Engineering record of the Phase 1 plugin-protocol refactor (background reading). |

The hosted product's customer-facing docs (workflows, rulesets,
brand profiles, integrations) live at
[lintpdf.com/docs](https://lintpdf.com/docs).

---

## Licensing

LintPDF is licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0+).

**What that means in practice:**

- **Self-host for any use** (commercial or otherwise) — no fee, no
  per-tenant cap, no notify-us clause. Run it on your own infra and
  ship reports to your customers.
- **Modifications** must be made available under the same AGPL-3.0+
  license to anyone who interacts with your modified version
  **including over a network** (this is the "A" in AGPL — the
  network-use trigger). If you patch the engine and run it as a
  hosted service, your patches are AGPL.
- **Commercial / proprietary use without disclosure** — contact
  Think Neverland LLC about a commercial license. The hosted SaaS
  at lintpdf.com runs under such a commercial license arrangement
  with itself; the engine you're reading is the same code, just
  under different licensing terms when you pay for the hosted /
  embedded option.

Copyright © 2024–2026 Think Neverland LLC.

Third-party dependencies retain their own licenses — see
[`docs/CONTRIBUTING.md#third-party-licenses`](docs/CONTRIBUTING.md#third-party-licenses)
for the inventory.

---

## Contributing

We accept patches via pull request. Before opening a PR:

1. Read [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — covers
   the engine-purity tripwire (analyzers must not import
   tenant/billing/storage modules), the OpenAPI-description
   discipline (every Pydantic field needs `description=…`), and
   the test pyramid.
2. Sign off your commits (`git commit -s`). LintPDF uses the
   [Developer Certificate of Origin](https://developercertificate.org/)
   to track contributor licensing intent.
3. Run the tripwires locally — `bash scripts/check_engine_purity.sh`
   and `python scripts/check_openapi_descriptions.py` — and the
   pytest suite (`pytest --no-header`).

For larger changes (a new analyzer category, schema migration,
public-API addition) open a discussion issue first so we can align
on shape before you write code.

---

## Support

- **Hosted product** — [lintpdf.com](https://lintpdf.com) — fully
  managed, white-label, billing + admin included.
- **OSS issues** — [GitHub Issues](https://github.com/thinkneverland/lint-pdf/issues)
  for bug reports, feature requests, and security disclosures
  (mark security issues with the `security` label and we'll triage
  off-list).
- **Commercial** — `dev@thinkneverland.com` for commercial licenses,
  embedded deployments, or paid support contracts.

---

*LintPDF is a Think Neverland LLC project, originally extracted from
the production codebase of the hosted SaaS at lintpdf.com. The
extraction itself is documented in
[`docs/audit-phase1.md`](docs/audit-phase1.md).*
