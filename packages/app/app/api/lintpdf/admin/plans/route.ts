export const dynamic = "force-dynamic";

import { requireSuperAdmin } from "@/lib/admin-auth";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

/**
 * List every plan tier with its baseline + ops-edited overrides.
 * Proxies `GET /api/v1/admin/plans` on the engine. Admin-key
 * authentication happens on the engine side; this route just
 * gates on the super-admin cookie.
 */
export async function GET(req: Request) {
  const denied = await requireSuperAdmin(req);
  if (denied) return denied;

  const adminKey = env.LINTPDF_ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json(
      { error: "Admin API key not configured" },
      { status: 503 },
    );
  }
  try {
    const resp = await fetch(`${env.LINTPDF_API_URL}/api/v1/admin/plans`, {
      headers: { "X-Admin-Key": adminKey },
    });
    const text = await resp.text();
    try {
      return NextResponse.json(JSON.parse(text), { status: resp.status });
    } catch {
      return NextResponse.json(
        { error: "Invalid response from engine", detail: text.slice(0, 200) },
        { status: 502 },
      );
    }
  } catch (e) {
    return NextResponse.json(
      {
        error: "Engine unreachable",
        detail: e instanceof Error ? e.message : String(e),
      },
      { status: 502 },
    );
  }
}
