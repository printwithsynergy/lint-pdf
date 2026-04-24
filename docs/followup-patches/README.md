# Follow-up patches

Patches staged here are ready-to-apply changes that were authored in
this PR but whose commits are blocked by upstream tech debt (most
commonly the engine-wide `ruff check src/ tests/ + ruff format --check
src/ tests/ + mypy src/` pre-commit hook, which fails on pre-existing
issues in files outside the authored change set).

Apply with `git apply docs/followup-patches/<name>.patch` from the repo
root once the blocker is resolved (or alongside the cleanup PR that
fixes the blocker). Delete the patch file in the same commit that
lands it so this directory stays empty between resolutions.

## admin-usage-endpoint.patch

**Owner scope:** Phase 4.1 of the dashboard CRUD/styling playbook.

**Adds:** `GET /api/v1/admin/tenants/{tenant_id}/usage` — admin-auth
sibling of `/api/v1/usage` that accepts an explicit tenant id instead
of resolving tenant from the Bearer key. The plugin's
`/api/lintpdf/usage` route already calls this endpoint and falls back
to the legacy shared-key path on 404, so applying the patch + deploying
the engine cleanly lights up correct per-tenant usage for every
dashboard user.

**Blocked by:** 42 pre-existing `ruff check` errors + 41 files needing
`ruff format` in unrelated engine files (analyzers, audit, queue, etc.).
The admin.py edit in this patch individually passes ruff on its own.

**Suggested landing sequence:**

1. Open a `chore(engine): ruff format + safe autofix` PR that runs
   `ruff check src/ tests/ --fix` and `ruff format src/ tests/` across
   the whole engine tree. Nothing in that PR is in this playbook — it's
   purely mechanical debt payoff.
2. Merge that first.
3. Apply this patch, commit, open a tiny follow-up PR "feat(engine):
   admin usage endpoint (Phase 4.1 tail)".
4. Remove the `if (resp.status === 404)` fallback branch in
   `packages/plugin/src/plugins/usage/index.ts` in a third PR (or in
   the same PR as step 3 once the engine is verified deployed).
