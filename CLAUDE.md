# CLAUDE.md — LintPDF Project Instructions

## Project Overview

LintPDF is a PDF preflight quality assurance SaaS built on the Pixie Dust framework. Monorepo with pnpm workspaces.

**Packages:**
- `packages/app` — Next.js 15 dashboard (TypeScript, TailwindCSS, Prisma)
- `packages/plugin` — Fairy Ring plugin for Pixie Dust (`@thinkneverland/grounded-plugin`)
- `packages/stripe` — Stripe billing integration (`@lintpdf/stripe`)
- `packages/engine` — Python PDF analysis engine (FastAPI, Celery, pikepdf)
- `packages/web` — Public marketing site (Next.js)
- `packages/desktop` — Desktop app (Tauri)

**Key conventions:**
- Always push to `main` unless told otherwise
- All `@thinkneverland/pixie-dust-*` packages use **caret (`^`) version specifiers** pinned to the latest published version on `npm.pkg.github.com` — **never `"*"`**. When upgrading, query the GitHub Packages registry for each package's `dist-tags.latest` using `GITHUB_TOKEN` and bump the caret range to match. See the "Pixie Dust Upgrade Checklist" below for the exact procedure.
- Plugin routes use `req.auth?.tenantId` (NOT `req.tenantId`) for tenant context
- Engine routes use SQLAlchemy + Alembic migrations
- App routes use Prisma with multi-file schema in `prisma/schema/`

---

## Pixie Dust Upgrade Checklist

### Version specifier policy

All `@thinkneverland/pixie-dust-*` dependencies in `packages/app/package.json`, `packages/plugin/package.json`, and `packages/stripe/package.json` **MUST** use caret ranges pinned to the latest published version on `npm.pkg.github.com` (e.g. `"^1.8.0"`). **Do not use `"*"`** — it defers resolution to `pnpm install`, which makes deploys non-reproducible and hides breaking major bumps.

`.npmrc` is configured with `save-prefix=^` so `pnpm add` / `pnpm update` write caret ranges by default.

### Refreshing to latest (run this on every Pixie Dust bump)

Use the `GITHUB_TOKEN` env var to query the GitHub Packages npm registry directly, then update every `@thinkneverland/pixie-dust-*` specifier to `^<latest>` in **all three** workspace package.json files (`packages/app`, `packages/plugin`, `packages/stripe`).

One-liner to fetch latest versions for every Pixie Dust package this repo depends on:

```sh
for pkg in api-keys auth boilerplate config cookie-consent core dashboard database \
           devtools email fairy-ring stripe-kit theme-default theme-kit ui usage \
           waitlist webhooks tsconfig; do
  version=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
    "https://npm.pkg.github.com/@thinkneverland/pixie-dust-$pkg" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['dist-tags']['latest'])")
  echo "@thinkneverland/pixie-dust-$pkg: ^$version"
done
```

After bumping the specifiers, run `pnpm install` and commit the updated `package.json` files (no lockfile). Then sync the database schema:

```sh
npx prisma db push
```

Or if using migrations:

```sh
npx prisma migrate deploy
```

### Deploy pipeline requirement

Your deploy/start command should **ALWAYS** include a schema sync before the app starts. The full pipeline is:

```
pnpm store prune          # Clear cached packages — no stale Pixie Dust
pnpm install              # Fresh resolve honoring caret ranges in package.json
prisma db push            # Sync schema for any new PD columns
next start                # Run the app
```

No lockfile committed, no local references, no cached packages. Every deploy resolves the caret ranges against `npm.pkg.github.com` using `GITHUB_TOKEN`. To pull in a new major release, re-run the refresh script above and bump the caret.

**Important:** `.npmrc` must contain `save-prefix=^` so pnpm preserves caret ranges during `pnpm add` / `pnpm update`. Never revert to `save-prefix=` (empty) or `"*"` specifiers.

**Railway / Docker:**
```sh
npx prisma db push && npm start
```

