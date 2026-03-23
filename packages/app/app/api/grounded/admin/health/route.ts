export const dynamic = "force-dynamic";

import { env } from "@/lib/env";
import { NextResponse } from "next/server";

export async function GET() {
  const adminKey = env.LINTPDF_ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json(
      { error: "Admin API key not configured" },
      { status: 503 },
    );
  }

  const resp = await fetch(`${env.LINTPDF_API_URL}/api/v1/status`, {
    headers: { "X-Admin-Key": adminKey },
  });

  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
