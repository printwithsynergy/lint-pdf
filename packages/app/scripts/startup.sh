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

prisma db execute --schema packages/app/prisma/schema --stdin <<'SQL'
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
SQL

echo "Step 1 complete (exit code: $?)"

# Step 2: Prisma db push (may warn about engine tables — we continue regardless)
echo "Step 2: Running prisma db push..."
prisma db push --schema packages/app/prisma/schema --skip-generate 2>&1 || echo "prisma db push had warnings — continuing"

# Step 3: Seed (idempotent)
echo "Step 3: Running seed..."
node packages/app/prisma/seed.mjs 2>&1 || true

# Step 4: Start the server
echo "Step 4: Starting Next.js server..."
exec node packages/app/server.js