**LintPDF uses `startup.sh`** (`packages/app/scripts/startup.sh`) which:
1. Runs raw SQL `ALTER TABLE ADD COLUMN IF NOT EXISTS` for new columns (safe, no drops)
2. Creates new tables via raw SQL `CREATE TABLE IF NOT EXISTS`
3. Runs `prisma db push` (may warn about engine tables — that's OK)
4. Seeds the database
5. Starts the server

This is necessary because `prisma db push` without `--accept-data-loss` refuses to make changes when it sees engine tables (tenants, jobs, api_keys, etc.) that aren't in the Prisma schema.

### Why this matters

Pixie Dust packages may add new database columns (e.g., `AppSettings.primaryColor`, `AppSettings.emailButtonColor`). The `getBranding()` function is resilient — it won't crash if columns are missing — but features like branding customization, email colors, and login page theming will silently degrade.

On startup, `checkSchemaHealth()` logs a warning if drift is detected:

```
WARNING: Database schema is out of date! Missing columns on AppSettings: primaryColor, emailButtonColor, ...
To fix, run one of:
  npx prisma db push --schema=prisma/schema
  npx prisma migrate deploy --schema=prisma/schema
```

### Current required schema versions

- `@thinkneverland/pixie-dust-database@1.3.1` — AppSettings needs: `primaryColor`, `emailButtonColor`, `loginBgColor`, `loginHeading`, `loginSubheading`
- `@thinkneverland/pixie-dust-auth@1.4.1` — Resilient `getBranding()` (no explicit select)

### Rule

**NEVER** skip `prisma db push` after upgrading Pixie Dust packages. Add it to your deploy pipeline so it runs automatically on every deployment.

When adding new columns to the Prisma schema that Pixie Dust expects, also add the corresponding `ALTER TABLE ADD COLUMN IF NOT EXISTS` to `packages/app/scripts/startup.sh` so the column gets created even when `prisma db push` can't apply it due to engine table conflicts.

---

## Trial / Try-It Page

The public `/try-it` page (`packages/web/src/app/try-it/page.tsx`) lets prospects upload PDFs for a free preflight report. The flow is **env-gated**:

| `LINTPDF_TRIAL_AUTO_SUBMIT` | Behavior |
|---|---|
| `false` *(default)* | Submission lands in the admin queue with status `PENDING`. An admin must log into `/dashboard/admin/trials`, click **Run Preflight** on each file, wait for the job to complete, then click **Send Report Email**. |
| `true` | Preflight is queued **automatically** on submission. The submission still shows up in the admin queue (for monitoring and re-runs), but moves straight to `PROCESSING`. The admin still manually clicks **Send Report Email** once jobs complete — report delivery is never automated. |

Supporting env vars:
- `LINTPDF_TRIAL_SECRET` — shared secret between the marketing site and the engine (required).
- `LINTPDF_TRIAL_AUTO_SUBMIT_PROFILE_ID` — profile id used for auto-submit (default: `lintpdf-default`).
- `LINTPDF_ADMIN_EMAIL` — recipient for new-submission notifications.

The admin UI (`packages/app/app/dashboard/admin/trials/page.tsx`) reads the current mode via `GET /api/v1/admin/trials/config` and shows an **Auto-Submit: ON/OFF** banner so admins know whether action is required.

### ClamAV scanning (best-effort, fail-open)

Every upload endpoint (`/api/v1/jobs`, `/api/v1/batch/submit`, `/api/v1/endpoints/{id}/submit`, `/api/v1/trial/submit`, `/api/v1/ai/config/logos`) calls `validate_upload()` in `packages/engine/src/lintpdf/api/upload_security.py`. ClamAV scanning is **best-effort**:
- `LINTPDF_CLAMAV_URL` unset → scan skipped, upload proceeds (warning logged).
- `clamd` unreachable/timeout → scan skipped, upload proceeds (warning logged).
- Malware positively detected → HTTP 422, upload rejected.

**Why fail-open?** The production `thinkneverland/railway-clamav` sidecar has a latent bug: its Dockerfile runs `configure-env.sh` at build time instead of runtime, so `CLAMD_CONF_TCPSocket` / `CLAMD_CONF_TCPAddr` env vars are silently ignored and clamd only binds the Unix socket — TCP probes from the engine fail with `Connection refused`. Until that repo's Dockerfile is fixed (move `configure-env.sh` into an entrypoint wrapper, or bake `TCPSocket 3310` into clamd.conf directly), fail-closed behavior turns every production upload into a 503. Local dev still has a working clamd via the `clamav` service in `packages/engine/docker-compose.yml`.

---

## Shared Database

The app (Prisma) and engine (SQLAlchemy/Alembic) share the same PostgreSQL database. This means:
- `prisma db push` sees engine tables it doesn't own and wants to drop them
- **NEVER** use `--accept-data-loss` — it will wipe engine tables
- New Prisma columns must also be added to `startup.sh` as raw SQL fallback
- Engine migrations are handled by Alembic (separate from Prisma)

---

## Docs parity

Customer-reachable surface area has three places to land — forget any one and we ship a feature that nobody can find:

1. **Markdown docs** — `packages/web/src/content/docs/<slug>.md`, registered in `packages/web/src/lib/doc-sections.ts` and surfaced on `packages/web/src/app/docs/page.tsx`.
2. **JSX doc pages** — `packages/web/src/components/docs/pages/ApiReferencePage.tsx` (composed of the section components in `components/docs/pages/api/`), plus `ReportFormatsPage.tsx`, `WebhooksPage.tsx`, `GlossaryPage.tsx`, `ChecksPage.tsx`.
3. **Example payloads** — `docs/examples/` at repo root. Every `external_format` parser and every tenant-editable shape (custom mappings, branding defaults) has a runnable sample here plus a matching curl script.

Rules:

- **Any new submit-form field** (new `preflight_source` value, new `external_format` enum, new `brand` resolution mode, new `unbranded` / `mapping_id` / `ai_*` knob) lands in both the markdown docs **and** the `ApiReferencePage` section components **in the same commit**. Don't split them — the marketing site and the JSX API reference drift immediately otherwise.
- **Any new viewer-config field** (new `enable_*` toggle, new `data_capabilities` flag, new toolbar/branding knob) lands in `viewer-capabilities.md` **and** the `ApiViewerSection.tsx` config FieldTable.
- **Any new branding column** (tenant defaults, BrandProfile, share-link immutability capture) lands in `branding-and-anonymous.md` / `share-links.md` **and** the `ApiBrandingSection.tsx` component.
- **New engine parsers** for an external preflight format must ship a fresh `docs/examples/<vendor>-report.{xml,json}` sample + update `external-imports.md` + update the enum appendix in `ApiEnumsSection.tsx`.
- **New Pydantic fields** on any `Request`/`Response` schema need `Field(..., description=...)` so FastAPI surfaces them in `/openapi.json` and `/redoc`.

When in doubt, grep the docs for the concept name before merging — if there's a mention anywhere, at least two other mentions probably need to change too.

---

## Git & Deploy

- Push to `main` for deployment
- Railway auto-deploys from main
- `railway.toml` configs are in each package directory
- App Dockerfile has `noCache = true` to always pull latest Pixie Dust
- Engine Dockerfile includes `poppler-utils` and `ghostscript` for PDF rendering
