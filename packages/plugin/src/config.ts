import { z } from "zod";

/**
 * Configuration schema for the LintPDF plugin.
 * Validated at plugin registration time.
 */
export const lintpdfConfigSchema = z.object({
  /** Base URL of the LintPDF API (e.g. https://api.lintpdf.com) */
  apiUrl: z.string().url(),

  /** HMAC secret for verifying webhook signatures from LintPDF */
  webhookSecret: z.string().min(16),

  /** API key for authenticating with LintPDF (stored per-tenant) */
  apiKey: z.string().optional(),
});

export type LintPDFPluginConfig = z.infer<typeof lintpdfConfigSchema>;
