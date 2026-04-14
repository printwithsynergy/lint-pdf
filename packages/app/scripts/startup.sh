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

-- Engine: preflight_source enum + Job columns + JobImportedReport table (Alembic 019).
-- Mirrored here so the app can boot against a DB where Alembic hasn't run yet.
DO $$ BEGIN
  CREATE TYPE preflightsource AS ENUM ('engine', 'external', 'minimal');
EXCEPTION WHEN duplicate_object THEN null; END $$;

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS preflight_source preflightsource NOT NULL DEFAULT 'engine';
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS external_format VARCHAR(32);
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS data_capabilities JSON;
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS brand_profile_id_override UUID;
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS unbranded_override BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS unbranded_by_default BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS job_imported_reports (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  format VARCHAR(32) NOT NULL,
  raw_blob_key VARCHAR(512) NOT NULL,
  raw_size_bytes INTEGER NOT NULL DEFAULT 0,
  parser_version VARCHAR(32) NOT NULL DEFAULT '1',
  source_metadata JSON,
  parsed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_job_imported_reports_job ON job_imported_reports(job_id);

-- ReportToken: persist brand choice at mint time so downstream viewers see
-- consistent (possibly anonymous) branding regardless of later tenant changes.
ALTER TABLE report_tokens
  ADD COLUMN IF NOT EXISTS brand_mode VARCHAR(16);
ALTER TABLE report_tokens
  ADD COLUMN IF NOT EXISTS brand_profile_id UUID;

-- Engine: tenant_import_mappings (Alembic 020). Tenant-defined custom
-- parsers so teams with proprietary preflight formats can map their
-- XML/JSON onto engine findings without us shipping a new parser.
CREATE TABLE IF NOT EXISTS tenant_import_mappings (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name VARCHAR(128) NOT NULL,
  description TEXT,
  format VARCHAR(8) NOT NULL DEFAULT 'xml',
  config JSON NOT NULL,
  sample_payload TEXT,
  sample_mime VARCHAR(64),
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_tenant_import_mappings_tenant
  ON tenant_import_mappings(tenant_id);

-- Engine: viewer_annotations + share_link_visitors (Alembic 021). Reviewer
-- drawing/markup layer and email-gated capture for anonymous share-link
-- annotators.
CREATE TABLE IF NOT EXISTS viewer_annotations (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  share_token VARCHAR(255),
  page_num INTEGER NOT NULL,
  kind VARCHAR(16) NOT NULL,
  geometry_json JSON NOT NULL,
  color VARCHAR(16) NOT NULL DEFAULT '#dc2626',
  text TEXT,
  author_email VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_viewer_annotations_job_page
  ON viewer_annotations(job_id, page_num);
CREATE INDEX IF NOT EXISTS ix_viewer_annotations_token
  ON viewer_annotations(share_token);

CREATE TABLE IF NOT EXISTS share_link_visitors (
  id UUID PRIMARY KEY,
  share_token VARCHAR(255) NOT NULL,
  visitor_email VARCHAR(255) NOT NULL,
  ip_hash VARCHAR(64),
  user_agent VARCHAR(512),
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_share_visitors_token
  ON share_link_visitors(share_token);
CREATE INDEX IF NOT EXISTS ix_share_visitors_token_email
  ON share_link_visitors(share_token, visitor_email);

ALTER TABLE report_tokens
  ADD COLUMN IF NOT EXISTS allow_annotations BOOLEAN NOT NULL DEFAULT false;

-- Engine: viewer_annotation_comments (Alembic 022). Threaded replies on
-- a reviewer annotation — the Wave B collaboration surface. Comments
-- cascade-delete with the parent annotation.
CREATE TABLE IF NOT EXISTS viewer_annotation_comments (
  id UUID PRIMARY KEY,
  annotation_id UUID NOT NULL REFERENCES viewer_annotations(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  share_token VARCHAR(255),
  author_email VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_viewer_ann_comments_annotation
  ON viewer_annotation_comments(annotation_id, created_at);
CREATE INDEX IF NOT EXISTS ix_viewer_ann_comments_token
  ON viewer_annotation_comments(share_token);
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
