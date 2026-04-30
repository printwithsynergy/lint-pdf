/**
 * LayerPanel — Q7-A snapshot backfill.
 *
 * Reads layers via services.layers.listLayers() (PR #339) and
 * renders a checkbox per layer + an All On / All Off pair. Tests
 * cover loading state, empty state, populated state, and the
 * onToggleLayer / onSetAllLayers wiring.
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, waitFor } from "@testing-library/react";

import { LayerPanel } from "../../src/core/components/LayerPanel";
import { ViewerServicesContext } from "../../src/core/host";
import type { ViewerServices } from "../../src/core/plugin/services";
import {
  defaultThemeTokens,
  noopI18n,
  noopTelemetry,
} from "../../src/core/plugin/services";
import type { LayerInfo } from "../../src/core/types";

const stubServices = (
  listLayers: () => Promise<ReadonlyArray<LayerInfo>>,
): ViewerServices => ({
  pageImages: { getPageImageUrl: () => "" },
  layers: { getLayerImageUrl: () => "", listLayers },
  separations: { getChannelImageUrl: () => "" },
  tacHeatmap: { getHeatmapImageUrl: () => "", listRuns: async () => [] },
  colorSample: { sampleAt: async () => null },
  densitometer: {
    sampleAt: async () => {
      throw new Error("no separations");
    },
  },
  annotations: {
    list: async () => [],
    getForPage: async () => null,
    saveForPage: async () => {},
    remove: async () => {},
  },
  reports: { getHtmlReportUrl: () => "", getPdfDownloadUrl: () => "" },
  telemetry: noopTelemetry,
  i18n: noopI18n,
  tokens: defaultThemeTokens,
});

const wrap = (ui: React.ReactNode, services: ViewerServices) => (
  <ViewerServicesContext.Provider value={services}>
    {ui}
  </ViewerServicesContext.Provider>
);

const baseProps = {
  jobId: "job-1",
  enabledLayers: new Set<number>(),
  onToggleLayer: () => {},
  onSetAllLayers: () => {},
};

describe("LayerPanel", () => {
  it("renders the loading state on first render", () => {
    const services = stubServices(() => new Promise(() => {})); // never resolves
    const { container } = render(wrap(<LayerPanel {...baseProps} />, services));
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders the empty-state placeholder when listLayers returns []", async () => {
    const services = stubServices(async () => []);
    const { container, findByText } = render(
      wrap(<LayerPanel {...baseProps} />, services),
    );
    await findByText(/no optional content layers/i);
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders one row per layer with checkbox + name", async () => {
    const services = stubServices(async () => [
      { name: "CutContour", ocg_index: 0, default_on: true },
      { name: "Artwork", ocg_index: 1, default_on: true },
    ]);
    const enabled = new Set<number>([0]);
    const { container, findByText } = render(
      wrap(
        <LayerPanel {...baseProps} enabledLayers={enabled} />,
        services,
      ),
    );
    await findByText("CutContour");
    expect(container.firstChild).toMatchSnapshot();
  });

  it("calls onToggleLayer with the OCG index when a checkbox is clicked", async () => {
    const onToggleLayer = vi.fn();
    const services = stubServices(async () => [
      { name: "Artwork", ocg_index: 1, default_on: true },
    ]);
    const { findByText } = render(
      wrap(
        <LayerPanel {...baseProps} onToggleLayer={onToggleLayer} />,
        services,
      ),
    );
    const label = await findByText("Artwork");
    fireEvent.click(label.previousSibling as HTMLInputElement);
    expect(onToggleLayer).toHaveBeenCalledWith(1);
  });

  it("calls onSetAllLayers(true) when All On is clicked", async () => {
    const onSetAllLayers = vi.fn();
    const services = stubServices(async () => [
      { name: "Artwork", ocg_index: 1, default_on: true },
    ]);
    const { findByText } = render(
      wrap(
        <LayerPanel {...baseProps} onSetAllLayers={onSetAllLayers} />,
        services,
      ),
    );
    fireEvent.click(await findByText("All On"));
    expect(onSetAllLayers).toHaveBeenCalledWith(true);
  });

  it("renders an error state when listLayers throws", async () => {
    const services = stubServices(async () => {
      throw new Error("Failed to load layers");
    });
    const { findByText } = render(wrap(<LayerPanel {...baseProps} />, services));
    await waitFor(() =>
      expect(findByText("Failed to load layers")).resolves.toBeTruthy(),
    );
  });
});
