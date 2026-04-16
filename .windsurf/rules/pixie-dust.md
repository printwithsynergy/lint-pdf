---
trigger: always_on
description: "Pixie Dust framework compliance rules for LintPDF"
---

# Pixie Dust Framework Rules

## Session Start
- Ask: "Want me to check for `@thinkneverland/pixie-dust-*` package upgrades?"
- If yes: `pnpm update '@thinkneverland/*' -r` then `npx prisma db push`

## Critical Compliance — NEVER Violate

- **Auth**: NEVER bypass `@thinkneverland/pixie-dust-auth` — no custom login/session/token logic
- **Database**: NEVER use raw `prisma.model.findMany()` without tenant filtering — always use `withTenant(tenantId)` or `createTenantClient(db, tenantId)` from `@thinkneverland/pixie-dust-database/server`
- **Payments**: NEVER import `stripe` directly — use `@thinkneverland/pixie-dust-stripe-kit`
- **Styling**: NEVER use arbitrary Tailwind values — use Pixie Dust CSS token system (`--pd-*` variables)
- **RBAC**: NEVER hardcode role checks — use Pixie Dust role guards from `@thinkneverland/pixie-dust-auth`
- **Plugins**: NEVER register sidebar/nav items outside the Fairy Ring plugin system

## Package Policy

- ALL `@thinkneverland/pixie-dust-*` packages use `"^"` version specifier
- Commit `pnpm-lock.yaml` for reproducibility
- On deploy: `pnpm update '@thinkneverland/*' -r` pulls latest compatible versions
- After upgrading: always run `npx prisma db push`

## Workflow

1. Create a feature branch from `main`
2. Make changes — follow Pixie Dust patterns
3. Pre-push: `pnpm typecheck && pnpm lint && pnpm build`
4. Push and create PR
5. Never hardcode secrets — use environment variables

## Code Style

- TypeScript strict mode
- Absolute imports with `@/` alias
- No `any` types without explicit `// eslint-disable` comment explaining why
- All exported functions must have JSDoc comments

## Custom Code Boundaries

- Pixie Dust owns: auth, tenancy, billing, dashboard shell, plugin system, theming, database schema
- LintPDF owns: preflight engine, PDF processing, annotation UI, all domain-specific features
- NEVER modify Pixie Dust-owned patterns in custom code
- NEVER touch the preflight engine (`packages/engine/`) when doing PD work
