/**
 * Viewer proxy routes — forward page tile and info requests to the LintPDF engine.
 * Also includes public viewer routes (no auth) and view tracking.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

interface ViewerDb {
  reportView: {
    create: (args: Record<string, unknown>) => Promise<unknown>;
    findMany: (args: Record<string, unknown>) => Promise<unknown[]>;
  };
}

function engineUrl(path: string): string {
  const baseUrl = (
    process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com"
  ).replace(/\/$/, "");
  return `${baseUrl}${path}`;
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return headers;
}

/** Auth headers + a forwarded visitor-email so the engine can attribute
 *  annotation writes to the actual Next.js user, not the tenant's
 *  generic API-key owner. ``emailOverride`` wins when the app has a
 *  better signal than ``req.auth?.email`` (e.g. for tests). */
function authHeadersWithUserEmail(
  req: RouteRequest,
  emailOverride?: string,
): Record<string, string> {
  const headers = authHeaders();
  const email = emailOverride || req.auth?.email;
  if (email) {
    headers["X-Visitor-Email"] = email;
  }
  return headers;
}

function relayJson(resp: Response): Promise<RouteResponse> {
  return resp
    .text()
    .then(async (text) => {
      if (!resp.ok) {
        return { status: resp.status, body: text ? { error: text } : {} };
      }
      if (!text) return { status: resp.status, body: null };
      try {
        return { status: resp.status, body: JSON.parse(text) };
      } catch {
        return { status: resp.status, body: text };
      }
    });
}

/** Build the full auth + public proxy matrix for the engine's
 *  ``/api/v1/viewer/.../annotations(/.../comments)`` routes.
 *
 *  Kept in a helper so the routes block stays scannable — without
 *  this, the sheer number of proxy stubs (14 endpoints × two handler
 *  shapes) drowns out the rest of the viewer route declarations. */
