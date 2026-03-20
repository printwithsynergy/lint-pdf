export const dynamic = "force-dynamic";

import { ensureRegistry } from "@/lib/plugins";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const registry = await ensureRegistry();
  const route = registry
    .getRoutes()
    .find((r) => r.method === "POST" && r.fullPath === "/api/stripe/webhooks");

  if (!route) {
    return NextResponse.json(
      { error: "Stripe webhook handler not registered" },
      { status: 404 },
    );
  }

  const body = await req.text();
  const result = await route.handler({
    method: "POST",
    path: "/api/stripe/webhooks",
    headers: Object.fromEntries(req.headers.entries()),
    params: {},
    query: {},
    body: body ? JSON.parse(body) : undefined,
  });

  return NextResponse.json(result.body ?? null, {
    status: result.status,
    headers: result.headers,
  });
}
