/**
 * Annotation routes — CRUD for Fabric.js markup annotations stored in Prisma.
 *
 * Annotations live in the Next.js app database (not the engine).
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

interface AnnotationRecord {
  id: string;
  jobId: string;
  tenantId: string;
  pageNum: number;
  authorId: string | null;
  authorEmail: string;
  authorName: string | null;
  fabricJson: unknown;
  createdAt: Date;
  updatedAt: Date;
}

interface AnnotationDb {
  annotation: {
    findMany: (args: Record<string, unknown>) => Promise<AnnotationRecord[]>;
    findFirst: (args: Record<string, unknown>) => Promise<AnnotationRecord | null>;
    create: (args: Record<string, unknown>) => Promise<AnnotationRecord>;
    update: (args: Record<string, unknown>) => Promise<AnnotationRecord>;
    delete: (args: Record<string, unknown>) => Promise<unknown>;
  };
}

export function annotationRoutes(db: AnnotationDb): RouteDefinition[] {
  return [
    // ── List all annotations for a job ────────────────────────
    {
      method: "GET" as HttpMethod,
      path: "/annotations/:jobId",
      auth: true,
      permission: "preflight:view",
      description: "List all annotations for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        const annotations = await db.annotation.findMany({
          where: { jobId: req.params.jobId, tenantId },
          orderBy: [{ pageNum: "asc" }, { createdAt: "asc" }],
        });

        return { status: 200, body: annotations };
      }) as RouteHandler,
    },

    // ── Get annotations for a specific page ───────────────────
    {
      method: "GET" as HttpMethod,
      path: "/annotations/:jobId/:pageNum",
      auth: true,
      permission: "preflight:view",
      description: "Get annotations for a specific page",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        const pageNum = parseInt(req.params.pageNum, 10);
        if (isNaN(pageNum)) {
          return { status: 400, body: { error: "Invalid page number" } };
        }

        const annotations = await db.annotation.findMany({
          where: { jobId: req.params.jobId, tenantId, pageNum },
          orderBy: { createdAt: "asc" },
        });

        return { status: 200, body: annotations };
      }) as RouteHandler,
    },

    // ── Create / update annotation for a page ─────────────────
    {
      method: "POST" as HttpMethod,
      path: "/annotations/:jobId/:pageNum",
      auth: true,
      permission: "annotation:create",
      description: "Create or update an annotation for a page",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        const pageNum = parseInt(req.params.pageNum, 10);
        if (isNaN(pageNum)) {
          return { status: 400, body: { error: "Invalid page number" } };
        }

        const { fabricJson } = req.body as { fabricJson?: unknown };
        if (!fabricJson) {
          return { status: 400, body: { error: "fabricJson is required" } };
        }

        const authorEmail = req.auth?.email ?? "unknown";
        const authorId = req.auth?.userId ?? null;
        const authorName = req.auth?.name ?? null;

        // Upsert: check if this author already has an annotation on this page
        const existing = await db.annotation.findFirst({
          where: {
            jobId: req.params.jobId,
            tenantId,
            pageNum,
            authorEmail,
          },
        });

        if (existing) {
          const updated = await db.annotation.update({
            where: { id: existing.id },
            data: { fabricJson },
          });
          return { status: 200, body: updated };
        }

        const annotation = await db.annotation.create({
          data: {
            jobId: req.params.jobId,
            tenantId,
            pageNum,
            authorId,
            authorEmail,
            authorName,
            fabricJson,
          },
        });

        return { status: 201, body: annotation };
      }) as RouteHandler,
    },

    // ── Delete an annotation ──────────────────────────────────
    {
      method: "DELETE" as HttpMethod,
      path: "/annotations/:jobId/:annotationId",
      auth: true,
      permission: "annotation:create",
      description: "Delete an annotation",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        const existing = await db.annotation.findFirst({
          where: {
            id: req.params.annotationId,
            jobId: req.params.jobId,
            tenantId,
          },
        });

        if (!existing) {
          return { status: 404, body: { error: "Annotation not found" } };
        }

        await db.annotation.delete({
          where: { id: req.params.annotationId },
        });

        return { status: 204 };
      }) as RouteHandler,
    },
  ];
}
