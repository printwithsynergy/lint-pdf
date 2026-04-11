export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { getCookieName } from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { ensureRegistry } from "@/lib/plugins";
import { NextResponse } from "next/server";

/**
 * Catch-all route handler that dispatches /api/lintpdf/* requests
 * to the plugin registry. Handles authentication and route matching.
 */

type RouteRegistryEntry = {
  method: string;
  fullPath: string;
  path: string;
  auth?: boolean;
  permission?: string;
  handler: (req: {
    method: string;
    path: string;
    headers: Record<string, string>;
    params: Record<string, string>;
    query: Record<string, string>;
    body?: unknown;
    auth?: {
      userId: string;
      tenantId: string;
      role: string;
      isSuperAdmin: boolean;
    };
  }) => Promise<{
    status: number;
    body?: unknown;
    headers?: Record<string, string>;
  }>;
};

/**
 * Match a request path against a route pattern (e.g. /jobs/:jobId).
 * Returns extracted params or null if no match.
 */
function matchPath(
  pattern: string,
  requestPath: string,
): Record<string, string> | null {
  const patternParts = pattern.split("/").filter(Boolean);
  const requestParts = requestPath.split("/").filter(Boolean);

  if (patternParts.length !== requestParts.length) return null;

  const params: Record<string, string> = {};
  for (let i = 0; i < patternParts.length; i++) {
    const patternPart = patternParts[i]!;
    const requestPart = requestParts[i]!;
    if (patternPart.startsWith(":")) {
      params[patternPart.slice(1)] = requestPart;
    } else if (patternPart !== requestPart) {
      return null;
    }
  }
  return params;
}

async function handleRequest(
  req: Request,
  { params: routeParams }: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const { path: pathSegments } = await routeParams;
  const requestPath = `/api/lintpdf/${pathSegments.join("/")}`;
  const method = req.method;

  const registry = await ensureRegistry();
  const routes = registry.getRoutes() as unknown as RouteRegistryEntry[];

  // Find matching route
  let matchedRoute: RouteRegistryEntry | null = null;
  let matchedParams: Record<string, string> = {};

  for (const route of routes) {
    if (route.method !== method) continue;
    const params = matchPath(route.fullPath, requestPath);
    if (params) {
      matchedRoute = route;
      matchedParams = params;
      break;
    }
  }

  if (!matchedRoute) {
    return NextResponse.json(
      { error: "Route not found", path: requestPath, method },
      { status: 404 },
    );
  }

  // Authenticate if route requires it
  let auth:
    | {
        userId: string;
        tenantId: string;
        role: string;
        isSuperAdmin: boolean;
      }
    | undefined;

  if (matchedRoute.auth) {
    const cookieHeader = req.headers.get("cookie");
    const session = await authenticateRequest(prisma, cookieHeader);

    if (!session) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Check for super admin status first (needed for impersonation + tenant-less access)
    const user = await prisma.user.findUnique({
      where: { id: session.userId },
      select: { isSuperAdmin: true },
    });

    // Get user's tenant membership
    const tenantUser = await prisma.tenantUser.findFirst({
      where: { userId: session.userId },
      include: { tenant: true },
      orderBy: { joinedAt: "asc" },
    });

    // Super admins may not have a tenant membership — check impersonation first
    let tenantId = tenantUser?.tenantId ?? "";
    let role = tenantUser?.role ?? "OWNER";

    if (user?.isSuperAdmin) {
      const cookieName = getCookieName();
      const cookies =
        cookieHeader?.split(";").map((c: string) => c.trim()) ?? [];
      const sessionToken = cookies
        .find((c: string) => c.startsWith(`${cookieName}=`))
        ?.split("=")[1];
      if (sessionToken) {
        const dbSession = await prisma.session.findUnique({
          where: { token: sessionToken },
          select: { impersonatingTenantId: true },
        });
        if (dbSession?.impersonatingTenantId) {
          tenantId = dbSession.impersonatingTenantId;
        }
      }
    }

    // Non-super-admin users must have a tenant membership
    if (!tenantUser && !user?.isSuperAdmin) {
      return NextResponse.json(
        { error: "No tenant membership found" },
        { status: 403 },
      );
    }

    auth = {
      userId: session.userId,
      tenantId,
      role,
      isSuperAdmin: user?.isSuperAdmin ?? false,
    };
  }

  // Parse request body for non-GET requests
  let body: unknown;
  if (method !== "GET" && method !== "HEAD") {
    const text = await req.text();
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        return NextResponse.json(
          { error: "Malformed JSON body" },
          { status: 400 },
        );
      }
    }
  }

  // Build query params
  const { searchParams } = new URL(req.url);
  const query: Record<string, string> = {};
  searchParams.forEach((value, key) => {
    query[key] = value;
  });

  // Dispatch to plugin handler
  try {
    const result = await matchedRoute.handler({
      method,
      path: requestPath,
      headers: Object.fromEntries(req.headers.entries()),
      params: matchedParams,
      query,
      body,
      auth,
    });

    if (result.status === 204) {
      return new NextResponse(null, { status: 204, headers: result.headers });
    }

    // Binary responses (Buffer/Uint8Array) must be sent as raw bytes,
    // not JSON-serialized. Detect by checking the body type or the
    // Content-Type header from the handler.
    if (Buffer.isBuffer(result.body) || result.body instanceof Uint8Array) {
      return new NextResponse(result.body, {
        status: result.status,
        headers: result.headers,
      });
    }

    return NextResponse.json(result.body ?? null, {
      status: result.status,
      headers: result.headers,
    });
  } catch (e) {
    console.error("Plugin route error:", requestPath, e);
    return NextResponse.json(
      {
        error: "Internal server error",
        detail: e instanceof Error ? e.message : String(e),
      },
      { status: 500 },
    );
  }
}

export const GET = handleRequest;
export const POST = handleRequest;
export const PUT = handleRequest;
export const PATCH = handleRequest;
export const DELETE = handleRequest;
