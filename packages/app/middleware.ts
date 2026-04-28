import { getConfig } from "@thinkneverland/pixie-dust-config";
import { evaluateMiddleware } from "@thinkneverland/pixie-dust-core/middleware";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

function getClientIp(request: NextRequest): string {
  return (
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    request.headers.get("x-real-ip") ??
    "unknown"
  );
}

export function middleware(request: NextRequest) {
  const appConfig = getConfig();

  const result = evaluateMiddleware(
    {
      cookieName: appConfig.cookieName,
      // The interactive viewer at ``/view/{token}`` is public, but so are
      // the endpoints the client-side bundle hits once the page hydrates:
      // token validation, viewer config, page tiles, findings. If those
      // aren't explicitly public, a stale or invalid session cookie on an
      // iOS in-app browser trips the middleware and the fetch 401s — the
      // page then shows "Invalid or expired link" even though the token
      // is fine. Keep these patterns narrow: only the /public/ surfaces
      // that take a token as the authentication credential go in here.
      publicPaths: [
        "/view",
        "/api/waitlist",
        "/api/lintpdf/viewer/public",
        "/api/lintpdf/reports/tokens",
        // First-run Onboarding for the desktop and mobile apps —
        // resolves a tenant by name/slug/id/domain and returns the
        // branding blob to theme the app. Called before any user has
        // authenticated, so it must not require a session.
        "/api/public/tenant-lookup",
        // Universal links / App Links manifest files. iOS's CDN and
        // the Android Play Services verifier fetch these without any
        // session context. Auth would force a redirect they can't
        // follow, so the deep-link claim would silently fail.
        "/.well-known/apple-app-site-association",
        "/.well-known/assetlinks.json",
        // Machine-to-machine receiver fired by the LintPDF engine
        // when approval steps progress. Authenticated by HMAC-SHA256
        // against `LINTPDF_INTERNAL_WEBHOOK_SECRET`, not by a session
        // cookie — the engine has no cookie to send.
        "/api/internal/approval-webhook",
      ],
      rateLimitExemptPaths: [
        "/api/auth/magic-link/status",
        "/api/auth/claim-session",
        "/api/auth/mcp-backdoor",
        "/api/lintpdf",
        "/api/auth",
        "/api/trpc",
        "/api/waitlist",
        // Engine fan-out: a busy chain can fire dozens of step
        // events in quick succession during a multi-stakeholder
        // review. Rate-limiting here would drop legitimate push
        // notifications.
        "/api/internal/approval-webhook",
      ],
    },
    {
      pathname: request.nextUrl.pathname,
      sessionCookie: request.cookies.get(appConfig.cookieName)?.value,
      clientIp: getClientIp(request),
      url: request.url,
    },
  );

  if (result.redirect) {
    const response = NextResponse.redirect(result.redirect);
    for (const [key, value] of Object.entries(result.headers)) {
      response.headers.set(key, value);
    }
    return response;
  }

  if (result.error) {
    return NextResponse.json(result.error.body, {
      status: result.error.status,
      headers: result.headers,
    });
  }

  const response = NextResponse.next();
  for (const [key, value] of Object.entries(result.headers)) {
    response.headers.set(key, value);
  }

  // The Swagger UI pages load swagger-ui-bundle.js + swagger-ui.css
  // from cdn.jsdelivr.net. Pixie Dust's default CSP only allows
  // 'self' for script-src + style-src, so the bundle is blocked and
  // the page renders blank chrome. Override CSP for just those routes
  // so Swagger hydrates cleanly. Everything else keeps the strict
  // default.
  const path = request.nextUrl.pathname;
  if (
    path === "/dashboard/api-reference" ||
    path === "/dashboard/admin/api-reference" ||
    path === "/dashboard/admin/swagger"
  ) {
    response.headers.set(
      "Content-Security-Policy",
      [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "img-src 'self' data: https:",
        "font-src 'self' https://fonts.gstatic.com",
        "connect-src 'self' https://api.lintpdf.com",
        "frame-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ].join("; "),
    );
  }

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon\\.ico|favicon\\.png|favicon\\.svg|logo\\.png|logo\\.svg).*)",
  ],
};
