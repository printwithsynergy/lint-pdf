export const dynamic = "force-dynamic";

import { ensureRegistry } from "@/lib/plugins";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const registry = await ensureRegistry();
  const route = registry
    .getRoutes()
    .find((r) => r.method === "POST" && r.fullPath === "/api/lintpdf/webhooks");

  if (!route) {
    return NextResponse.json(
      { error: "Webhook handler not registered" },
      { status: 404 },
    );
  }

  const body = await req.text();
  let parsedBody: unknown;
  if (body) {
    try {
      parsedBody = JSON.parse(body);
    } catch {
      return NextResponse.json({ error: "Malformed JSON body" }, { status: 400 });
    }
  }
  const result = await route.handler({
    method: "POST",
    path: "/api/lintpdf/webhooks",
    headers: Object.fromEntries(req.headers.entries()),
    params: {},
    query: {},
    body: parsedBody,
  });

  return NextResponse.json(result.body ?? null, {
    status: result.status,
    headers: result.headers,
  });
}
