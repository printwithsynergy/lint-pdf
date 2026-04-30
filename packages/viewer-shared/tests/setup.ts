/**
 * Test setup for @lintpdf/viewer-shared.
 *
 * Loads jest-dom matchers (toBeInTheDocument, toHaveClass, etc.) and
 * stubs browser APIs that components reach for but jsdom doesn't
 * implement. Snapshot tests in tests/core/ rely on this setup
 * loading before any test file evaluates.
 */

import "@testing-library/jest-dom/vitest";

// PDF viewer components occasionally call ResizeObserver during mount
// (e.g., to compute viewport-aware layout). jsdom doesn't ship one.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  } as unknown as typeof ResizeObserver;
}

// matchMedia is a similar story — components that branch on
// `prefers-reduced-motion` etc. trip without it.
if (typeof globalThis.matchMedia === "undefined") {
  globalThis.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof matchMedia;
}
