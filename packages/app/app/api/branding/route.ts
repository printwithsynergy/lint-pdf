export const dynamic = "force-dynamic";

/**
 * Alias of /api/admin/branding — see admin-branding-handler.ts for details.
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
