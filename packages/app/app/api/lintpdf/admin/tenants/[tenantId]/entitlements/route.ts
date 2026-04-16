export const dynamic = "force-dynamic";

import { requireSuperAdmin } from "@/lib/admin-auth";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

async function forward(
  req: Request,
  tenantId: string,
  method: "PATCH" | "DELETE" | "GET",
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

  const init: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
    },
  };
  if (method === "PATCH") {
    const body = await req.json();
    init.body = JSON.stringify(body);
  }

  try {
    const resp = await fetch(
      `${env.LINTPDF_API_URL}/api/v1/admin/tenants/${tenantId}/entitlements`,
      init,
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

export async function GET(
  req: Request,
  { params }: { params: Promise<{ tenantId: string }> },
) {
  const { tenantId } = await params;
  return forward(req, tenantId, "GET");
}

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ tenantId: string }> },
) {
  const { tenantId } = await params;
  return forward(req, tenantId, "PATCH");
}

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ tenantId: string }> },
) {
  const { tenantId } = await params;
  return forward(req, tenantId, "DELETE");
}
