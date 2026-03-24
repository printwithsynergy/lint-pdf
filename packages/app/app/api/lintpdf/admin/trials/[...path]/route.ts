export const dynamic = "force-dynamic";

import { requireSuperAdmin } from "@/lib/admin-auth";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

/**
 * Catch-all proxy for trial admin endpoints.
 * Forwards GET/POST/PATCH to the engine at /api/v1/admin/trials/<path>.
 */
async function proxy(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> },
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

  const { path } = await params;
  const subPath = path.join("/");
  const url = `${env.LINTPDF_API_URL}/api/v1/admin/trials/${subPath}`;

  try {
    const headers: Record<string, string> = { "X-Admin-Key": adminKey };

    const fetchOpts: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method === "POST" || req.method === "PATCH") {
      const contentType = req.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        headers["Content-Type"] = "application/json";
        fetchOpts.body = await req.text();
      }
    }

    const resp = await fetch(url, fetchOpts);
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

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
