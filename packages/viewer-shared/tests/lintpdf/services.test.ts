/**
 * createLintPDFViewerServices — Phase 2 services factory contract.
 *
 * Locks in the LintPDF URL formats so future refactors of the
 * factory don't silently change the wire shapes that the engine
 * expects. The components themselves are tested in tests/core/.
 */

import { describe, expect, it, vi } from "vitest";

import { createLintPDFViewerServices } from "../../src/lintpdf/sources/services";

describe("createLintPDFViewerServices", () => {
  const services = createLintPDFViewerServices({
    apiBase: "/api/lintpdf/viewer/job-1",
    jobApiBase: "/api/lintpdf/jobs/job-1",
  });

  describe("pageImages", () => {
    it("returns a synchronous tile URL with apiBase + pageNum + dpi", () => {
      const url = services.pageImages.getPageImageUrl({ pageNum: 5, dpi: 200 });
      expect(url).toBe("/api/lintpdf/viewer/job-1/pages/5/tile?dpi=200");
    });
  });

  describe("layers", () => {
    it("returns a synchronous layer-image URL", () => {
      const url = services.layers.getLayerImageUrl({
        pageNum: 3,
        layerIndex: 7,
        dpi: 150,
      });
      expect(url).toBe("/api/lintpdf/viewer/job-1/pages/3/layers/7?dpi=150");
    });

    it("listLayers fetches /layers and returns the layers array", async () => {
      const fakeLayers = [
        { name: "CutContour", ocg_index: 0, default_on: true },
        { name: "Artwork", ocg_index: 1, default_on: true },
      ];
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ layers: fakeLayers }), { status: 200 }),
        );
      const result = await services.layers.listLayers();
      expect(fetchSpy).toHaveBeenCalledWith("/api/lintpdf/viewer/job-1/layers");
      expect(result).toEqual(fakeLayers);
      fetchSpy.mockRestore();
    });

    it("listLayers throws when the response is not ok", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("nope", { status: 500 }));
      await expect(services.layers.listLayers()).rejects.toThrow(
        "Failed to load layers",
      );
      fetchSpy.mockRestore();
    });

    it("listLayers tolerates missing layers field (returns [])", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify({}), { status: 200 }),
        );
      const result = await services.layers.listLayers();
      expect(result).toEqual([]);
      fetchSpy.mockRestore();
    });
  });

  describe("separations", () => {
    it("returns a synchronous channel-image URL with percent-encoded channel name", () => {
      const url = services.separations.getChannelImageUrl({
        pageNum: 2,
        channelName: "Pantone Reflex Blue C",
        dpi: 150,
      });
      expect(url).toBe(
        "/api/lintpdf/viewer/job-1/pages/2/channel/Pantone%20Reflex%20Blue%20C?dpi=150",
      );
    });

    it("encodes process-ink channel names that don't need percent-encoding", () => {
      const url = services.separations.getChannelImageUrl({
        pageNum: 1,
        channelName: "Cyan",
        dpi: 150,
      });
      expect(url).toBe("/api/lintpdf/viewer/job-1/pages/1/channel/Cyan?dpi=150");
    });
  });

  describe("tacHeatmap", () => {
    it("returns a synchronous heatmap-image URL with dpi + tacLimit", () => {
      const url = services.tacHeatmap.getHeatmapImageUrl({
        pageNum: 4,
        dpi: 150,
        tacLimit: 280,
      });
      expect(url).toBe(
        "/api/lintpdf/viewer/job-1/pages/4/tac-heatmap?dpi=150&tac_limit=280",
      );
    });

    it("listRuns fetches /tac-heatmap/runs and returns the runs array", async () => {
      const fakeRuns = [
        { x0: 10, y0: 20, x1: 30, y1: 40, mean_tac: 250, limit: 300, exceeds: false },
        { x0: 50, y0: 60, x1: 70, y1: 80, mean_tac: 320, limit: 300, exceeds: true },
      ];
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ runs: fakeRuns }), { status: 200 }),
        );
      const result = await services.tacHeatmap.listRuns({
        pageNum: 2,
        dpi: 150,
        tacLimit: 300,
      });
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/lintpdf/viewer/job-1/pages/2/tac-heatmap/runs?dpi=150&tac_limit=300",
      );
      expect(result).toEqual(fakeRuns);
      fetchSpy.mockRestore();
    });

    it("listRuns returns [] (non-fatal) on non-2xx response", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("nope", { status: 500 }));
      const result = await services.tacHeatmap.listRuns({
        pageNum: 1,
        dpi: 150,
        tacLimit: 300,
      });
      expect(result).toEqual([]);
      fetchSpy.mockRestore();
    });

    it("listRuns returns [] (non-fatal) on network error", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockRejectedValueOnce(new TypeError("Failed to fetch"));
      const result = await services.tacHeatmap.listRuns({
        pageNum: 1,
        dpi: 150,
        tacLimit: 300,
      });
      expect(result).toEqual([]);
      fetchSpy.mockRestore();
    });

    it("listRuns tolerates a missing runs field (returns [])", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify({}), { status: 200 }),
        );
      const result = await services.tacHeatmap.listRuns({
        pageNum: 1,
        dpi: 150,
        tacLimit: 300,
      });
      expect(result).toEqual([]);
      fetchSpy.mockRestore();
    });
  });

  describe("annotations / telemetry / i18n / tokens", () => {
    it("annotations.list resolves to an empty array (no-op default)", async () => {
      expect(await services.annotations.list()).toEqual([]);
    });

    it("telemetry.track is a no-op (does not throw)", () => {
      expect(() =>
        services.telemetry.track("evt", { foo: "bar" }),
      ).not.toThrow();
    });

    it("i18n.t returns the key unchanged", () => {
      expect(services.i18n.t("foo.bar")).toBe("foo.bar");
    });

    it("tokens carries the default theme palette", () => {
      expect(services.tokens.primary).toBeTruthy();
      expect(services.tokens.bg).toBeTruthy();
    });
  });
});
