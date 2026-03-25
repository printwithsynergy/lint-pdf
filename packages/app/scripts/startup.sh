#!/bin/sh
# LintPDF app startup script for Railway.
# Safely migrates the database, seeds, and starts the server.
# NOTE: No set -e — each step has its own error handling and we must
# always reach the server start even if migration/seed has warnings.

echo "=== LintPDF App Startup ==="

# Step 1: Add missing columns via raw SQL (safe — IF NOT EXISTS, no drops)
# This handles columns added to the Prisma schema that prisma db push
# can't apply without --accept-data-loss (because engine tables exist).
echo "Step 1: Ensuring new columns exist..."
node -e "
const { PrismaClient } = require('@prisma/client');
const p = new PrismaClient();
(async () => {
  const cols = [
    ['AppSettings', 'primaryColor', 'TEXT'],
    ['AppSettings', 'emailButtonColor', 'TEXT'],
    ['AppSettings', 'loginBgColor', 'TEXT'],
    ['AppSettings', 'loginHeading', 'TEXT'],
    ['AppSettings', 'loginSubheading', 'TEXT'],
  ];
  for (const [table, col, type] of cols) {
    try {
      await p.\$executeRawUnsafe(
        'ALTER TABLE \"' + table + '\" ADD COLUMN IF NOT EXISTS \"' + col + '\" ' + type
      );
    } catch (e) {
      // Column may already exist or table doesn't exist yet — both fine
    }
  }
  // Ensure new tables exist (Annotation, ReportView)
  const tables = [
    'CREATE TABLE IF NOT EXISTS \"Annotation\" (\"id\" TEXT NOT NULL, \"jobId\" TEXT NOT NULL, \"tenantId\" TEXT NOT NULL, \"pageNum\" INTEGER NOT NULL, \"authorId\" TEXT, \"authorEmail\" TEXT NOT NULL, \"authorName\" TEXT, \"fabricJson\" JSONB NOT NULL, \"createdAt\" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP, \"updatedAt\" TIMESTAMP(3) NOT NULL, CONSTRAINT \"Annotation_pkey\" PRIMARY KEY (\"id\"))',
    'CREATE INDEX IF NOT EXISTS \"Annotation_jobId_pageNum_idx\" ON \"Annotation\"(\"jobId\", \"pageNum\")',
    'CREATE INDEX IF NOT EXISTS \"Annotation_tenantId_idx\" ON \"Annotation\"(\"tenantId\")',
    'CREATE TABLE IF NOT EXISTS \"ReportView\" (\"id\" TEXT NOT NULL, \"jobId\" TEXT NOT NULL, \"tenantId\" TEXT NOT NULL, \"reportToken\" TEXT NOT NULL, \"viewerEmail\" TEXT, \"viewerName\" TEXT, \"ipAddress\" TEXT, \"userAgent\" TEXT, \"viewedAt\" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP, CONSTRAINT \"ReportView_pkey\" PRIMARY KEY (\"id\"))',
    'CREATE INDEX IF NOT EXISTS \"ReportView_jobId_idx\" ON \"ReportView\"(\"jobId\")',
    'CREATE INDEX IF NOT EXISTS \"ReportView_tenantId_viewedAt_idx\" ON \"ReportView\"(\"tenantId\", \"viewedAt\")',
    'CREATE INDEX IF NOT EXISTS \"ReportView_reportToken_idx\" ON \"ReportView\"(\"reportToken\")',
  ];
  for (const sql of tables) {
    try { await p.\$executeRawUnsafe(sql); } catch (e) { /* already exists */ }
  }
  await p.\$disconnect();
  console.log('Pre-migration: columns and tables ensured.');
})();
" 2>&1 || echo "Pre-migration had warnings — continuing"

# Step 2: Prisma db push (may warn about engine tables — we continue regardless)
echo "Step 2: Running prisma db push..."
prisma db push --schema packages/app/prisma/schema --skip-generate 2>&1 || echo "prisma db push had warnings — continuing"

# Step 3: Seed (idempotent)
echo "Step 3: Running seed..."
node packages/app/prisma/seed.mjs 2>&1 || true

# Step 4: Start the server
echo "Step 4: Starting Next.js server..."
exec node packages/app/server.js
