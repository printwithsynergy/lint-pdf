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
import type { ViewerServices } from "../../core/plugin/services";

/**
 * Build the LintPDF SaaS-flavoured services for the given viewer
 * session. `apiBase` is the viewer-scoped path (e.g.,
 * `/api/lintpdf/viewer/{jobId}` or `/api/lintpdf/viewer/public/{token}`)
 * — same value `useViewerHost()` exposes today.
 */
export function createLintPDFViewerServices(args: {
  apiBase: string;
  jobApiBase: string;
}): ViewerServices {
  const { apiBase } = args;
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
    // Annotations / telemetry / i18n / tokens stay on the OSS no-op
    // defaults until subsequent PRs land their LintPDF impls.
    annotations: {
      list: async () => [],
      create: async (a) => a,
      update: async (_id, patch) => patch,
      remove: async () => {},
    },
    telemetry: noopTelemetry,
    i18n: noopI18n,
    tokens: defaultThemeTokens,
  };
}
