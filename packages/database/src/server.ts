/**
 * LintPDF Database — Server-only Exports
 *
 * This package provides LintPDF's extended Prisma client with custom tenant
 * structure and preflight engine models. Everything here depends on Node.js
 * built-ins and must NOT be imported in browser/client bundles.
 *
 * Import from `@lintpdf/database/server` in server-side code only.
 * For browser-safe types and enums, import from `@lintpdf/database`.
 */

import { PrismaClient } from "./generated/client";

// Singleton Prisma client instance
let prisma: PrismaClient;

declare global {
  // eslint-disable-next-line no-var
  var __prisma: PrismaClient | undefined;
}

export function getPrismaClient(): PrismaClient {
  if (!global.__prisma) {
    global.__prisma = new PrismaClient();
  }
  return global.__prisma;
}

// Export the singleton prisma client
export const prisma = getPrismaClient();

// Export types from generated client
export type * from "./generated/client";

// Export the PrismaClient class for advanced usage
export { PrismaClient };
