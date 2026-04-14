export const dynamic = "force-dynamic";

import { requireSuperAdmin } from "@/lib/admin-auth";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const denied = await requireSuperAdmin(req);
  if (denied) return denied;

  const adminKey = env.LINTPDF_ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json(
      { error: "Admin API key not configured" },
      { status: 503 },
    );
  }

  const { jobId } = await params;
  const url = `${env.LINTPDF_API_URL}/api/v1/admin/tile-warming/jobs/${encodeURIComponent(
    jobId,
  )}`;

  try {
    const resp = await fetch(url, {
      headers: { "X-Admin-Key": adminKey },
      cache: "no-store",
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
