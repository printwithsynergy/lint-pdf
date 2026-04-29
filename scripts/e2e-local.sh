#!/usr/bin/env bash
set -euo pipefail

# ============================================
# LintPDF — Local E2E Test Runner (no Docker)
#
# Usage:
#   bash scripts/e2e-local.sh              # Run all tests
#   bash scripts/e2e-local.sh --headed     # Run with browser visible
#   bash scripts/e2e-local.sh tests/e2e/  # Run specific tests
#
# Environment:
#   SKIP_BROWSERS — set to "true" to skip Playwright browser install
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_PID=""

cleanup() {
  echo ""
  echo "Cleaning up..."
  if [ -n "$APP_PID" ]; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
  # Clean up PostgreSQL if we started it
  if [ "$STARTED_PG" = true ] && [ -n "$PG_TMP_DIR" ]; then
    echo "Stopping ephemeral PostgreSQL..."
    pg_ctl -D "$PG_TMP_DIR" stop -m fast 2>/dev/null || true
    rm -rf "$PG_TMP_DIR" 2>/dev/null || true
  fi
  # Clean up auth state files
  rm -f "$ROOT_DIR/packages/web/tests/e2e/auth-state-"*.json 2>/dev/null || true
}
trap cleanup EXIT

# ============================================
# Phase 1: Prerequisites
# ============================================
check_prereqs() {
  echo "=== Checking prerequisites ==="

  command -v node >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
  command -v pnpm >/dev/null 2>&1 || { echo "ERROR: pnpm not found"; exit 1; }

  echo "  ✓ node $(node --version)"
  echo "  ✓ pnpm $(pnpm --version)"
}

# ============================================
# Phase 2: Database setup (PostgreSQL)
# ============================================
setup_database() {
  echo ""
  echo "=== Setting up PostgreSQL database ==="

  # Postgres defaults (for local detection)
  E2E_DB_NAME="${E2E_DB_NAME:-lintpdf_e2e}"
  E2E_DB_USER="${E2E_DB_USER:-postgres}"
  E2E_DB_PASS="${E2E_DB_PASS:-postgres}"
  E2E_DB_HOST="${E2E_DB_HOST:-localhost}"
  E2E_DB_PORT="${E2E_DB_PORT:-5434}"  # Different port to avoid conflicts

  STARTED_PG=false
  PG_TMP_DIR=""

  # Try to connect to existing Postgres
  if psql -h "$E2E_DB_HOST" -p "$E2E_DB_PORT" -U "$E2E_DB_USER" -d postgres -c "SELECT 1;" >/dev/null 2>&1; then
    echo "  Using existing PostgreSQL on $E2E_DB_HOST:$E2E_DB_PORT"
    createdb -h "$E2E_DB_HOST" -p "$E2E_DB_PORT" -U "$E2E_DB_USER" "$E2E_DB_NAME" 2>/dev/null || \
      createdb -h "$E2E_DB_HOST" -p "$E2E_DB_PORT" -U "$E2E_DB_USER" "$E2E_DB_NAME" 2>/dev/null || true
    export DATABASE_URL="postgresql://$E2E_DB_USER@$E2E_DB_HOST:$E2E_DB_PORT/$E2E_DB_NAME"
    export DIRECT_URL="$DATABASE_URL"
    echo "  Database: $E2E_DB_NAME on $E2E_DB_HOST:$E2E_DB_PORT"
    return
  fi

  # Start ephemeral PostgreSQL
  if command -v initdb >/dev/null 2>&1 && command -v pg_ctl >/dev/null 2>&1; then
    echo "  Starting ephemeral PostgreSQL..."
    PG_TMP_DIR=$(mktemp -d)
    initdb -D "$PG_TMP_DIR" --no-locale --encoding=UTF8 --auth=trust >/dev/null
    
    # Create postgresql.conf with custom port
    cat > "$PG_TMP_DIR/postgresql.conf" << EOF
port = $E2E_DB_PORT
unix_socket_directories = '/tmp'
listen_addresses = 'localhost'
max_connections = 100
shared_buffers = 128MB
EOF

    pg_ctl -D "$PG_TMP_DIR" start -l "$PG_TMP_DIR/pg.log" -o "-c listen_addresses=localhost -c port=$E2E_DB_PORT" >/dev/null
    STARTED_PG=true
    
    # Wait for PostgreSQL to be ready
    for i in $(seq 1 30); do
      if pg_isready -h localhost -p "$E2E_DB_PORT" -q; then
        break
      fi
      if [ "$i" -eq 30 ]; then
        echo "ERROR: PostgreSQL failed to start"
        exit 1
      fi
      sleep 1
    done
    
    createdb -h localhost -p "$E2E_DB_PORT" -U "$E2E_DB_USER" "$E2E_DB_NAME" 2>/dev/null || true
    export DATABASE_URL="postgresql://$E2E_DB_USER@localhost:$E2E_DB_PORT/$E2E_DB_NAME"
    export DIRECT_URL="$DATABASE_URL"
    echo "  Ephemeral PostgreSQL running on port $E2E_DB_PORT"
    return
  fi

  echo "ERROR: No PostgreSQL available."
  echo "  Options:"
  echo "    1. Set DATABASE_URL env var to a reachable Postgres"
  echo "    2. Install PostgreSQL locally (apt install postgresql)"
  echo "    3. Start a Postgres service"
  exit 1
}

