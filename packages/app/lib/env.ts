import {
  baseEnvSchema,
  createEnvProxy,
} from "@thinkneverland/pixie-dust-config";
import { z } from "zod";

const envSchema = baseEnvSchema.extend({
  // Stripe
  STRIPE_SECRET_KEY: z.string().min(1),
  STRIPE_PUBLISHABLE_KEY: z.string().min(1),
  STRIPE_WEBHOOK_SECRET: z.string().min(1),
  STRIPE_MODE: z.enum(["standard", "connect"]).default("standard"),
  STRIPE_SANDBOX: z.string().default("true"),

  // LintPDF engine
  LINTPDF_API_URL: z.string().url(),
  LINTPDF_WEBHOOK_SECRET: z.string().default(""),
  LINTPDF_API_KEY: z.string().optional(),
  LINTPDF_ADMIN_API_KEY: z.string().optional(),
});

export const env = createEnvProxy(envSchema);
