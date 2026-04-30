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
