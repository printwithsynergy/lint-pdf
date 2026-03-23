# Build context is the repo root (Railway uses dockerfilePath from root)

# Stage 1: Install dependencies
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
RUN pnpm install --filter=@thinkneverland/grounded-app...

# Stage 2: Build
FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable pnpm
# Copy workspace config, lockfile, and .npmrc for pnpm install
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
# Copy full workspace package sources
COPY packages/plugin/ ./packages/plugin/
COPY packages/stripe/ ./packages/stripe/
COPY packages/app/ ./packages/app/
# Copy cached node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages/app/node_modules ./packages/app/node_modules
COPY --from=deps /app/packages/plugin/node_modules ./packages/plugin/node_modules
COPY --from=deps /app/packages/stripe/node_modules ./packages/stripe/node_modules
# Re-run install to fix workspace symlinks (uses cached deps, just recreates links)
ARG NODE_AUTH_TOKEN
ENV NODE_AUTH_TOKEN=$NODE_AUTH_TOKEN
RUN pnpm install --filter=@thinkneverland/grounded-app... --prefer-offline

# Build workspace dependencies first (they export from dist/)
RUN pnpm --filter=@thinkneverland/grounded-plugin build && \
    pnpm --filter=@grounded/stripe build

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

USER nextjs

EXPOSE 8080
ENV PORT=8080
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:8080/api/health || exit 1

# Run Prisma db push on startup to ensure schema is in sync, then start the server
# IMPORTANT: Do NOT use --accept-data-loss here — it drops tables not in the Prisma
# schema, which would wipe the engine tables (tenants, jobs, api_keys, etc.)
CMD ["sh", "-c", "prisma db push --schema packages/app/prisma/schema --skip-generate 2>&1 || true && node packages/app/server.js"]
