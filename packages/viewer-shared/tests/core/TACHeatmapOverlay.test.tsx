/**
 * TACHeatmapOverlay — Q7-A snapshot backfill.
 *
 * Renders a Total-Area-Coverage heatmap PNG over the page canvas
 * plus an SVG hover layer showing per-text-run TAC readings.
 * Loading-state snapshot + service URL/listRuns plumbing.
 */

import { describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";

import { TACHeatmapOverlay } from "../../src/core/components/TACHeatmapOverlay";
import { makeStubServices, withServices } from "../_helpers/services";

const baseProps = {
  jobId: "job-1",
  pageNum: 1,
  width: 612,
  height: 792,
  pageWidthPts: 612,
  pageHeightPts: 792,
};

describe("TACHeatmapOverlay", () => {
  it("renders the loading state on first render (heatmap PNG hasn't loaded yet)", () => {
    const services = makeStubServices();
    const { container } = render(
      withServices(<TACHeatmapOverlay {...baseProps} />, services),
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("calls services.tacHeatmap.getHeatmapImageUrl with default dpi=150 + tacLimit=300", () => {
    const getHeatmapImageUrl = vi.fn(() => "blob:test");
    const services = makeStubServices({
      tacHeatmap: { getHeatmapImageUrl, listRuns: async () => [] },
    });
    render(withServices(<TACHeatmapOverlay {...baseProps} />, services));
    expect(getHeatmapImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      dpi: 150,
      tacLimit: 300,
    });
  });

  it("honors custom dpi + tacLimit", () => {
    const getHeatmapImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      tacHeatmap: { getHeatmapImageUrl, listRuns: async () => [] },
    });
    render(
      withServices(
        <TACHeatmapOverlay {...baseProps} dpi={300} tacLimit={280} />,
        services,
      ),
    );
    expect(getHeatmapImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      dpi: 300,
      tacLimit: 280,
    });
  });

  it("calls services.tacHeatmap.listRuns to fetch hover-tooltip data", async () => {
    const listRuns = vi.fn(async () => []);
    const services = makeStubServices({
      tacHeatmap: { getHeatmapImageUrl: () => "", listRuns },
    });
    render(withServices(<TACHeatmapOverlay {...baseProps} />, services));
    await waitFor(() =>
      expect(listRuns).toHaveBeenCalledWith({
        pageNum: 1,
        dpi: 150,
        tacLimit: 300,
      }),
    );
  });

  it("does not crash when listRuns returns []", async () => {
    const services = makeStubServices({
      tacHeatmap: {
        getHeatmapImageUrl: () => "",
        listRuns: async () => [],
      },
    });
    expect(() =>
      render(withServices(<TACHeatmapOverlay {...baseProps} />, services)),
    ).not.toThrow();
  });

  it("re-fetches when pageNum changes", () => {
    const getHeatmapImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      tacHeatmap: { getHeatmapImageUrl, listRuns: async () => [] },
    });
    const { rerender } = render(
      withServices(<TACHeatmapOverlay {...baseProps} />, services),
    );
    expect(getHeatmapImageUrl).toHaveBeenCalledWith(
      expect.objectContaining({ pageNum: 1 }),
    );
    rerender(
      withServices(<TACHeatmapOverlay {...baseProps} pageNum={3} />, services),
    );
    expect(getHeatmapImageUrl).toHaveBeenCalledWith(
      expect.objectContaining({ pageNum: 3 }),
    );
  });
});
