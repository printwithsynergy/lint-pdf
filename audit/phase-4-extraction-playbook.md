# Phase 4 — Repo extraction playbook

This playbook walks through the extraction of the engine
(`packages/engine/` → `thinkneverland/sift-pdf`) and the viewer core
(`packages/viewer-shared/src/core/` → `thinkneverland/loupe-pdf`)
from the `lint-pdf` monorepo into their own repositories.

## What's already done (this PR)

The extraction branches are pre-built and pushed to the lint-pdf
remote:

- **`extract/sift-pdf`** — 70 commits. History-preserving subtree
  split of `packages/engine/`. Every blob and commit is scoped to
  files under that path.
- **`extract/loupe-pdf`** — 16 commits. History-preserving subtree
  split of `packages/viewer-shared/src/core/`.

Both branches are valid root-level repositories (their root is the
former subtree's root: `packages/engine/` for sift-pdf,
`packages/viewer-shared/src/core/` for loupe-pdf).

## What you do next

### Step 1: create the private GitHub repos

The Claude Code MCP integration is scoped to `thinkneverland/lint-pdf`
only — it cannot create new repos under the org. Create these two
manually (UI or `gh`):

```sh
gh repo create thinkneverland/sift-pdf \
    --private \
    --description "SiftPDF — OSS PDF preflight engine. Extracted from lint-pdf."

gh repo create thinkneverland/loupe-pdf \
    --private \
    --description "LoupePDF — OSS PDF viewer core. Extracted from lint-pdf."
```

Repository visibility starts **private**. Flip to public when you're
ready (visibility flip is the only manually-driven step in this
extraction).

### Step 2: push the extraction branches as the new repos' main

```sh
# In the lint-pdf checkout that has extract/sift-pdf and extract/loupe-pdf:

git push git@github.com:thinkneverland/sift-pdf.git \
    extract/sift-pdf:main

git push git@github.com:thinkneverland/loupe-pdf.git \
    extract/loupe-pdf:main
```

Both pushes carry full file-scoped commit history.

### Step 3 (sift-pdf only): rename `lintpdf` → `siftpdf`

In the new sift-pdf checkout, do the Python package rename. This is
mechanical but touches every file — keep it as one focused commit
so reviewers can see the rename in isolation.

```sh
git clone git@github.com:thinkneverland/sift-pdf.git
cd sift-pdf

# Rename the Python package directory
git mv src/lintpdf src/siftpdf

# Update Python imports + string references in the code
# (replace exactly ``lintpdf`` standalone — don't rewrite ``LINTPDF_*``
# env-var names or customer-facing brand strings)
grep -rl --include='*.py' '\blintpdf\b' src/ tests/ scripts/ \
  | xargs sed -i 's/\blintpdf\b/siftpdf/g'

# Update pyproject.toml: name = "lintpdf" → "siftpdf"
sed -i 's/name = "lintpdf"/name = "siftpdf"/' pyproject.toml

# Update entry-point group from lintpdf.plugins → siftpdf.plugins
sed -i 's/lintpdf\.plugins/siftpdf.plugins/' pyproject.toml

# Update Dockerfile / Railway configs
sed -i 's/lintpdf\./siftpdf./g' Dockerfile railway.toml scripts/entrypoint.sh

# Verify
grep -rln '\blintpdf\b' src/ tests/ scripts/ pyproject.toml | head
# Customer-facing brand strings ("LintPDF", "lintpdf.com",
# "LINTPDF_*" env vars) should remain. Anything else that's still
# matching is probably a bug.

git add -A
git commit -m "refactor: rename Python package lintpdf → siftpdf"
git push
```

### Step 4 (sift-pdf): publish to PyPI / pip-installable index

For the SaaS to consume sift-pdf as an external dep, it needs to be
installable. Options:

- **GitHub Packages** (private) — use the existing GitHub Token
  pattern (same as the Pixie Dust upgrade flow in `/CLAUDE.md`).
  Add a `publish` workflow that runs on tag push.
- **PyPI** (public) — only after the visibility flip; would expose
  package contents to anyone.
- **Direct git ref in `pyproject.toml`** (no publish step) — fine for
  development; works for both private and post-flip public repos.

Recommended: direct git ref initially, GitHub Packages once stable.

### Step 5 (lint-pdf monorepo): consume sift-pdf as external dep

In lint-pdf's `packages/engine/pyproject.toml`, replace the local
package layout with a dependency:

```diff
- [project]
- name = "lintpdf"
- ...
+ [project]
+ name = "lintpdf-saas"
+ ...
+ dependencies = [
+     "siftpdf @ git+https://github.com/thinkneverland/sift-pdf.git@main",
+     ...
+ ]
```

