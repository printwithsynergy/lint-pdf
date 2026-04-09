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
- All `@thinkneverland/pixie-dust-*` packages use `"*"` version specifiers — always pull latest
- Plugin routes use `req.auth?.tenantId` (NOT `req.tenantId`) for tenant context
- Engine routes use SQLAlchemy + Alembic migrations
- App routes use Prisma with multi-file schema in `prisma/schema/`

---

## Pixie Dust Upgrade Checklist

After upgrading any `@thinkneverland/pixie-dust-*` packages, you **MUST** sync your database schema:

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
pnpm install              # Fresh resolve from GitHub Packages (no lockfile)
pnpm update '@thinkneverland/*' -r  # Force re-resolve to newest published
prisma db push            # Sync schema for any new PD columns
next start                # Run the app
```

No lockfile committed, no local references, no cached packages. Every deploy pulls the latest published Pixie Dust versions from `npm.pkg.github.com`.

**Important:** `.npmrc` must contain `save-prefix=` to prevent pnpm from rewriting `"*"` specifiers to caret ranges like `"^4.0.2"` during `pnpm update`.

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

## Git & Deploy

- Push to `main` for deployment
- Railway auto-deploys from main
- `railway.toml` configs are in each package directory
- App Dockerfile has `noCache = true` to always pull latest Pixie Dust
- Engine Dockerfile includes `poppler-utils` and `ghostscript` for PDF rendering