# ============================================
# Phase 3: Environment variables
# ============================================
setup_env() {
  echo ""
  echo "=== Setting test environment ==="

  export NODE_ENV=development
  export MCP_BACKDOOR=true
  export MCP_SECRET_KEY="${MCP_SECRET_KEY:-test-secret-key-minimum-32-characters!!}"
  export COOKIE_SECRET="${COOKIE_SECRET:-e2e-test-cookie-secret-minimum-32-chars!!}"
  export MAGIC_LINK_SECRET="${MAGIC_LINK_SECRET:-e2e-test-magic-link-secret-min-32-chars!!}"
  export SESSION_SECRET="${SESSION_SECRET:-e2e-test-session-secret-minimum-32-chars!!}"
  export APP_URL="${APP_URL:-http://localhost:3001}"  # Already unique port
  export PORT="${PORT:-3001}"
  export SITE_URL="${SITE_URL:-http://localhost:3001}"

  # Other required environment variables
  export RESEND_API_KEY="${RESEND_API_KEY:-re_test_dummy}"
  export EMAIL_FROM="${EMAIL_FROM:-noreply@lintpdf.dev}"
  export STRIPE_MODE="${STRIPE_MODE:-standard}"
  export STRIPE_SANDBOX="${STRIPE_SANDBOX:-true}"
  export STRIPE_SDB_SECRET_KEY="${STRIPE_SDB_SECRET_KEY:-sk_test_dummy}"
  export STRIPE_SDB_PUBLISHABLE_KEY="${STRIPE_SDB_PUBLISHABLE_KEY:-pk_test_dummy}"
  export STRIPE_SDB_WEBHOOK_SECRET="${STRIPE_SDB_WEBHOOK_SECRET:-whsec_dummy}"
  export RATE_LIMIT_WINDOW_MS="${RATE_LIMIT_WINDOW_MS:-60000}"
  export RATE_LIMIT_MAX_REQUESTS="${RATE_LIMIT_MAX_REQUESTS:-100}"

  # Unset BASE_URL so Playwright starts the dev server via webServer config
  unset BASE_URL 2>/dev/null || true

  echo "  NODE_ENV=$NODE_ENV"
  echo "  MCP_BACKDOOR=$MCP_BACKDOOR"
  echo "  APP_URL=$APP_URL"
  echo "  PORT=$PORT"
}

# ============================================
# Phase 4: Prisma setup
# ============================================
setup_prisma() {
  echo ""
  echo "=== Setting up database schema ==="

  cd "$ROOT_DIR"
  
  # Generate Prisma client
  pnpm --filter @lintpdf/database exec prisma generate 2>&1 | tail -3
  
  # Push schema to PostgreSQL
  pnpm --filter @lintpdf/database exec prisma db push --accept-data-loss 2>&1 | tail -3
  
  echo "  Database schema ready"
}

# ============================================
# Phase 5: Build application
# ============================================
build_app() {
  echo ""
  echo "=== Building application ==="

  cd "$ROOT_DIR"
  pnpm --filter @thinkneverland/lintpdf-web build 2>&1 | tail -3
  
  echo "  Application built"
}

# ============================================
# Phase 6: Playwright browsers
# ============================================
ensure_browsers() {
  if [ "${SKIP_BROWSERS:-}" = "true" ]; then
    echo ""
    echo "=== Skipping browser install (SKIP_BROWSERS=true) ==="
    return
  fi

  echo ""
  echo "=== Ensuring Playwright browsers ==="

  cd "$ROOT_DIR/packages/web"
  # Install chromium (--with-deps installs system libs on Linux)
  npx playwright install chromium --with-deps 2>/dev/null || npx playwright install chromium 2>/dev/null || true
  echo "  Chromium ready"
}

# ============================================
# Phase 7: Run tests
# ============================================
run_tests() {
  echo ""
  echo "=== Running Playwright E2E tests ==="
  echo ""

  cd "$ROOT_DIR/packages/web"
  npx playwright test "$@"
}

# ============================================
# Main
# ============================================
main() {
  echo "=========================================="
  echo "  LintPDF E2E Tests (local, no Docker)"
  echo "=========================================="

  check_prereqs
  setup_env
  setup_database
  setup_prisma
  build_app
  ensure_browsers
  run_tests "$@"
}

main "$@"
