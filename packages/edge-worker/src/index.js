/**
 * LintPDF edge Worker.
 *
 * Terminates customer traffic for branded subdomains under
 * ``*.custom.lintpdf.com`` and routes by path to the correct Railway
 * backend service:
 *
 *   /r/*         -> reports.lintpdf.com   (static reports, signed tokens)
 *   /api/v1/*    -> reports.lintpdf.com   (public viewer API, OpenAPI, etc.)
 *   /view/*      -> app.lintpdf.com       (interactive viewer, Next.js)
 *   /_next/*     -> app.lintpdf.com       (Next.js assets)
 *   /dashboard/* -> app.lintpdf.com       (admin + tenant dashboards)
 *   default      -> app.lintpdf.com       (landing / marketing)
 *
 * Why this exists: Railway's per-domain cert issuance (TLS-ALPN-01)
 * requires customer CNAMEs to point DIRECTLY at Railway's per-domain
 * target (e.g. ``xyz.up.railway.app``). That leaks Railway's brand
 * into every customer's DNS record. By routing through this Worker,
 * Cloudflare terminates TLS using the wildcard cert on
 * ``*.custom.lintpdf.com`` and forwards the request to Railway with
 * the service's registered host header, so Railway never sees the
 * customer-facing hostname. Customers get a single branded target
 * (``{slug}.custom.lintpdf.com``), zero Railway wait, one CNAME.
 *
 * The wildcard cert is provisioned by Cloudflare automatically when
 * the route binding is attached to the zone.
 *
 * Traffic flow:
 *
 *   customer         CF edge (this Worker)          Railway backend
 *   --------         ---------------------          ---------------
 *   reports.acme.com -> {slug}.custom.lintpdf.com -> reports.lintpdf.com
 *                       (path-routed proxy)           (Host: reports.lintpdf.com)
 *
 * Upstream Host header is rewritten to the backend service's known
 * hostname so Railway's edge-level routing treats the request as if
 * it came to the service directly. X-Forwarded-Host preserves the
 * original customer-facing hostname for engine-side logging /
 * telemetry / tenant lookup.
 */

const REPORTS_UPSTREAM = "reports.lintpdf.com";
const APP_UPSTREAM = "app.lintpdf.com";
// Railway's per-service backend hostnames. The Worker fetch uses
// these as the ACTUAL connection target (via cf.resolveOverride),
// while keeping the visible URL / TLS SNI on the *.lintpdf.com name.
// Needed because a plain fetch("https://app.lintpdf.com/") from a
// Worker goes through CF's own network fabric and fails with
// "Cannot assign requested address" (the fetch tries to open a
// socket to a CF IP for our own zone, which is forbidden).
const REPORTS_BACKEND = "e3fo0e01.up.railway.app";
const APP_BACKEND = "bwfl38nz.up.railway.app";

function pickRoute(pathname) {
  // Order matters: more-specific prefixes first. Returns both the
  // hostname visible to Railway (what goes into Host header + TLS SNI)
  // and the backend hostname we actually connect to via resolveOverride.
  if (pathname.startsWith("/r/")) return { upstream: REPORTS_UPSTREAM, backend: REPORTS_BACKEND };
  if (pathname.startsWith("/api/v1/")) return { upstream: REPORTS_UPSTREAM, backend: REPORTS_BACKEND };
  if (pathname.startsWith("/_next/")) return { upstream: APP_UPSTREAM, backend: APP_BACKEND };
  if (pathname.startsWith("/view/")) return { upstream: APP_UPSTREAM, backend: APP_BACKEND };
  if (pathname.startsWith("/dashboard/")) return { upstream: APP_UPSTREAM, backend: APP_BACKEND };
  if (pathname === "/favicon.ico" || pathname === "/robots.txt") {
    return { upstream: APP_UPSTREAM, backend: APP_BACKEND };
  }
  return { upstream: APP_UPSTREAM, backend: APP_BACKEND };
}

function buildUpstreamRequest(request, upstream, backend) {
  const incoming = new URL(request.url);
  // URL + TLS SNI + Host are all the upstream hostname (reports.lintpdf.com
  // or app.lintpdf.com). Railway's edge routes by Host header; Railway has
  // a valid cert for upstream; upstream matches SNI. Connection target is
  // overridden via cf.resolveOverride to the Railway backend hostname so
  // we bypass CF's own-zone DNS routing and hit Railway's Fastly edge
  // directly.
  const target = new URL(incoming.pathname + incoming.search, `https://${upstream}`);
  const req = new Request(target.toString(), {
    method: request.method,
    headers: new Headers(request.headers),
    body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    redirect: "manual",
    cf: {
      resolveOverride: backend,
    },
  });
  req.headers.set("Host", upstream);
  req.headers.set("X-Forwarded-Host", incoming.hostname);
  req.headers.set("X-Forwarded-Proto", "https");
  // Let CF's edge re-add the real client IP on the upstream request.
  req.headers.delete("CF-Connecting-IP");
  return req;
}

function rewriteCookieDomain(response, originalHost) {
  // If any Set-Cookie headers scope cookies to the upstream's domain
  // (lintpdf.com), rewrite the Domain attribute to the customer's
  // branded hostname so the cookie actually applies on their URL.
  const cookies = response.headers.getAll
    ? response.headers.getAll("Set-Cookie")
    : [response.headers.get("Set-Cookie")].filter(Boolean);
  if (!cookies.length) return response;

  const newHeaders = new Headers(response.headers);
  newHeaders.delete("Set-Cookie");
  for (const cookie of cookies) {
    // Strip any Domain= attribute; let the browser scope to the
    // current host. Prevents Domain=lintpdf.com cookies leaking
    // across customer URLs.
    const rewritten = cookie
      .split(";")
      .filter((part) => !/^\s*Domain\s*=/i.test(part))
      .join(";");
    newHeaders.append("Set-Cookie", rewritten);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Operational probes -- return immediately without touching the
    // backend so health checks don't double as a Railway ping.
    if (url.pathname === "/__edge/health") {
      return new Response(
        JSON.stringify({
          ok: true,
          host: url.hostname,
          path: url.pathname,
          upstream_probe: "edge only, not routed",
          build: env.BUILD_TAG || "unset",
        }),
        { headers: { "content-type": "application/json" } }
      );
    }

    const { upstream, backend } = pickRoute(url.pathname);
    const upstreamReq = buildUpstreamRequest(request, upstream, backend);

    let upstreamRes;
    try {
      upstreamRes = await fetch(upstreamReq);
    } catch (err) {
      return new Response(
        `LintPDF edge: upstream ${upstream} unreachable (${err.message})`,
        { status: 502, headers: { "content-type": "text/plain" } }
      );
    }

    // Strip / rewrite Set-Cookie Domain attributes.
    return rewriteCookieDomain(upstreamRes, url.hostname);
  },
};