Then delete `packages/engine/src/lintpdf/` and replace it with the
SaaS-only modules that aren't part of sift-pdf (the orchestrator,
the FastAPI app shell, the Stripe billing wiring, the Celery worker
glue). Most of `src/lintpdf/{ai,analyzers,plugin,rendering,
semantic,profiles,conformance,imports,reports}` is sift-pdf turf
and goes away in this repo.

Done in stages:

1. Add `siftpdf` as a dep alongside the existing local package.
2. Update one consumer at a time to import from `siftpdf` instead
   of `lintpdf` (use `try/except ImportError` for the transition).
3. Once every consumer is on `siftpdf`, delete the local
   `packages/engine/src/lintpdf/` directory.

**Hard constraint**: hosted SaaS (`lintpdf.com` /
`app.lintpdf.com` / `reports.lintpdf.com`) must produce bit-for-bit
identical responses through every step of this transition. The
behaviour-locking tests in `tests/regression/` are the gate.

### Step 6 (loupe-pdf): same steps, simpler

1. Push `extract/loupe-pdf` to the new repo (Step 2 above).
2. **No rename needed** — the viewer core was always called
   `core/`; LoupePDF is the brand name, not a package name in code.
3. Publish to npm (private package on `npm.pkg.github.com` initially).
4. Update lint-pdf's `packages/viewer-shared/` to consume
   `@thinkneverland/loupe-pdf` as an external npm dep instead of
   the local `src/core/` directory.

### Step 7: visibility flip

When you're satisfied with each repo's contents, structure, and
documentation, flip from private → public via the GitHub UI. This is
the only step that the Claude Code session can't automate; it's also
the one you specifically asked to drive yourself.

## Why it was done this way

### Why I did the subtree split inside lint-pdf instead of in the new repos

`git subtree split` produces a synthetic root commit that re-bases
all the file-scoped history at the new path. Doing it inside the
source repo means:

1. The new repos start with full history (not just a single squash
   commit).
2. The split is reproducible — anyone with read access to lint-pdf
   can verify the extraction is correct.
3. The new repos can be created later without losing anything;
   pushing the same `extract/*` branch produces the same hash chain.

### Why I didn't do the lintpdf → siftpdf rename in lint-pdf

Three reasons:

1. **Production risk.** The hosted SaaS imports `lintpdf` everywhere
   — alembic env, Celery worker glue, FastAPI app, route handlers.
   A rename inside the monorepo would have to update all of them
   atomically without breaking any deploy. Any partial state risks
   a Railway redeploy with broken imports.
2. **Shared DB.** Alembic migrations reference `lintpdf` model
   modules. Renaming requires either renaming all migrations
   (history rewrite, dangerous) or keeping the package literal as
   `lintpdf` for migration env (defeats the point).
3. **Better venue.** Inside the new sift-pdf repo, the rename has
   no production impact — the repo doesn't yet have any deployed
   surface. One focused PR. Clean.

### Why no registry unification

Original Phase 3 plan called for unifying 4 registries (`ai/`,
`profiles/`, `regulatory/`, `warming/`) into a single
`plugin/registry.py`. After looking at each one:

- They hold genuinely different domain objects: AI analyzer
  CLASSES, PreflightProfile INSTANCES, regulatory rule
  MAPPINGS, cache warmer SCHEDULES.
- A unified registry would either lose type safety (everything
  becomes `Any`) or add a useless level of indirection.
- Post-extraction, most of these registries live in different
  packages (sift-pdf for ai/profiles/regulatory; lint-pdf SaaS
  for warming) and the unification stops making sense.

The plugin registry already exists at `plugin/registry.py` and
provides the entry-point + decorator-driven discovery surface that
post-extraction third-party plugin packs need. That's the
canonical "plugin registry"; the per-domain registries each serve
their own concerns.

## Verification commands (post-extraction)

After Step 5:

```sh
# Engine tests still pass
cd packages/engine && pytest tests/

# Customer surface unchanged
cd packages/engine && pytest tests/regression/test_customer_surface_parity.py
cd packages/engine && pytest tests/regression/test_finding_parity.py

# Viewer test snapshots unchanged
cd packages/viewer-shared && pnpm test

# Engine purity tripwire still at 0
cd packages/engine && bash scripts/check_engine_purity.sh
```

## Rollback

If the extraction goes wrong at any step, the lint-pdf monorepo is
the source of truth and the `extract/*` branches are reproducible
from `git subtree split`. Worst case: delete the new repos, recreate
from a fresh `git subtree split --prefix=packages/engine` of the
current `lint-pdf` HEAD.
