#!/bin/sh
# LintPDF E2E Test Runner
#
# Starts all services in Docker, runs Playwright tests, then cleans up.
# Usage: ./scripts/e2e.sh
#
# Stripe tests auto-skip (no STRIPE_SECRET_KEY set).
# Reports saved to ./playwright-report/

set -e

echo "=== LintPDF E2E Tests ==="
echo "Starting services..."

# Build and run all services, exit when playwright finishes
docker compose -f docker-compose.e2e.yml up \
  --build \
  --abort-on-container-exit \
  --exit-code-from playwright
EXIT_CODE=$?

# Clean up containers and volumes
echo "Cleaning up..."
docker compose -f docker-compose.e2e.yml down -v --remove-orphans 2>/dev/null

if [ $EXIT_CODE -eq 0 ]; then
  echo "=== E2E TESTS PASSED ==="
else
  echo "=== E2E TESTS FAILED ==="
  echo "Reports available at: ./playwright-report/"
fi

exit $EXIT_CODE
