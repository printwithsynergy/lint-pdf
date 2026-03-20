import { z } from "zod";

/**
 * Configuration schema for the Grounded plugin.
 * Validated at plugin registration time.
 */
export const groundedConfigSchema = z.object({
  /** Base URL of the Grounded API (e.g. https://api.grounded.thinkneverland.com) */
  apiUrl: z.string().url(),

  /** HMAC secret for verifying webhook signatures from Grounded */
  webhookSecret: z.string().min(16),

  /** API key for authenticating with Grounded (stored per-tenant) */
  apiKey: z.string().optional(),
});

export type GroundedPluginConfig = z.infer<typeof groundedConfigSchema>;
