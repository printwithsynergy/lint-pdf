export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { env } from "@/lib/env";
import { NextResponse } from "next/server";

/**
 * POST /api/lintpdf/submit — proxy file upload to engine.
 * Forwards the multipart form data directly to the engine's POST /api/v1/jobs.
 */
export async function POST(req: Request) {
  // Authenticate
  const cookieHeader = req.headers.get("cookie");
  const session = await authenticateRequest(prisma, cookieHeader);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const apiKey = env.LINTPDF_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: "Engine API key not configured" },
      { status: 503 },
    );
  }

  try {
    // Forward the raw request body (multipart/form-data) to the engine
    const contentType = req.headers.get("content-type") ?? "";
    const body = await req.arrayBuffer();

    const resp = await fetch(`${env.LINTPDF_API_URL}/api/v1/jobs`, {
      method: "POST",
      headers: {
        "Content-Type": contentType,
        Authorization: `Bearer ${apiKey}`,
      },
      body,
    });

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
