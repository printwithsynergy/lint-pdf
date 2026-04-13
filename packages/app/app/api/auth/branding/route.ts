export const dynamic = "force-dynamic";

/**
 * Alias of /api/admin/branding — Pixie Dust's BrandingPage ships compiled,
 * so we register the handler at several likely URLs (auth/branding mirrors
 * /api/auth/me for user profile).
 */
import {
  handleGet,
  handlePatch,
  handlePost,
  handlePut,
} from "@/lib/admin-branding-handler";

export const GET = handleGet;
export const PATCH = handlePatch;
export const POST = handlePost;
export const PUT = handlePut;
