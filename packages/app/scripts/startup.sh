#!/bin/sh
# LintPDF app startup script for Railway.
# Safely migrates the database, seeds, and starts the server.
# NOTE: No set -e — each step has its own error handling and we must
# always reach the server start even if migration/seed has warnings.

echo "=== LintPDF App Startup ==="

# RAILPACK builds a Next.js standalone image where devDependencies (including
# the `prisma` CLI) get pruned from the production node_modules, so bare
# `prisma` used to fail with "prisma: not found" on every boot — which meant
# Step 1 never ran and every subsequent request 500'd on missing columns
# (AppSettings.themeTokenOverrides, Session.impersonatingTenantId, ...).
# Resolve it through the local bin first, falling back to npx which will
# download the CLI on demand if it's truly absent.
if [ -x "./node_modules/.bin/prisma" ]; then
  PRISMA="./node_modules/.bin/prisma"
elif [ -x "../../node_modules/.bin/prisma" ]; then
  PRISMA="../../node_modules/.bin/prisma"
else
  PRISMA="npx --yes prisma@7"
fi
echo "Using prisma CLI: $PRISMA"

# Step 0: Regenerate the Prisma client against the app's own schema so
# LintPDF-specific columns (Tenant.engineTenantId, Session.impersonatingTenantId,
# etc.) are known to the runtime client. Without this, pnpm's hoisted
# @prisma/client can end up pointed at a sibling package's schema and every
# query touching those columns throws "Unknown field ..." / "Unknown
# argument ...".
echo "Step 0: Generating Prisma client from app schema..."
$PRISMA generate --schema prisma/schema 2>&1 || echo "prisma generate had warnings — continuing"

# Step 1: Add missing columns via raw SQL (safe — IF NOT EXISTS, no drops)
# This handles columns added to the Prisma schema that prisma db push
# can't apply without --accept-data-loss (because engine tables exist).
# Uses prisma db execute instead of node -e because @prisma/client
# is not available as a CJS require in the standalone Next.js output.
echo "Step 1: Ensuring new columns exist..."

$PRISMA db execute --schema prisma/schema --stdin <<'SQL'
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
-- Added in @thinkneverland/pixie-dust-database 2.x (Phase 5 refresh):
-- JSON blob of theme-token overrides applied globally.
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "themeTokenOverrides" TEXT;
ALTER TABLE "AppSettings" ADD COLUMN IF NOT EXISTS "disabledPlugins" TEXT;

-- MagicLink ipAddress column added in PD update
ALTER TABLE "MagicLink" ADD COLUMN IF NOT EXISTS "ipAddress" TEXT;
CREATE INDEX IF NOT EXISTS "MagicLink_ipAddress_idx" ON "MagicLink"("ipAddress");

