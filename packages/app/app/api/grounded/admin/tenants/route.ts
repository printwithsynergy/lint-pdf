export const dynamic = "force-dynamic";

import { env } from "@/lib/env";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const adminKey = env.GROUNDED_ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json(
      { error: "Admin API key not configured" },
      { status: 503 },
    );
  }

  const { searchParams } = new URL(req.url);
  const page = searchParams.get("page") ?? "1";
  const pageSize = searchParams.get("page_size") ?? "50";

  try {
    const resp = await fetch(
      `${env.GROUNDED_API_URL}/api/v1/admin/tenants?page=${page}&page_size=${pageSize}`,
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
