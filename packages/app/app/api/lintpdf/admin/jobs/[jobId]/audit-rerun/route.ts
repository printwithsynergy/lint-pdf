export const dynamic = "force-dynamic";

import { requireSuperAdmin } from "@/lib/admin-auth";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

/**
 * Admin-only proxy for `POST /api/v1/jobs/{id}/audit:rerun`.
 *
 * The engine path uses a `:rerun` colon segment (RFC 3986 allows
 * colons in path segments and FastAPI routes it fine); we keep the
 * app-side proxy on a plain `audit-rerun` path so Next's route
 * parser doesn't have to deal with the colon in a dynamic segment
 * and router groups line up with every other `/jobs/{id}/xxx` proxy.
 *
 * The engine endpoint scopes the job lookup to the caller's tenant
 * via the `get_current_tenant` dependency when called with a tenant
 * bearer token. For the admin path we forward the super-admin's
 * identity through a separate endpoint on the engine — but today
 * the engine endpoint is tenant-scoped only. To make this work for
 * ops, we mint a super-admin bearer via the existing
 * `LINTPDF_ADMIN_API_KEY`... except the audit:rerun endpoint uses
 * `get_current_tenant` (tenant auth), not admin-key auth.
 *
 * Simplest fix that doesn't change the engine route: call the
 * engine admin-key flow that already resolves a tenant's API key
 * given the job id, then post with that bearer. Deferred — for now
 * the proxy returns 501 Not Implemented with a clear message so
 * the admin UI surfaces the limitation rather than silently
 * succeeding.
 */
export async function POST(
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

  try {
    // Engine accepts admin-key auth on every /api/v1/admin/* route,
    // and the audit:rerun helper is safe to call with the admin
    // context: it only reads findings + Modal, writes verdicts to
    // the existing rows, no tenant-boundary violation. We forward
    // through the admin mirror endpoint on the engine.
    const resp = await fetch(
      `${env.LINTPDF_API_URL}/api/v1/admin/jobs/${encodeURIComponent(jobId)}/audit-rerun`,
      {
        method: "POST",
        headers: { "X-Admin-Key": adminKey },
      },
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
