# Build context is the repo root (Railway uses dockerfilePath from root)

# Stage 1: Fresh install — always resolve latest Pixie Dust packages
# No lockfile copied — pnpm generates a fresh one each build so
# @thinkneverland/pixie-dust-* packages with "*" specifiers always
# resolve to the newest published version from GitHub Packages.
FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable pnpm
# Copy workspace config (NO lockfile) + package.json files
COPY package.json pnpm-workspace.yaml .npmrc ./
COPY scripts/ scripts/
COPY packages/app/package.json packages/app/package.json
COPY packages/plugin/package.json packages/plugin/package.json
COPY packages/stripe/package.json packages/stripe/package.json
# Private @thinkneverland packages need auth
ARG NODE_AUTH_TOKEN
ENV NODE_AUTH_TOKEN=$NODE_AUTH_TOKEN
# Purge pnpm store cache so no stale Pixie Dust versions persist between builds
RUN pnpm store prune 2>/dev/null || true
# Fresh install — resolves all "*" specifiers to latest published versions
# No --frozen-lockfile since there's no lockfile to freeze against
RUN pnpm install --filter=@thinkneverland/lintpdf-app... --no-frozen-lockfile
# Force re-resolve @thinkneverland/* to newest published versions
# (pnpm install may satisfy "*" from cache; update forces registry check)
RUN pnpm update '@thinkneverland/*' -r

# Stage 2: Build
FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable pnpm
# Copy workspace config + the fresh lockfile from deps stage
COPY package.json pnpm-workspace.yaml .npmrc ./
COPY scripts/ scripts/
COPY --from=deps /app/pnpm-lock.yaml ./
# Copy full workspace package sources
COPY packages/plugin/ ./packages/plugin/
COPY packages/stripe/ ./packages/stripe/
COPY packages/app/ ./packages/app/
# Copy node_modules from deps stage (already has latest Pixie Dust)
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages/app/node_modules ./packages/app/node_modules
COPY --from=deps /app/packages/plugin/node_modules ./packages/plugin/node_modules
COPY --from=deps /app/packages/stripe/node_modules ./packages/stripe/node_modules
# Re-run install to fix workspace symlinks — uses fresh lockfile
ARG NODE_AUTH_TOKEN
ENV NODE_AUTH_TOKEN=$NODE_AUTH_TOKEN
RUN pnpm install --filter=@thinkneverland/lintpdf-app... --prefer-offline

# Build workspace dependencies first (they export from dist/)
RUN pnpm --filter=@thinkneverland/grounded-plugin build && \
    pnpm --filter=@lintpdf/stripe build

# Generate Prisma client
WORKDIR /app/packages/app
RUN npx prisma generate --schema=prisma/schema

ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# Stage 3: Runtime
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Standalone output preserves monorepo structure
COPY --from=builder --chown=nextjs:nodejs /app/packages/app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/packages/app/.next/static ./packages/app/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/packages/app/public ./packages/app/public

# Copy Prisma schema for runtime db push
COPY --from=builder --chown=nextjs:nodejs /app/packages/app/prisma ./packages/app/prisma

# Install Prisma CLI globally for runtime migrations (avoids pnpm hoisting issues)
RUN npm install -g prisma@7

# Copy startup script
COPY --from=builder --chown=nextjs:nodejs /app/packages/app/scripts/startup.sh ./packages/app/scripts/startup.sh

USER nextjs

EXPOSE 8080
ENV PORT=8080
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:8080/api/health || exit 1

# Startup: safe SQL migration → prisma db push → seed → start server
CMD ["sh", "packages/app/scripts/startup.sh"]
