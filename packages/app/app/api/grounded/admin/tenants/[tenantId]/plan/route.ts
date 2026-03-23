export const dynamic = "force-dynamic";

import { env } from "@/lib/env";
import { NextResponse } from "next/server";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ tenantId: string }> },
) {
  const adminKey = env.GROUNDED_ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json(
      { error: "Admin API key not configured" },
      { status: 503 },
    );
  }

  const { tenantId } = await params;
  const body = await req.json();

  const resp = await fetch(
    `${env.GROUNDED_API_URL}/api/v1/admin/tenants/${tenantId}/plan`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Key": adminKey,
      },
      body: JSON.stringify(body),
    },
  );

  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
