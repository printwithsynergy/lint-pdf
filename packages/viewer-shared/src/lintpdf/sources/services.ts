/**
 * LintPDF concrete `ViewerServices` implementation.
 *
 * Phase 2 abstraction stage 3: `core/components/` consume host data
 * through `services.X.Y(...)` instead of building URLs from a raw
 * `apiBase` string. This factory returns the LintPDF-specific
 * `ViewerServices` that `PdfViewer.tsx` mounts on the
 * `ViewerServicesContext` provider.
 *
 * Subsequent PRs expand `ViewerServices` to also cover layers,
 * separations, tac-heatmap, color sampling, densitometer reads,
 * annotations, and report exports — at which point this file grows
 * the corresponding methods. Today only `pageImages` is wired (used
 * by PageCanvas + PageNavigator in this PR).
 */

import {
  defaultThemeTokens,
  noopI18n,
  noopTelemetry,
} from "../../core/plugin/services";
import type {
  AnnotationEntry,
  ViewerServices,
} from "../../core/plugin/services";
import type { ColorSample, DensitometerSample } from "../../core/types";

/**
 * Build the LintPDF SaaS-flavoured services for the given viewer
 * session. `apiBase` is the viewer-scoped path (e.g.,
 * `/api/lintpdf/viewer/{jobId}` or `/api/lintpdf/viewer/public/{token}`)
 * — same value `useViewerHost()` exposes today. `jobId` lets the
 * annotations endpoints (which sit at `/api/lintpdf/annotations/{jobId}`,
 * not under `/viewer/`) build their base URL without
 * apiBase.replace() acrobatics in every call site.
 */
export function createLintPDFViewerServices(args: {
  apiBase: string;
  jobApiBase: string;
  jobId: string;
}): ViewerServices {
  const { apiBase, jobId } = args;
  // Annotations live at /api/lintpdf/annotations/{jobId} regardless of
  // whether the viewer is in authenticated or public-token mode. The
  // existing components recovered this URL by stripping /viewer/...
  // off apiBase; the factory does that once instead.
  const annotationsBase = apiBase.replace(
    /\/viewer\/.*$/,
    `/annotations/${jobId}`,
  );
  // Reports live at /api/lintpdf/reports/{jobId} — same shape as
  // annotations, different sub-path.
  const reportsBase = apiBase.replace(
    /\/viewer\/.*$/,
    `/reports/${jobId}`,
  );
  return {
    pageImages: {
      getPageImageUrl: ({ pageNum, dpi }) =>
        `${apiBase}/pages/${pageNum}/tile?dpi=${dpi}`,
    },
    layers: {
      getLayerImageUrl: ({ pageNum, layerIndex, dpi }) =>
        `${apiBase}/pages/${pageNum}/layers/${layerIndex}?dpi=${dpi}`,
      listLayers: async () => {
        const resp = await fetch(`${apiBase}/layers`);
        if (!resp.ok) {
          throw new Error("Failed to load layers");
        }
        const data = (await resp.json()) as {
          layers?: ReadonlyArray<{
            name: string;
            ocg_index: number;
            default_on: boolean;
          }>;
        };
        return data.layers ?? [];
      },
    },
    separations: {
      getChannelImageUrl: ({ pageNum, channelName, dpi }) =>
        `${apiBase}/pages/${pageNum}/channel/${encodeURIComponent(channelName)}?dpi=${dpi}`,
    },
    colorSample: {
      sampleAt: async ({ pageNum, pdfX, pdfY, dpi = 300 }) => {
        try {
          const resp = await fetch(
            `${apiBase}/pages/${pageNum}/sample?x=${pdfX.toFixed(1)}&y=${pdfY.toFixed(1)}&dpi=${dpi}`,
          );
          if (!resp.ok) return null;
          return (await resp.json()) as ColorSample;
        } catch {
          return null;
        }
      },
    },
    densitometer: {
      sampleAt: async ({ pageNum, pdfX, pdfY, dpi = 300, tacLimit }) => {
        let resp: Response;
        try {
          resp = await fetch(
            `${apiBase}/pages/${pageNum}/densitometer` +
              `?x=${pdfX.toFixed(1)}&y=${pdfY.toFixed(1)}&dpi=${dpi}&tac_limit=${tacLimit}`,
          );
        } catch {
          throw new Error("Network error");
        }
        if (resp.ok) {
          return (await resp.json()) as DensitometerSample;
        }
        if (resp.status === 422) {
          const body = await resp
            .json()
            .catch(() => ({ detail: "No separations" }));
          throw new Error(
            (body as { detail?: string }).detail ??
              "No separations available for this page.",
          );
        }
        throw new Error(`Sampling failed (${resp.status})`);
      },
    },
    tacHeatmap: {
      getHeatmapImageUrl: ({ pageNum, dpi, tacLimit }) =>
        `${apiBase}/pages/${pageNum}/tac-heatmap?dpi=${dpi}&tac_limit=${tacLimit}`,
      listRuns: async ({ pageNum, dpi, tacLimit }) => {
        // Non-fatal failures: TACHeatmapOverlay's hover layer just stays
        // empty, the heatmap PNG itself still renders. Returning [] on
        // any error preserves that behaviour through the service shape.
        try {
          const resp = await fetch(
            `${apiBase}/pages/${pageNum}/tac-heatmap/runs?dpi=${dpi}&tac_limit=${tacLimit}`,
          );
          if (!resp.ok) return [];
          const data = (await resp.json()) as {
            runs?: ReadonlyArray<{
              x0: number;
              y0: number;
              x1: number;
              y1: number;
              mean_tac: number;
              limit: number;
              exceeds: boolean;
            }>;
          };
          return Array.isArray(data.runs) ? data.runs : [];
        } catch {
          return [];
        }
      },
    },
    annotations: {
      list: async () => {
        try {
          const resp = await fetch(annotationsBase);
          if (!resp.ok) return [];
          const data = (await resp.json()) as ReadonlyArray<unknown>;
          return Array.isArray(data) ? (data as ReadonlyArray<AnnotationEntry>) : [];
        } catch {
          return [];
        }
      },
      getForPage: async (pageNum) => {
        try {
          const resp = await fetch(`${annotationsBase}/${pageNum}`);
          if (!resp.ok) return null;
          const data = (await resp.json()) as ReadonlyArray<AnnotationEntry>;
          return Array.isArray(data) && data.length > 0 ? (data[0] ?? null) : null;
        } catch {
          return null;
        }
      },
      saveForPage: async (pageNum, fabricJson) => {
        // Best-effort — autosave on a flaky connection should not crash
        // the canvas. The user is still drawing locally; the next save
        // will pick up the snapshot.
        try {
          await fetch(`${annotationsBase}/${pageNum}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fabricJson }),
          });
        } catch {
          /* swallow */
        }
      },
      remove: async (id) => {
        try {
          await fetch(`${annotationsBase}/${id}`, { method: "DELETE" });
        } catch {
          /* swallow */
        }
      },
    },
    reports: {
      getHtmlReportUrl: () => `${reportsBase}/html`,
      getPdfDownloadUrl: () => `${reportsBase}/download`,
    },
    telemetry: noopTelemetry,
    i18n: noopI18n,
    tokens: defaultThemeTokens,
  };
}
