export const dynamic = "force-dynamic";

import { handleBrandLogoEmailRequest } from "@thinkneverland/pixie-dust-dashboard/server";
import { prisma } from "@thinkneverland/pixie-dust-database/server";

/**
 * Email-safe logo endpoint. `buildEmailBranding` hardcodes this URL
 * into every outgoing email, so downstream apps have to expose the
 * route. All the tenant-raster-or-fallback logic lives upstream in
 * `@thinkneverland/pixie-dust-dashboard/server` — this file only
 * exists to satisfy Next.js's file-based routing.
 */
export async function GET(req: Request) {
  return handleBrandLogoEmailRequest(req, prisma, {
    fallbackPath: "/logo.png",
  });
}