-- Session.impersonatingTenantId — local-schema extension used by
-- /api/auth/me and the /api/lintpdf/* dispatcher to let a super admin
-- view the dashboard "as" a tenant. The PD-shipped Prisma client
-- doesn't know about this column, so prisma db push won't add it once
-- engine tables are present in the database. Add it explicitly here
-- so super-admin auth queries don't 500 on a fresh deploy.
ALTER TABLE "Session" ADD COLUMN IF NOT EXISTS "impersonatingTenantId" TEXT;

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

-- Stripe billing tables (pixie-dust-stripe-kit). The stripe-kit
-- subscriptions dashboard widget throws P2021 when Subscription is missing,
-- and every checkout flow needs StripeCustomer. Prisma db push can't create
-- them on a DB that already holds engine tables (SQLAlchemy-owned), so mirror
-- the shapes here.
CREATE TABLE IF NOT EXISTS "StripeCustomer" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "stripeCustomerId" TEXT NOT NULL,
  "mode" TEXT NOT NULL DEFAULT 'standard',
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "StripeCustomer_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "StripeCustomer_stripeCustomerId_key" UNIQUE ("stripeCustomerId")
);
CREATE INDEX IF NOT EXISTS "StripeCustomer_tenantId_idx" ON "StripeCustomer"("tenantId");
CREATE INDEX IF NOT EXISTS "StripeCustomer_stripeCustomerId_idx" ON "StripeCustomer"("stripeCustomerId");
CREATE INDEX IF NOT EXISTS "StripeCustomer_mode_idx" ON "StripeCustomer"("mode");

DO $$ BEGIN
  CREATE TYPE "SubscriptionStatus" AS ENUM ('ACTIVE', 'PAST_DUE', 'CANCELED', 'TRIALING', 'INCOMPLETE', 'UNPAID');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS "Subscription" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "stripeSubscriptionId" TEXT NOT NULL,
  "stripePriceId" TEXT NOT NULL,
  "stripeProductId" TEXT,
  "status" "SubscriptionStatus" NOT NULL,
  "currentPeriodStart" TIMESTAMP(3) NOT NULL,
  "currentPeriodEnd" TIMESTAMP(3) NOT NULL,
  "trialEnd" TIMESTAMP(3),
  "cancelAtPeriodEnd" BOOLEAN NOT NULL DEFAULT false,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Subscription_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "Subscription_stripeSubscriptionId_key" UNIQUE ("stripeSubscriptionId")
);
CREATE INDEX IF NOT EXISTS "Subscription_tenantId_idx" ON "Subscription"("tenantId");
CREATE INDEX IF NOT EXISTS "Subscription_stripeSubscriptionId_idx" ON "Subscription"("stripeSubscriptionId");
CREATE INDEX IF NOT EXISTS "Subscription_status_idx" ON "Subscription"("status");

DO $$ BEGIN
  CREATE TYPE "PaymentStatus" AS ENUM ('SUCCEEDED', 'PENDING', 'FAILED', 'REFUNDED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS "Payment" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "stripePaymentId" TEXT NOT NULL,
  "amount" INTEGER NOT NULL,
  "currency" TEXT NOT NULL DEFAULT 'usd',
  "status" "PaymentStatus" NOT NULL,
  "description" TEXT,
  "connectedAccountId" TEXT,
  "applicationFeeAmount" INTEGER,
  "metadata" JSONB NOT NULL DEFAULT '{}',
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Payment_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "Payment_stripePaymentId_key" UNIQUE ("stripePaymentId")
);
CREATE INDEX IF NOT EXISTS "Payment_tenantId_idx" ON "Payment"("tenantId");
CREATE INDEX IF NOT EXISTS "Payment_stripePaymentId_idx" ON "Payment"("stripePaymentId");
CREATE INDEX IF NOT EXISTS "Payment_status_idx" ON "Payment"("status");
CREATE INDEX IF NOT EXISTS "Payment_connectedAccountId_idx" ON "Payment"("connectedAccountId");

CREATE TABLE IF NOT EXISTS "ConnectedAccount" (
  "id" TEXT NOT NULL,
  "tenantId" TEXT NOT NULL,
  "stripeAccountId" TEXT NOT NULL,
  "email" TEXT NOT NULL,
  "businessName" TEXT,
  "onboardingComplete" BOOLEAN NOT NULL DEFAULT false,
  "payoutsEnabled" BOOLEAN NOT NULL DEFAULT false,
  "chargesEnabled" BOOLEAN NOT NULL DEFAULT false,
  "feePercent" DOUBLE PRECISION NOT NULL DEFAULT 0.2,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "ConnectedAccount_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "ConnectedAccount_stripeAccountId_key" UNIQUE ("stripeAccountId")
);
CREATE INDEX IF NOT EXISTS "ConnectedAccount_tenantId_idx" ON "ConnectedAccount"("tenantId");
CREATE INDEX IF NOT EXISTS "ConnectedAccount_stripeAccountId_idx" ON "ConnectedAccount"("stripeAccountId");

CREATE TABLE IF NOT EXISTS "WebhookEvent" (
  "id" TEXT NOT NULL,
  "stripeEventId" TEXT NOT NULL,
  "eventType" TEXT NOT NULL,
  "processedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "WebhookEvent_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "WebhookEvent_stripeEventId_key" UNIQUE ("stripeEventId")
);
CREATE INDEX IF NOT EXISTS "WebhookEvent_stripeEventId_idx" ON "WebhookEvent"("stripeEventId");
CREATE INDEX IF NOT EXISTS "WebhookEvent_eventType_idx" ON "WebhookEvent"("eventType");

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
-- Alembic 024: share_email_required toggle. Default true preserves the
-- pre-existing behaviour for every existing tenant (public share-link
-- viewers are gated behind an email prompt). Admins flip it to false
-- for tenants that share internally and don't need lead-gen.
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS share_email_required BOOLEAN NOT NULL DEFAULT true;

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
-- Alembic 023: widen report_tokens.format from VARCHAR(10) to VARCHAR(32) so
-- 'annotated_pdf' (13 chars) and 'annotated_pdf_markup' (20 chars) can persist.
-- Without this the mint endpoint 500'd with StringDataRightTruncation for
-- every request that asked for either format, even though the code path
-- produced valid PDF bytes and had already uploaded them to R2.
ALTER TABLE report_tokens
  ALTER COLUMN format TYPE VARCHAR(32);

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
-- Alembic 025: per-token email-gate override. NULL = inherit the tenant's
-- share_email_required setting. True/False = force the gate on/off for
-- this specific token regardless of tenant default. Lets a tenant mint
-- both gated (external) and ungated (internal) links in one session.
ALTER TABLE report_tokens
  ADD COLUMN IF NOT EXISTS require_visitor_email BOOLEAN;
-- Alembic 026: universal per-call override envelope. JSON blob captured
-- at submit time (jobs.overrides) and mint time (report_tokens.overrides)
-- so every stage of the pipeline honours the caller's per-job / per-mint
-- tweaks — checks, thresholds, color workflow, AI, viewer UI defaults,
-- share-link gating — without re-parsing the request. NULL = no overrides.
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS overrides JSON;
ALTER TABLE report_tokens
  ADD COLUMN IF NOT EXISTS overrides JSON;

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

-- Engine: metered-resource packs (Alembic TBD). Extend the existing
-- tenant_ai_credit_packages table so it holds both AI credits AND
-- file packs, discriminated by ``kind``. Also add per-tenant overrides
-- on tenants so ops can grant VIP customers more than their plan
-- default without changing plan. Additive + defaulted → safe on rows
-- created before the credits+files unification.
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS monthly_ai_credits_override INTEGER NULL;
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS monthly_files_override INTEGER NULL;

ALTER TABLE tenant_ai_credit_packages
  ADD COLUMN IF NOT EXISTS kind VARCHAR(16) NOT NULL DEFAULT 'credits';
ALTER TABLE tenant_ai_credit_packages
  ADD COLUMN IF NOT EXISTS source VARCHAR(32) NOT NULL DEFAULT 'admin_grant';
ALTER TABLE tenant_ai_credit_packages
  ADD COLUMN IF NOT EXISTS stripe_session_id VARCHAR(255);
ALTER TABLE tenant_ai_credit_packages
  ADD COLUMN IF NOT EXISTS billing_period_start TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS ix_ai_credit_packages_stripe_session
  ON tenant_ai_credit_packages(stripe_session_id)
  WHERE stripe_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_ai_credit_packages_tenant_kind
  ON tenant_ai_credit_packages(tenant_id, kind);
SQL

echo "Step 1 complete (exit code: $?)"

# Step 2: Prisma db push (may warn about engine tables — we continue regardless)
echo "Step 2: Running prisma db push..."
$PRISMA db push --schema prisma/schema --skip-generate 2>&1 || echo "prisma db push had warnings — continuing"

# Step 3: Seed (idempotent)
echo "Step 3: Running seed..."
node prisma/seed.mjs 2>&1 || true

# Step 4: Start the server
echo "Step 4: Starting Next.js server..."
exec npx next start
