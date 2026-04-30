/**
 * Vitest config for @lintpdf/viewer-shared.
 *
 * Phase 2 setup. Subsequent PRs will move the 16 pure-core components
 * into src/core/components/ with snapshot tests written per-component
 * before each move. This config establishes the test harness those
 * snapshots will use.
 */

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/**/index.ts"],
    },
  },
});
