# Build context is the repo root (Railway uses dockerfilePath from root)

# Stage 1: Install dependencies & pull latest Pixie Dust packages
FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable pnpm
# Copy root workspace config + lockfile, then relevant package.json files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY packages/app/package.json packages/app/package.json
COPY packages/plugin/package.json packages/plugin/package.json
COPY packages/stripe/package.json packages/stripe/package.json
# Private @thinkneverland packages need auth
ARG NODE_AUTH_TOKEN
ENV NODE_AUTH_TOKEN=$NODE_AUTH_TOKEN
# Install deps (cached when lockfile unchanged)
RUN pnpm install --filter=@thinkneverland/lintpdf-app...
# Bust Docker cache so pnpm update always runs on every deploy/redeploy.
# noCache=true in railway.toml ensures this ARG gets a fresh value each time.
ARG CACHEBUST
# Always pull latest Pixie Dust packages (glob covers base + all suffixed packages)
RUN pnpm update --recursive '@thinkneverland/pixie-dust' '@thinkneverland/pixie-dust-*'

# Stage 2: Build
FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable pnpm
# Copy workspace config and .npmrc (NOT the repo lockfile — use the updated one from deps)
COPY package.json pnpm-workspace.yaml .npmrc ./
# Copy the updated lockfile from deps stage so builder resolves the latest Pixie Dust versions
COPY --from=deps /app/pnpm-lock.yaml ./
# Copy full workspace package sources
COPY packages/plugin/ ./packages/plugin/
COPY packages/stripe/ ./packages/stripe/
COPY packages/app/ ./packages/app/
# Copy cached node_modules from deps stage (already has latest Pixie Dust)
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages/app/node_modules ./packages/app/node_modules
COPY --from=deps /app/packages/plugin/node_modules ./packages/plugin/node_modules
COPY --from=deps /app/packages/stripe/node_modules ./packages/stripe/node_modules
# Re-run install to fix workspace symlinks — uses updated lockfile so versions stay current
ARG NODE_AUTH_TOKEN
ENV NODE_AUTH_TOKEN=$NODE_AUTH_TOKEN
RUN pnpm install --filter=@thinkneverland/lintpdf-app... --prefer-offline

# Build workspace dependencies first (they export from dist/)
RUN pnpm --filter=@thinkneverland/grounded-plugin build && \
    pnpm --filter=@lintpdf/stripe build

# Generate Prisma client
WORKDIR /app/packages/app
RUN npx prisma generate

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
RUN npm install -g prisma@6

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
