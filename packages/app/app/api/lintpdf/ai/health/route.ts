export const dynamic = "force-dynamic";

import { NextResponse } from "next/server";

/**
 * AI health probe proxy — unauthenticated passthrough to the engine's
 * ``GET /api/v1/ai/health`` surface. Consumed by
 * ``components/ai/OutageBanner.tsx`` every 60s.
 *
 * The engine endpoint itself is ungated so the viewer (served from
 * third-party origins) can also poll it — this proxy just forwards
 * cache-bust headers and shields the app from a hardcoded base URL.
 */
export async function GET(): Promise<NextResponse> {
  const base =
    process.env.LINTPDF_API_URL || process.env.NEXT_PUBLIC_LINTPDF_API_URL || "";
  if (!base) {
    // No engine URL configured — fail open (status: ok) so the
    // banner never flips on misconfigured local dev.
    return NextResponse.json({ status: "ok" });
  }
  try {
    const upstream = await fetch(`${base.replace(/\/$/, "")}/api/v1/ai/health`, {
      cache: "no-store",
    });
    if (!upstream.ok) {
      return NextResponse.json({ status: "ok" });
    }
    const body = (await upstream.json()) as { status?: string };
    return NextResponse.json(
      { status: body.status === "degraded" ? "degraded" : "ok" },
      {
        headers: {
          "Cache-Control": "no-store, max-age=0",
        },
      },
    );
  } catch {
    return NextResponse.json({ status: "ok" });
  }
}
