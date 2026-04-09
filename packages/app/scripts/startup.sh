#!/bin/sh
# LintPDF app startup script for Railway.
# Safely migrates the database, seeds, and starts the server.
# NOTE: No set -e — each step has its own error handling and we must
# always reach the server start even if migration/seed has warnings.

echo "=== LintPDF App Startup ==="

# Step 1: Add missing columns via raw SQL (safe — IF NOT EXISTS, no drops)
# This handles columns added to the Prisma schema that prisma db push
# can't apply without --accept-data-loss (because engine tables exist).
# Uses prisma db execute instead of node -e because @prisma/client
# is not available as a CJS require in the standalone Next.js output.
echo "Step 1: Ensuring new columns exist..."

prisma db execute --schema prisma/schema --stdin <<'SQL'
-- AppSettings columns required by pixie-dust-dashboard
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "primaryColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "accentColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "emailButtonColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "brandLogoUrlDark" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginBgColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginCardColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginTextColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginInputColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginRingColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginBgColorDark" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginCardColorDark" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginTextColorDark" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginInputColorDark" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginRingColorDark" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "sidebarBgColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "sidebarTextColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "sidebarAccentColor" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "faviconUrl" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginHeading" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "loginSubheading" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "disabledPlugins" TEXT;

-- MagicLink ipAddress column added in PD update
ALTER TABLE "MagicLink" ADD COLUMN IF NOT EXISTS "ipAddress" TEXT;
CREATE INDEX IF NOT EXISTS "MagicLink_ipAddress_idx" ON "MagicLink"("ipAddress");

-- ApiKey table (pixie-dust-api-keys plugin)
CREATE TABLE IF NOT EXISTS "ApiKey" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "prefix" TEXT NOT NULL,
  "hash" TEXT NOT NULL,
  "expiresAt" TIMESTAMP(3),
  "lastUsedAt" TIMESTAMP(3),
  "revokedAt" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "ApiKey_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "ApiKey_tenantId_idx" ON "ApiKey"("tenantId");
CREATE INDEX IF NOT EXISTS "ApiKey_hash_idx" ON "ApiKey"("hash");
CREATE INDEX IF NOT EXISTS "ApiKey_prefix_idx" ON "ApiKey"("prefix");

-- UsageMeter table (pixie-dust-usage plugin)
CREATE TABLE IF NOT EXISTS "UsageMeter" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "metric" TEXT NOT NULL,
  "value" BIGINT NOT NULL DEFAULT 0,
  "period" TEXT NOT NULL,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "UsageMeter_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "UsageMeter_tenantId_metric_period_key" UNIQUE ("tenantId", "metric", "period")
);
CREATE INDEX IF NOT EXISTS "UsageMeter_tenantId_idx" ON "UsageMeter"("tenantId");
CREATE INDEX IF NOT EXISTS "UsageMeter_metric_idx" ON "UsageMeter"("metric");

-- WebhookEndpoint table (pixie-dust-webhooks plugin)
CREATE TABLE IF NOT EXISTS "WebhookEndpoint" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "url" TEXT NOT NULL,
  "secret" TEXT NOT NULL,
  "events" TEXT[] NOT NULL,
  "active" BOOLEAN NOT NULL DEFAULT true,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "WebhookEndpoint_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "WebhookEndpoint_tenantId_idx" ON "WebhookEndpoint"("tenantId");
CREATE INDEX IF NOT EXISTS "WebhookEndpoint_active_idx" ON "WebhookEndpoint"("active");

-- WebhookDelivery table (pixie-dust-webhooks plugin)
CREATE TABLE IF NOT EXISTS "WebhookDelivery" (
  "id" TEXT NOT NULL,
  "endpointId" TEXT NOT NULL,
  "event" TEXT NOT NULL,
  "payload" JSONB NOT NULL,
  "status" INTEGER NOT NULL,
  "response" TEXT,
  "attempts" INTEGER NOT NULL DEFAULT 1,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "WebhookDelivery_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "WebhookDelivery_endpointId_fkey" FOREIGN KEY ("endpointId") REFERENCES "WebhookEndpoint"("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "WebhookDelivery_endpointId_idx" ON "WebhookDelivery"("endpointId");
CREATE INDEX IF NOT EXISTS "WebhookDelivery_event_idx" ON "WebhookDelivery"("event");
CREATE INDEX IF NOT EXISTS "WebhookDelivery_createdAt_idx" ON "WebhookDelivery"("createdAt");

-- PluginSettings table (pixie-dust-fairy-ring plugin)
CREATE TABLE IF NOT EXISTS "PluginSettings" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT,
  "pluginName" TEXT NOT NULL,
  "settings" JSONB NOT NULL DEFAULT '{}',
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "PluginSettings_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "PluginSettings_tenantId_pluginName_key" UNIQUE ("tenantId", "pluginName")
);
CREATE INDEX IF NOT EXISTS "PluginSettings_tenantId_idx" ON "PluginSettings"("tenantId");
CREATE INDEX IF NOT EXISTS "PluginSettings_pluginName_idx" ON "PluginSettings"("pluginName");

