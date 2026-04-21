export const dynamic = "force-dynamic";

import { requireSuperAdmin } from "@/lib/admin-auth";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

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

  const { searchParams } = new URL(req.url);
  const qs = new URLSearchParams();
  qs.set("page", searchParams.get("page") ?? "1");
  qs.set("page_size", searchParams.get("page_size") ?? "50");
  const dead = searchParams.get("dead");
  if (dead !== null) qs.set("dead", dead);
  const tenantId = searchParams.get("tenant_id");
  if (tenantId) qs.set("tenant_id", tenantId);

  try {
    const resp = await fetch(
      `${env.LINTPDF_API_URL}/api/v1/admin/webhooks/deliveries?${qs.toString()}`,
      { headers: { "X-Admin-Key": adminKey } },
    );

    const text = await resp.text();
    try {
      const data = JSON.parse(text);
      return NextResponse.json(data, { status: resp.status });
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
