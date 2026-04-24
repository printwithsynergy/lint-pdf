#!/usr/bin/env bash
# Phase 4 investigation runbook — run from a shell with TCP access to
# ballast.proxy.rlwy.net:23076 (i.e. your local machine, not the
# sandboxed Claude session).
#
# Usage:
#   DB_URL="postgresql://…" bash scripts/phase4-investigate.sh > phase4-output.txt
#   (then paste phase4-output.txt back into the Claude session)
#
# Safety:
#   - Read-only. All queries are SELECT. No schema or data is modified.
#   - Prints 10–50 rows per topic; nothing customer-sensitive is
#     exported beyond metadata.

set -euo pipefail

if [[ -z "${DB_URL:-}" ]]; then
  echo "ERROR: set DB_URL env var (postgresql://…)" >&2
  exit 1
fi

psql_ro() { psql "$DB_URL" -A -F $'\t' -t -c "$1"; }
section() { echo; echo "## $1"; echo; }

# ── Phase 4.1 — /dashboard/usage shows 0 for quincy@thinkneverland.com ──

section "Phase 4.1 — usage events for quincy's tenant"

echo "### App-side tenant for quincy@thinkneverland.com"
psql "$DB_URL" -c "
  SELECT u.id   AS user_id,
         u.email,
         tu.role,
         t.id   AS app_tenant_id,
         t.slug AS tenant_slug,
         t.\"engineTenantId\" AS engine_tenant_id
    FROM \"User\" u
    JOIN \"TenantUser\" tu ON tu.\"userId\" = u.id
    JOIN \"Tenant\" t ON t.id = tu.\"tenantId\"
   WHERE u.email = 'quincy@thinkneverland.com';
"

echo "### Engine-side tenant rows with contact_email matching quincy"
psql "$DB_URL" -c "
  SELECT id, name, contact_email, plan, rate_limit_daily
    FROM tenants
   WHERE contact_email ILIKE '%quincy%'
      OR name ILIKE '%thinkneverland%'
   ORDER BY name;
"

echo "### Engine job rows for likely tenant ids (last 30 days)"
psql "$DB_URL" -c "
  SELECT tenant_id, COUNT(*)          AS jobs,
                   MIN(created_at)    AS first_job,
                   MAX(created_at)    AS last_job
    FROM jobs
   WHERE created_at > now() - interval '30 days'
   GROUP BY tenant_id
   ORDER BY jobs DESC
   LIMIT 10;
"

echo "### If there is a dedicated usage_events table, row counts per tenant"
psql "$DB_URL" -c "
  SELECT to_regclass('public.usage_events') IS NOT NULL AS usage_events_exists;
"
psql "$DB_URL" -c "
  SELECT tenant_id, COUNT(*) AS events,
         MIN(created_at) AS first, MAX(created_at) AS last
    FROM usage_events
   WHERE created_at > now() - interval '30 days'
   GROUP BY tenant_id
   ORDER BY events DESC
   LIMIT 10;
" 2>&1 | head -30 || true

# ── Phase 4.2 — /dashboard/downloads no releases ──

section "Phase 4.2 — desktop entitlement + release manifest"

echo "### Tenants with desktop_app_enabled set"
psql "$DB_URL" -c "
  SELECT id, name, contact_email,
         entitlement_overrides -> 'desktop_app_enabled' AS desktop_flag
    FROM tenants
   WHERE entitlement_overrides ? 'desktop_app_enabled'
   ORDER BY name
   LIMIT 25;
"

echo "### Tables that look like desktop-release storage"
psql "$DB_URL" -c "
  SELECT tablename
    FROM pg_tables
   WHERE schemaname = 'public'
     AND (tablename ILIKE '%desktop%'
       OR tablename ILIKE '%release%'
       OR tablename ILIKE '%download%');
"

echo "### If desktop_releases exists, show recent rows"
psql "$DB_URL" -c "
  SELECT to_regclass('public.desktop_releases') IS NOT NULL AS desktop_releases_exists;
"
psql "$DB_URL" -c "
  SELECT * FROM desktop_releases ORDER BY released_at DESC LIMIT 5;
" 2>&1 | head -30 || true

# ── Phase 4.4 — /dashboard/admin/reports views always 0 ──

section "Phase 4.4 — public report tokens + view counts"

echo "### accessed_count distribution"
psql "$DB_URL" -c "
  SELECT (accessed_count > 0)::text AS has_views, COUNT(*) AS tokens
    FROM public_report_token
   GROUP BY 1
   ORDER BY 1;
"

echo "### Top 10 most-viewed reports"
psql "$DB_URL" -c "
  SELECT id, tenant_id, accessed_count, created_at, last_accessed_at
    FROM public_report_token
   ORDER BY accessed_count DESC
   LIMIT 10;
"

echo "### Most recent 10 tokens regardless of access"
psql "$DB_URL" -c "
  SELECT id, tenant_id, accessed_count, created_at, last_accessed_at
    FROM public_report_token
   ORDER BY created_at DESC
   LIMIT 10;
"

# ── Phase 4.3 bonus — tile warming ──

section "Phase 4.3 bonus — tile warming activity"

echo "### Recent warm_viewer_tiles task invocations (look for task_name or the queue_log table if present)"
psql "$DB_URL" -c "
  SELECT tablename
    FROM pg_tables
   WHERE schemaname = 'public'
     AND (tablename ILIKE '%celery%' OR tablename ILIKE '%task%' OR tablename ILIKE '%warm%');
"

echo
echo "=== End of runbook ==="
