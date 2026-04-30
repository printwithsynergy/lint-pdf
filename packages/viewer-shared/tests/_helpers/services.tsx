/**
 * Shared test fixture: a no-op ViewerServices factory + provider
 * wrapper used by the snapshot-backfill suite. Each component test
 * passes only the methods it cares about; the rest stay no-op so
 * unrelated services can't accidentally affect behavior.
 */

import type React from "react";

import { ViewerServicesContext } from "../../src/core/host";
import type { ViewerServices } from "../../src/core/plugin/services";
import {
  defaultThemeTokens,
  noopI18n,
  noopTelemetry,
} from "../../src/core/plugin/services";

/**
 * Build a complete `ViewerServices` from a partial-tree override.
 * Methods not supplied default to the safest no-op:
 *  - URL builders → ""
 *  - listLayers / listRuns → []
 *  - colorSample.sampleAt → null
 *  - densitometer.sampleAt → throws "no separations"
 *  - annotations CRUD → no-op / empty list
 */
export function makeStubServices(
  overrides: Partial<{
    [K in keyof ViewerServices]: Partial<ViewerServices[K]>;
  }> = {},
): ViewerServices {
  return {
    pageImages: { getPageImageUrl: () => "", ...(overrides.pageImages ?? {}) },
    layers: {
      getLayerImageUrl: () => "",
      listLayers: async () => [],
      ...(overrides.layers ?? {}),
    },
    separations: {
      getChannelImageUrl: () => "",
      ...(overrides.separations ?? {}),
    },
    tacHeatmap: {
      getHeatmapImageUrl: () => "",
      listRuns: async () => [],
      ...(overrides.tacHeatmap ?? {}),
    },
    colorSample: {
      sampleAt: async () => null,
      ...(overrides.colorSample ?? {}),
    },
    densitometer: {
      sampleAt: async () => {
        throw new Error("No separations available for this page.");
      },
      ...(overrides.densitometer ?? {}),
    },
    annotations: {
      list: async () => [],
      getForPage: async () => null,
      saveForPage: async () => {},
      remove: async () => {},
      ...(overrides.annotations ?? {}),
    },
    reports: {
      getHtmlReportUrl: () => "",
      getPdfDownloadUrl: () => "",
      ...(overrides.reports ?? {}),
    },
    telemetry: noopTelemetry,
    i18n: noopI18n,
    tokens: defaultThemeTokens,
  } as ViewerServices;
}

/** Wrap a render tree with a ViewerServicesContext provider. */
export function withServices(
  ui: React.ReactNode,
  services: ViewerServices,
): React.ReactElement {
  return (
    <ViewerServicesContext.Provider value={services}>
      {ui}
    </ViewerServicesContext.Provider>
  );
}
