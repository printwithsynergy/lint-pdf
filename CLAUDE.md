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
prisma db push            # Sync schema for any new PD columns
next start                # Run the app
```

No lockfile committed, no local references, no cached packages. Every deploy pulls the latest published Pixie Dust versions from `npm.pkg.github.com`.

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
