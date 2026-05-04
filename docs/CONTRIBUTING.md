---
title: "Contributing"
description: "Dev environment setup, sign-off and DCO, test conventions, commit / PR style, and the engine-purity tripwire that gates every analyzer change."
group: "Project"
order: 9
---

# Contributing to LintPDF

We accept patches via pull request. Before opening a PR, please
read this guide so your change lands fast.

## Licensing intent

LintPDF is licensed under the
[GNU Affero General Public License v3.0 or later](../LICENSE).
By submitting a pull request, you certify that you wrote the patch
(or have the right to submit it under the AGPL-3.0+ terms) per the
[Developer Certificate of Origin](https://developercertificate.org/).

Sign off your commits to make that explicit:

```bash
git commit -s -m "feat(analyzer): add foo bar check"
```

The `-s` adds a `Signed-off-by: Your Name <email>` trailer.
CI rejects unsigned commits.

## Development environment

```bash
git clone https://github.com/printwithsynergy/lint-pdf.git
cd lint-pdf
python -m venv .venv && source .venv/bin/activate
pip install -e ".[ai,dev]"

# Bring up the supporting services (Postgres + Redis + ClamAV)
docker compose up -d postgres redis clamav

# Run the full test suite
pytest --no-header
```

The `[ai]` extra pulls in the heavy vision/AI deps
(`scikit-image`, `imagehash`, `colour-science`, `statsmodels`,
…). Skip it if you're only working on non-AI analyzers — the
imports self-skip cleanly.

## The CI tripwires

LintPDF has two CI guards that run on every PR. Understand them
before you start a refactor that might trip them.

### Engine purity

`scripts/check_engine_purity.sh` enforces the rule that code under
`src/lintpdf/analyzers/**` and `src/lintpdf/ai/analyzers/**` cannot
import from SaaS-coupled modules (`lintpdf.tenants.*`,
`lintpdf.billing.*`, `lintpdf.audit.metering`,
`lintpdf.audit.cost`, `lintpdf.api.database`,
`lintpdf.api.storage`, …). Use `ctx.services.*` instead.

The script counts existing violations (baseline: 125 at the time
of writing) and fails CI when the count goes UP. Down-counts are
encouraged — once you eliminate a violation, regenerate the
baseline:

```bash
bash scripts/check_engine_purity.sh --update-baseline
git add scripts/engine_purity_baseline.txt
```

The git pre-commit hook in `.githooks/pre-commit` runs this guard
automatically whenever any `src/lintpdf/*.py` file is staged.

### OpenAPI descriptions

`scripts/check_openapi_descriptions.py` enforces that every
`Field(...)` in `api/schemas.py` (and route-handler request /
response models) has a `description="..."` argument. The
description is what `/openapi.json` and `/redoc` surface to API
consumers; missing descriptions silently ship a worse developer
experience.

Baseline: 0. New fields without `description=` fail the build.

### Migration scope (W7 alembic-split tripwire)

`scripts/check_migration_scope.py` enforces the engine ↔ SaaS
table-scope boundary in alembic migrations. Every Postgres table
is classified in `audit/table-scopes.yaml` as `engine`, `saas`,
or `orphan`. New migrations must touch tables in exactly one
scope — no cross-scope changes.

Historical pre-W6 migrations that legitimately mixed scopes (back
when both lived on a single `Base`) are tolerated via
`scripts/migration_scope_baseline.txt`. Don't add new entries
there: split the migration instead.

The tripwire runs on every PR via the `engine tripwires` job in
`.github/workflows/ci.yml`. New tables must be classified in
`audit/table-scopes.yaml` or the build fails with exit code 2.

Each tripwire is idempotent and fast (~2 seconds combined). The
pre-commit hook runs them on staged files only.

## Test conventions

We use pytest with the following marker conventions:

| Marker | Meaning |
|---|---|
| `corpus` | Requires the downloaded test corpus (deselect with `-m "not corpus"`). |
| `slow` | Takes more than 10 seconds. |
| `integration` | Requires Postgres / Redis / veraPDF. |
| `live_ai` | Hits the real Claude API (cost ~$0.01 / run; opt-in via `-m live_ai`). |

The default `pytest` invocation runs the unit tier
(`-m "not corpus and not slow and not integration and not live_ai"`).
CI runs the unit tier on every PR and the integration tier on
nightly builds.

### Behaviour-locking tests

When you change analyzer behaviour or schema shape, snapshot the
current output into a test that fails if the output changes.
Commit the test first; commit the refactor second. This makes the
behaviour-change explicit in the diff and prevents silent
regressions.

The customer-surface parity suites
(`tests/regression/test_customer_surface_parity.py` and
`tests/regression/test_finding_parity.py`) are the gate for any
change that touches a public route shape — both must pass on the
PR before merge.

### Coverage

`fail_under=80` is configured in `pyproject.toml`. Net coverage
drops require either added tests or an explicit dead-code
justification in the PR description.

## Commit + PR style

Conventional Commits format:

```
<type>(<scope>): <short summary>

<longer description, wrap at 72 chars>

<footers — Signed-off-by, Refs, …>
```

Common types we use:

- `feat` — new analyzer, new route, new public surface.
- `fix` — bug fix.
- `refactor` — internal restructure with no behaviour change.
- `test` — test-only changes.
- `docs` — documentation only.
- `chore` — tooling, dep bumps, CI.
- `perf` — performance fix with measurable improvement.

Common scopes: `analyzer`, `api`, `viewer`, `reports`, `engine`,
`plugin`, `services`, `tripwire`.

PR descriptions should include:

1. **Summary** — 1-3 bullets describing the change.
2. **Test plan** — checklist of how to verify the change works.
3. **Affected docs** — pointers to docs that may need updates
   (especially when adding routes / schema fields).

## Never bypass the sandbox

No `--no-verify`, `--no-gpg-sign`, or `--accept-data-loss`. If a
hook fails on a file you didn't stage, fix the underlying error or
unstage the hunk — never shortcut around the hook.

The `--accept-data-loss` flag in particular is dangerous because
the engine schema is shared with the SaaS in some deployments;
silently dropping engine tables would wipe production data.

## Adding an analyzer

1. Read [`docs/EXTENDING.md`](EXTENDING.md) and
   [`docs/plugin-api.md`](plugin-api.md) for the Protocol shape.
2. Decide whether your analyzer is a built-in (lives under
   `src/lintpdf/analyzers/` or `src/lintpdf/ai/analyzers/`) or a
   third-party plugin (separate Python package).
3. Implement `analyze_v2(ctx) -> list[Finding]` returning
   structured findings — never raw text strings.
4. Add a test under `tests/analyzers/` that exercises a fixture
   PDF from `tests/fixtures/`.
5. If your analyzer adds a new check id, document it in the
   check-name catalogue (`src/lintpdf/analyzers/check_names.py`)
   so reports + viewer pick it up.

## Adding a public-API field

1. Add the `Field(...)` with a `description="..."` (the tripwire
   will fail the build otherwise).
2. Add the field to the customer-facing JSX docs in the SaaS
   repo (the marketing site — separate PR there if you're a SaaS
   contributor).
3. Add an example to `docs/examples/` if the field's shape isn't
   obvious from the type annotation.
4. Regenerate the Postman collection — this happens in CI on
   merge to `main`, not in your PR.

## Third-party licenses

The engine depends on several BSD/MIT/Apache-licensed Python
packages (FastAPI, SQLAlchemy, pikepdf, Pillow, …) and one
LGPL-licensed package (pdf2image, via Poppler). Distribution of
modified versions of LintPDF must comply with both AGPL-3.0+
(this project) and the upstream licenses (per dep).

Generate a current license inventory with:

```bash
pip-licenses --format=markdown > docs/THIRD_PARTY_LICENSES.md
```

(Not committed — regenerate before each release.)

## Security disclosures

For security-sensitive findings, **do not open a public issue.**
Email `dev@thinkneverland.com` with `[security]` in the subject.
We'll triage off-list and credit you in the release notes when the
fix ships.

For non-sensitive bugs and feature requests, GitHub Issues is the
right channel.

## Questions

Open a discussion issue on
[GitHub](https://github.com/printwithsynergy/lint-pdf/discussions),
or reach `dev@thinkneverland.com` for commercial-license / paid
support topics.

---

Thanks for contributing.
