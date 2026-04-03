/**
 * LintPDF Database — Browser-safe Exports
 *
 * This barrel export contains only types, enums, and constants that are safe
 * for webpack/browser bundling. Zero dependency on Node.js built-ins.
 *
 * For PrismaClient and server utilities, import from:
 * `@lintpdf/database/server`
 *
 * @packageDocumentation
 */

// Browser-safe: types + enums only (uses @prisma/client/runtime/index-browser, no node: imports)
export * from "./generated/client/browser";

// Type-only re-exports from server module (erased at compile time, zero runtime cost)
export type { PrismaClient } from "./server";
