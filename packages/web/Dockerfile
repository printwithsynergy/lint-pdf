# Build context is the repo root (Railway uses dockerfilePath from root)

# Stage 1: Install dependencies
FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable pnpm
# Copy root workspace config + the web package.json (no lockfile — fresh resolve)
COPY package.json pnpm-workspace.yaml ./
COPY packages/web/package.json packages/web/package.json
RUN pnpm store prune 2>/dev/null || true
RUN pnpm install --filter=@thinkneverland/grounded-web --no-frozen-lockfile

# Stage 2: Build
FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable pnpm
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages/web/node_modules ./packages/web/node_modules
COPY packages/web/ ./packages/web/
WORKDIR /app/packages/web
ENV NEXT_TELEMETRY_DISABLED=1
# NEXT_PUBLIC_ vars are inlined at build time — accept from Railway build args
ARG NEXT_PUBLIC_GROUNDED_BETA_MODE=true
ARG NEXT_PUBLIC_GROUNDED_API_URL
ENV NEXT_PUBLIC_GROUNDED_BETA_MODE=$NEXT_PUBLIC_GROUNDED_BETA_MODE
ENV NEXT_PUBLIC_GROUNDED_API_URL=$NEXT_PUBLIC_GROUNDED_API_URL
RUN pnpm build

# Stage 3: Runtime
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Standalone output preserves monorepo structure:
#   node_modules/next/...           (workspace root)
#   packages/web/server.js          (entrypoint)
#   packages/web/.next/...          (runtime)
COPY --from=builder --chown=nextjs:nodejs /app/packages/web/.next/standalone ./
# Static assets must be placed where Next.js expects them (relative to server.js)
COPY --from=builder --chown=nextjs:nodejs /app/packages/web/.next/static ./packages/web/.next/static
# Public assets
COPY --from=builder /app/packages/web/public ./packages/web/public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "packages/web/server.js"]