function makeAnnotationProxies(): RouteDefinition[] {
  const routes: RouteDefinition[] = [];

  // Authenticated (dashboard) surface ----------------------------------
  routes.push(
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/annotations",
      auth: true,
      permission: "preflight:view",
      description: "List annotations for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/annotations`),
          { headers: authHeadersWithUserEmail(req) },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/:jobId/annotations",
      auth: true,
      permission: "preflight:view",
      description: "Create an annotation on a job page",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/annotations`),
          {
            method: "POST",
            headers: {
              ...authHeadersWithUserEmail(req),
              "Content-Type": "application/json",
            },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/viewer/:jobId/annotations/:annotationId",
      auth: true,
      permission: "preflight:view",
      description: "Update an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/annotations/${req.params.annotationId}`,
          ),
          {
            method: "PATCH",
            headers: {
              ...authHeadersWithUserEmail(req),
              "Content-Type": "application/json",
            },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "DELETE" as HttpMethod,
      path: "/viewer/:jobId/annotations/:annotationId",
      auth: true,
      permission: "preflight:view",
      description: "Delete an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/annotations/${req.params.annotationId}`,
          ),
          {
            method: "DELETE",
            headers: authHeadersWithUserEmail(req),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    // Comment threads on a single annotation
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/annotations/:annotationId/comments",
      auth: true,
      permission: "preflight:view",
      description: "List threaded comments on an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/annotations/${req.params.annotationId}/comments`,
          ),
          { headers: authHeadersWithUserEmail(req) },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/:jobId/annotations/:annotationId/comments",
      auth: true,
      permission: "preflight:view",
      description: "Post a comment on an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/annotations/${req.params.annotationId}/comments`,
          ),
          {
            method: "POST",
            headers: {
              ...authHeadersWithUserEmail(req),
              "Content-Type": "application/json",
            },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/viewer/:jobId/annotations/:annotationId/comments/:commentId",
      auth: true,
      permission: "preflight:view",
      description: "Edit a comment on an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/annotations/${req.params.annotationId}/comments/${req.params.commentId}`,
          ),
          {
            method: "PATCH",
            headers: {
              ...authHeadersWithUserEmail(req),
              "Content-Type": "application/json",
            },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "DELETE" as HttpMethod,
      path: "/viewer/:jobId/annotations/:annotationId/comments/:commentId",
      auth: true,
      permission: "preflight:view",
      description: "Delete a comment on an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/annotations/${req.params.annotationId}/comments/${req.params.commentId}`,
          ),
          {
            method: "DELETE",
            headers: authHeadersWithUserEmail(req),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
  );

  // Public share-link surface — forwards ``X-Visitor-Email`` verbatim
  // from the incoming request (the frontend email-gate modal sets it).
  const forwardVisitor = (req: RouteRequest): Record<string, string> => {
    const headers: Record<string, string> = {};
    const visitor =
      (req.headers?.["x-visitor-email"] as string | undefined) ||
      (req.headers?.["X-Visitor-Email"] as string | undefined);
    if (visitor) headers["X-Visitor-Email"] = visitor;
    return headers;
  };

  routes.push(
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/annotations",
      auth: false,
      description: "Public: list annotations on a share-link job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/public/${req.params.token}/annotations`),
          { headers: forwardVisitor(req) },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/public/:token/annotations",
      auth: false,
      description: "Public: create an annotation via a share-link token",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/public/${req.params.token}/annotations`),
          {
            method: "POST",
            headers: { ...forwardVisitor(req), "Content-Type": "application/json" },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/viewer/public/:token/annotations/:annotationId",
      auth: false,
      description: "Public: edit an annotation you authored",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/annotations/${req.params.annotationId}`,
          ),
          {
            method: "PATCH",
            headers: { ...forwardVisitor(req), "Content-Type": "application/json" },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "DELETE" as HttpMethod,
      path: "/viewer/public/:token/annotations/:annotationId",
      auth: false,
      description: "Public: delete an annotation you authored",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/annotations/${req.params.annotationId}`,
          ),
          { method: "DELETE", headers: forwardVisitor(req) },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/annotations/:annotationId/comments",
      auth: false,
      description: "Public: list comments on an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/annotations/${req.params.annotationId}/comments`,
          ),
          { headers: forwardVisitor(req) },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/public/:token/annotations/:annotationId/comments",
      auth: false,
      description: "Public: post a comment via a share-link token",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/annotations/${req.params.annotationId}/comments`,
          ),
          {
            method: "POST",
            headers: { ...forwardVisitor(req), "Content-Type": "application/json" },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/viewer/public/:token/annotations/:annotationId/comments/:commentId",
      auth: false,
      description: "Public: edit a comment you authored",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/annotations/${req.params.annotationId}/comments/${req.params.commentId}`,
          ),
          {
            method: "PATCH",
            headers: { ...forwardVisitor(req), "Content-Type": "application/json" },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
    {
      method: "DELETE" as HttpMethod,
      path: "/viewer/public/:token/annotations/:annotationId/comments/:commentId",
      auth: false,
      description: "Public: delete a comment you authored",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/annotations/${req.params.annotationId}/comments/${req.params.commentId}`,
          ),
          { method: "DELETE", headers: forwardVisitor(req) },
        );
        return relayJson(resp);
      }) as RouteHandler,
    },
  );

  return routes;
}

/**
 * Validate a report token by proxying to the engine's report token endpoint.
 * Returns job data on success, or null on failure.
 */
async function validateToken(
  token: string,
): Promise<{
  jobId: string;
  tenantId: string;
  fileName: string;
  emailRequired: boolean;
  brandName?: string;
  logoUrl?: string;
  anonymous: boolean;
} | null> {
  try {
    // The engine's ``/api/v1/reports/tokens/{token}`` endpoint is
    // token-authenticated (the token in the URL path is the credential) —
    // it does not require a tenant API key. Previously this call sent
    // ``authHeaders()`` (``Authorization: Bearer ${LINTPDF_API_KEY}``),
    // which introduced a silent failure mode: when the env var drifted
    // between deploys (or wasn't set at all on an edge instance), the
    // engine's auth middleware could reject the request, validateToken
    // returned null, the plugin handler 404'd, and the browser rendered
    // "Invalid or expired link" on a token that was perfectly valid.
    // Dropping the header removes that coupling entirely.
    const [tokenResp, configResp] = await Promise.all([
      fetch(engineUrl(`/api/v1/reports/tokens/${token}`)),
      fetch(engineUrl(`/api/v1/viewer/public/${token}/config`)).catch(() => null),
    ]);
    if (!tokenResp.ok) {
      // Surface the real reason in logs so the next "invalid link"
      // report can be debugged in 10 seconds instead of an hour of
      // curl-vs-browser divergence guessing.
      let body = "";
      try {
        body = (await tokenResp.text()).slice(0, 200);
      } catch {
        body = "(failed to read body)";
      }
      // eslint-disable-next-line no-console
      console.warn(
        `[fairy-ring] validateToken: engine token endpoint ${tokenResp.status} — ${body}`,
      );
      return null;
    }
    const data = await tokenResp.json() as Record<string, unknown>;
    let brandName: string | undefined;
    let logoUrl: string | undefined;
    let anonymous = false;
    if (configResp?.ok) {
      const cfg = await configResp.json() as Record<string, unknown>;
      anonymous = cfg.anonymous === true;
      // In anonymous mode the viewer strips all tenant/LintPDF chrome — the
      // share-page header must follow suit so brokers can forward links to
      // distributors without leaking their identity.
      brandName = anonymous ? undefined : ((cfg.brand_name as string) || undefined);
      logoUrl = anonymous ? undefined : ((cfg.brand_logo_url as string) || undefined);
    }
    return {
      jobId: (data.job_id ?? data.jobId) as string,
      tenantId: (data.tenant_id ?? data.tenantId ?? "") as string,
      fileName: anonymous
        ? "Preflight Report"
        : ((data.file_name ?? data.fileName ?? "Untitled") as string),
      emailRequired: (data.email_required ?? data.emailRequired ?? true) as boolean,
      brandName,
      logoUrl,
      anonymous,
    };
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn(
      `[fairy-ring] validateToken: threw for token ${token.slice(0, 8)}… — ${e instanceof Error ? e.message : String(e)}`,
    );
    return null;
  }
}

export function viewerRoutes(db?: ViewerDb): RouteDefinition[] {
  return [
    // ── Authenticated viewer proxy routes ──────────────────
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages",
      auth: true,
      permission: "preflight:view",
      description: "List all pages with dimensions for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/pages`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/tile",
      auth: true,
      permission: "preflight:view",
      description: "Get rendered page tile as PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/tile?dpi=${dpi}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: "Failed to render tile" } };
        }
        // Return raw image bytes
        const buffer = await resp.arrayBuffer();
        return {
          status: 200,
          body: Buffer.from(buffer),
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/info",
      auth: true,
      permission: "preflight:view",
      description: "Get page dimensions and box info",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/info`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    // --- Separation endpoints ---
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/separations",
      auth: true,
      permission: "preflight:view",
      description: "List ink channels (CMYK + spot colors)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/separations`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/channel/:channelName",
      auth: true,
      permission: "preflight:view",
      description: "Get a single separation channel as grayscale PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/channel/${encodeURIComponent(req.params.channelName)}?dpi=${dpi}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: "Failed to render channel" } };
        }
        const buffer = await resp.arrayBuffer();
        return {
          status: 200,
          body: Buffer.from(buffer),
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/interpretation",
      auth: true,
      permission: "preflight:view",
      description:
        "Get AI interpretation for a job (proxies to engine captains-log)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/captains-log/${req.params.jobId}/interpret`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/tac-heatmap",
      auth: true,
      permission: "preflight:view",
      description: "Get TAC heatmap overlay as RGBA PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const tacLimit = req.query.tac_limit ?? "300";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/tac-heatmap?dpi=${dpi}&tac_limit=${tacLimit}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: "Failed to render heatmap" } };
        }
        const buffer = await resp.arrayBuffer();
        return {
          status: 200,
          body: Buffer.from(buffer),
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/tac-heatmap/runs",
      auth: true,
      permission: "preflight:view",
      description: "TAC per-text-run metadata JSON for tooltip overlays",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const tacLimit = req.query.tac_limit ?? "300";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/tac-heatmap/runs?dpi=${dpi}&tac_limit=${tacLimit}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── Tile warming status ──────────────────────────────────
    //
    // The engine runs a background Celery task (lintpdf.viewer.warm_tiles)
    // after a job completes, pre-rendering every page tile into S3 so
    // the viewer opens without per-click cold renders. The viewer polls
    // this endpoint every ~1.5s to show a readiness progress badge.
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/tile-warming",
      auth: true,
      permission: "preflight:view",
      description: "Progress of the background tile pre-render task",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/tile-warming`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── Viewer annotations + comment threads (engine-backed) ──
    //
    // The engine owns ``viewer_annotations`` (reviewer markup) and
    // ``viewer_annotation_comments`` (threaded replies). We proxy the
    // CRUD surface through the plugin so the Next.js app can call
    // ``/api/lintpdf/viewer/{jobId}/annotations`` without cross-origin
    // auth gymnastics. For writes we forward the authenticated user's
    // email as ``X-Visitor-Email`` so the engine's audit-trail
    // attribution points at the actual human, not the tenant's
    // generic contact address. (The header name matches the one the
    // public share-link surface uses, which lets the engine handler
    // reuse the same email-gate code path.)
    ...makeAnnotationProxies(),

    // ── Check name registry ─────────────────────────────────
    {
      method: "GET" as HttpMethod,
      path: "/viewer/check-names",
      auth: true,
      permission: "preflight:view",
      description: "Get human-friendly check name registry",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl("/api/v1/check-names"), { headers: authHeaders() });
        if (!resp.ok) return { status: resp.status, body: {} };
        return {
          status: 200,
          body: await resp.json(),
          headers: { "Cache-Control": "public, max-age=86400" },
        } as RouteResponse;
      }) as RouteHandler,
    },

    // ── Viewer config ──────────────────────────────────────
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/config",
      auth: true,
      permission: "preflight:view",
      description: "Get resolved viewer configuration for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const brand = req.query.brand ? String(req.query.brand) : undefined;
        const qs = brand ? `?brand=${encodeURIComponent(brand)}` : "";
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/config${qs}`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── On-demand capability fill-in ───────────────────────
    // Used by the viewer when a tool (e.g. separations, TAC) has no data
    // because the job is ``minimal`` or an imported preflight didn't
    // cover it. Enqueues a single-analyzer Celery task.
    {
      method: "POST" as HttpMethod,
      path: "/viewer/:jobId/capabilities/:capability",
      auth: true,
      permission: "preflight:view",
      description: "Queue an on-demand analyzer run for a missing viewer capability",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/capabilities/${encodeURIComponent(req.params.capability)}`,
          ),
          {
            method: "POST",
            headers: authHeaders(),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: resp.status, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── Color picker (RGB sample) ────────────────────────
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/sample",
      auth: true,
      permission: "preflight:view",
      description: "Sample color at a point on a page",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const x = req.query.x ?? "0";
        const y = req.query.y ?? "0";
        const dpi = req.query.dpi ?? "300";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/sample?x=${x}&y=${y}&dpi=${dpi}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── Densitometer (per-channel CMYK + TAC readout) ────
    //
    // Distinct from the ``/sample`` color-picker above: this endpoint
    // shells out to Ghostscript tiffsep in the engine and returns
    // ``{channels: [{name, percent}], tac, limit_exceeded}``. The
    // engine route lives under the ``/densitometer`` suffix; we must
    // proxy by that exact path or the frontend gets a 404.
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/densitometer",
      auth: true,
      permission: "preflight:view",
      description: "Per-channel CMYK + spot ink densitometer sample",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const x = req.query.x ?? "0";
        const y = req.query.y ?? "0";
        const dpi = req.query.dpi ?? "300";
        const tacLimit = req.query.tac_limit ?? "300";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/densitometer?x=${x}&y=${y}&dpi=${dpi}&tac_limit=${tacLimit}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── PDF Layers (OCG) ─────────────────────────────────
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/layers",
      auth: true,
      permission: "preflight:view",
      description: "List PDF layers (Optional Content Groups)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/layers`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── Verdict ──────────────────────────────────────────
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/verdict",
      auth: true,
      permission: "preflight:view",
      description: "Get verdict for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/verdict`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/:jobId/verdict",
      auth: true,
      permission: "preflight:manage",
      description: "Set verdict for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/verdict`),
          {
            method: "POST",
            headers: { ...authHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify(req.body),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── File Comparison ──────────────────────────────────
    {
      method: "POST" as HttpMethod,
      path: "/viewer/compare",
      auth: true,
      permission: "preflight:view",
      description: "Create a file comparison between two jobs",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl("/api/v1/viewer/compare"),
          {
            method: "POST",
            headers: { ...authHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify(req.body),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/compare/:comparisonId/pages/:pageNum/diff",
      auth: true,
      permission: "preflight:view",
      description: "Get comparison diff image",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/compare/${req.params.comparisonId}/pages/${req.params.pageNum}/diff`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: "Diff not found" } };
        }
        const buffer = await resp.arrayBuffer();
        return {
          status: 200,
          body: Buffer.from(buffer),
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=3600",
          },
        } as RouteResponse;
      }) as RouteHandler,
    },

    // ── Public viewer routes (no auth) ─────────────────────

    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/job",
      auth: false,
      description: "Get job data for public viewing via report token",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tokenData = await validateToken(req.params.token);
        if (!tokenData) {
          return { status: 404, body: { error: "Invalid or expired token" } };
        }
        return {
          status: 200,
          body: {
            jobId: tokenData.jobId,
            tenantId: tokenData.tenantId,
            fileName: tokenData.fileName,
            emailRequired: tokenData.emailRequired,
            brandName: tokenData.brandName,
            logoUrl: tokenData.logoUrl,
            anonymous: tokenData.anonymous,
          },
        };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/public/:token/identify",
      auth: false,
      description: "Identify viewer for public report access and record view",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tokenData = await validateToken(req.params.token);
        if (!tokenData) {
          return { status: 404, body: { error: "Invalid or expired token" } };
        }

        const { email, name } = req.body as { email?: string; name?: string };
        if (tokenData.emailRequired && !email) {
          return { status: 400, body: { error: "Email is required" } };
        }

        // Record the view in Prisma
        if (db) {
          try {
            await db.reportView.create({
              data: {
                jobId: tokenData.jobId,
                tenantId: tokenData.tenantId,
                reportToken: req.params.token,
                viewerEmail: email ?? null,
                viewerName: name ?? null,
                ipAddress: req.headers?.["x-forwarded-for"] ?? req.headers?.["x-real-ip"] ?? null,
                userAgent: req.headers?.["user-agent"] ?? null,
              },
            });
          } catch {
            // Non-fatal — don't block viewer access if tracking fails
          }
        }

        return {
          status: 200,
          body: {
            success: true,
            jobId: tokenData.jobId,
          },
        };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/public/:token/share",
      auth: false,
      description: "Email the viewer link to one or more recipients",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/public/${req.params.token}/share`),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        const data = await resp.json().catch(() => ({ error: "Invalid response" }));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },

    // ── Public viewer proxy routes (token auth, read-only) ──
    //
    // These proxy directly to the engine's /api/v1/viewer/public/{token}/...
    // endpoints which validate the report token themselves — no tenant API
    // key or session needed.

    ...([
      { path: "/viewer/public/:token/pages", engine: (t: string) => `/api/v1/viewer/public/${t}/pages`, type: "json" as const },
      { path: "/viewer/public/:token/separations", engine: (t: string) => `/api/v1/viewer/public/${t}/separations`, type: "json" as const },
      { path: "/viewer/public/:token/config", engine: (t: string) => `/api/v1/viewer/public/${t}/config`, type: "json" as const },
      { path: "/viewer/public/:token/layers", engine: (t: string) => `/api/v1/viewer/public/${t}/layers`, type: "json" as const },
      { path: "/viewer/public/:token/verdict", engine: (t: string) => `/api/v1/viewer/public/${t}/verdict`, type: "json" as const },
      { path: "/viewer/public/:token/findings", engine: (t: string) => `/api/v1/reports/tokens/${t}/findings`, type: "json" as const },
      { path: "/viewer/public/:token/check-names", engine: () => "/api/v1/check-names", type: "json" as const },
    ]).map((r) => ({
      method: "GET" as HttpMethod,
      path: r.path,
      auth: false,
      description: `Public: ${r.path.split("/").pop()}`,
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl(r.engine(req.params.token)));
        if (!resp.ok) return { status: resp.status, body: { error: await resp.text() } };
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    })),

    // Page-level public endpoints (need pageNum, some return images)
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/pages/:pageNum/tile",
      auth: false,
      description: "Public: page tile PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const resp = await fetch(engineUrl(`/api/v1/viewer/public/${req.params.token}/pages/${req.params.pageNum}/tile?dpi=${dpi}`));
        if (!resp.ok) return { status: resp.status, body: { error: "Failed to render tile" } };
        const buffer = await resp.arrayBuffer();
        return { status: 200, body: Buffer.from(buffer), headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=86400" } } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/pages/:pageNum/info",
      auth: false,
      description: "Public: page info",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl(`/api/v1/viewer/public/${req.params.token}/pages/${req.params.pageNum}/info`));
        if (!resp.ok) return { status: resp.status, body: { error: await resp.text() } };
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/pages/:pageNum/channel/:channelName",
      auth: false,
      description: "Public: separation channel PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const resp = await fetch(engineUrl(`/api/v1/viewer/public/${req.params.token}/pages/${req.params.pageNum}/channel/${encodeURIComponent(req.params.channelName)}?dpi=${dpi}`));
        if (!resp.ok) return { status: resp.status, body: { error: "Failed to render channel" } };
        const buffer = await resp.arrayBuffer();
        return { status: 200, body: Buffer.from(buffer), headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=86400" } } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/pages/:pageNum/tac-heatmap",
      auth: false,
      description: "Public: TAC heatmap PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const tacLimit = req.query.tac_limit ?? "300";
        const resp = await fetch(engineUrl(`/api/v1/viewer/public/${req.params.token}/pages/${req.params.pageNum}/tac-heatmap?dpi=${dpi}&tac_limit=${tacLimit}`));
        if (!resp.ok) return { status: resp.status, body: { error: "Failed to render heatmap" } };
        const buffer = await resp.arrayBuffer();
        return { status: 200, body: Buffer.from(buffer), headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=86400" } } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/pages/:pageNum/sample",
      auth: false,
      description: "Public: color picker sample",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const { x = "0", y = "0", dpi = "300" } = req.query;
        const resp = await fetch(engineUrl(`/api/v1/viewer/public/${req.params.token}/pages/${req.params.pageNum}/sample?x=${x}&y=${y}&dpi=${dpi}`));
        if (!resp.ok) return { status: resp.status, body: { error: await resp.text() } };
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/pages/:pageNum/densitometer",
      auth: false,
      description: "Public: per-channel densitometer sample",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const { x = "0", y = "0", dpi = "300", tac_limit = "300" } = req.query;
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/pages/${req.params.pageNum}/densitometer?x=${x}&y=${y}&dpi=${dpi}&tac_limit=${tac_limit}`,
          ),
        );
        if (!resp.ok) return { status: resp.status, body: { error: await resp.text() } };
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/pages/:pageNum/tac-heatmap/runs",
      auth: false,
      description: "Public: TAC per-run metadata JSON for tooltip overlays",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const tacLimit = req.query.tac_limit ?? "300";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/public/${req.params.token}/pages/${req.params.pageNum}/tac-heatmap/runs?dpi=${dpi}&tac_limit=${tacLimit}`,
          ),
        );
        if (!resp.ok) return { status: resp.status, body: { error: await resp.text() } };
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/tile-warming",
      auth: false,
      description: "Public: tile pre-render progress for share-link viewers",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/public/${req.params.token}/tile-warming`),
        );
        if (!resp.ok) return { status: resp.status, body: { error: await resp.text() } };
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── View tracking routes (auth required) ───────────────

    {
      method: "POST" as HttpMethod,
      path: "/viewer/:jobId/track-view",
      auth: true,
      permission: "preflight:view",
      description: "Record an authenticated view of a job report",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        if (db) {
          try {
            await db.reportView.create({
              data: {
                jobId: req.params.jobId,
                tenantId,
                reportToken: "",
                viewerEmail: req.auth?.email ?? null,
                viewerName: (req.auth as Record<string, unknown>)?.name as string | null ?? null,
                ipAddress: req.headers?.["x-forwarded-for"] ?? req.headers?.["x-real-ip"] ?? null,
                userAgent: req.headers?.["user-agent"] ?? null,
              },
            });
          } catch {
            return { status: 500, body: { error: "Failed to record view" } };
          }
        }

        return { status: 200, body: { success: true } };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/views",
      auth: true,
      permission: "preflight:view",
      description: "List all views for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        if (!db) {
          return { status: 200, body: [] };
        }

        try {
          const views = await db.reportView.findMany({
            where: { jobId: req.params.jobId, tenantId },
            orderBy: { viewedAt: "desc" },
          });
          return { status: 200, body: views };
        } catch {
          return { status: 500, body: { error: "Failed to fetch views" } };
        }
      }) as RouteHandler,
    },
  ];
}
