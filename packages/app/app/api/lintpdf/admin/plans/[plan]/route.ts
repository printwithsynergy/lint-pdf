export const dynamic = "force-dynamic";

import { requireSuperAdmin } from "@/lib/admin-auth";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

/**
 * Per-plan CRUD proxy for `/api/v1/admin/plans/{plan}`.
 *
 * - GET:    fetch a single plan's baseline + overrides + effective view.
 * - PATCH:  merge `{overrides: {...}}` into the plan's DB row.
 * - DELETE: drop all DB overrides for this plan (revert to code baseline).
 *
 * All three go through the engine admin surface; we just carry the
 * super-admin cookie → engine `X-Admin-Key` header hop.
 */
async function forward(
  req: Request,
  plan: string,
  method: "GET" | "PATCH" | "DELETE",
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
      `${env.LINTPDF_API_URL}/api/v1/admin/plans/${encodeURIComponent(plan)}`,
      init,
    );
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

export function GET(
  req: Request,
  { params }: { params: Promise<{ plan: string }> },
) {
  return params.then(({ plan }) => forward(req, plan, "GET"));
}

export function PATCH(
  req: Request,
  { params }: { params: Promise<{ plan: string }> },
) {
  return params.then(({ plan }) => forward(req, plan, "PATCH"));
}

export function DELETE(
  req: Request,
  { params }: { params: Promise<{ plan: string }> },
) {
  return params.then(({ plan }) => forward(req, plan, "DELETE"));
}