-- Annotation table for PDF viewer markup
CREATE TABLE IF NOT EXISTS "Annotation" (
  "id" TEXT NOT NULL,
  "jobId" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "pageNum" INTEGER NOT NULL,
  "authorId" TEXT,
  "authorEmail" TEXT NOT NULL,
  "authorName" TEXT,
  "fabricJson" JSONB NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Annotation_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "Annotation_jobId_pageNum_idx" ON "Annotation"("jobId", "pageNum");
CREATE INDEX IF NOT EXISTS "Annotation_tenantId_idx" ON "Annotation"("tenantId");

-- ReportView table for tracking who viewed shared reports
CREATE TABLE IF NOT EXISTS "ReportView" (
  "id" TEXT NOT NULL,
  "jobId" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "reportToken" TEXT NOT NULL,
  "viewerEmail" TEXT,
  "viewerName" TEXT,
  "ipAddress" TEXT,
  "userAgent" TEXT,
  "viewedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "ReportView_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "ReportView_jobId_idx" ON "ReportView"("jobId");
CREATE INDEX IF NOT EXISTS "ReportView_tenantId_viewedAt_idx" ON "ReportView"("tenantId", "viewedAt");
CREATE INDEX IF NOT EXISTS "ReportView_reportToken_idx" ON "ReportView"("reportToken");

-- Engine: white-label custom report domain columns (Alembic 014).
-- These live in the engine-owned "tenants" and "brand_profiles" tables, but
-- adding them here as well means the columns exist even when Alembic hasn't
-- run yet (e.g. during a deploy where the app boots before the worker).
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS brand_custom_domain_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS brand_custom_domain_requested_at TIMESTAMPTZ NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_brand_custom_domain_unique
  ON tenants (brand_custom_domain)
  WHERE brand_custom_domain IS NOT NULL;

ALTER TABLE brand_profiles
  ADD COLUMN IF NOT EXISTS custom_domain VARCHAR(255) NULL;
ALTER TABLE brand_profiles
  ADD COLUMN IF NOT EXISTS custom_domain_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE brand_profiles
  ADD COLUMN IF NOT EXISTS custom_domain_requested_at TIMESTAMPTZ NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_brand_profiles_custom_domain_unique
  ON brand_profiles (custom_domain)
  WHERE custom_domain IS NOT NULL;

-- One-shot data migration: rewrite any logo URLs still pinned to the dead
-- reports.lintpdf.com host (never configured in DNS) to the working
-- api.lintpdf.com host. Safe to run repeatedly — a no-op on fresh rows.
UPDATE brand_profiles
   SET logo_url = REPLACE(logo_url, 'https://reports.lintpdf.com/', 'https://api.lintpdf.com/')
 WHERE logo_url LIKE 'https://reports.lintpdf.com/%';
UPDATE tenants
   SET brand_logo_url = REPLACE(brand_logo_url, 'https://reports.lintpdf.com/', 'https://api.lintpdf.com/')
 WHERE brand_logo_url LIKE 'https://reports.lintpdf.com/%';
SQL

echo "Step 1 complete (exit code: $?)"

# Step 2: Prisma db push (may warn about engine tables — we continue regardless)
echo "Step 2: Running prisma db push..."
prisma db push --schema prisma/schema --skip-generate 2>&1 || echo "prisma db push had warnings — continuing"

# Step 3: Seed (idempotent)
echo "Step 3: Running seed..."
node prisma/seed.mjs 2>&1 || true

# Step 4: Start the server
echo "Step 4: Starting Next.js server..."
exec npx next start
