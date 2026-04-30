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
    jobId: "job-1",
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

  describe("colorSample", () => {
    it("sampleAt returns the parsed JSON on 2xx", async () => {
      const fake = { x: 100, y: 200, rgb: [255, 0, 0], hex: "#ff0000", tac: 100 };
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify(fake), { status: 200 }),
        );
      const result = await services.colorSample.sampleAt({
        pageNum: 1,
        pdfX: 100.456,
        pdfY: 200.123,
      });
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/lintpdf/viewer/job-1/pages/1/sample?x=100.5&y=200.1&dpi=300",
      );
      expect(result).toEqual(fake);
      fetchSpy.mockRestore();
    });

    it("sampleAt honors a custom dpi when provided", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("{}", { status: 200 }));
      await services.colorSample.sampleAt({
        pageNum: 1,
        pdfX: 0,
        pdfY: 0,
        dpi: 150,
      });
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/lintpdf/viewer/job-1/pages/1/sample?x=0.0&y=0.0&dpi=150",
      );
      fetchSpy.mockRestore();
    });

    it("sampleAt returns null on non-2xx (silent swallow)", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("nope", { status: 500 }));
      const result = await services.colorSample.sampleAt({
        pageNum: 1,
        pdfX: 0,
        pdfY: 0,
      });
      expect(result).toBeNull();
      fetchSpy.mockRestore();
    });

    it("sampleAt returns null on network error", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockRejectedValueOnce(new TypeError("fail"));
      const result = await services.colorSample.sampleAt({
        pageNum: 1,
        pdfX: 0,
        pdfY: 0,
      });
      expect(result).toBeNull();
      fetchSpy.mockRestore();
    });
  });

  describe("densitometer", () => {
    it("sampleAt returns the parsed JSON on 2xx", async () => {
      const fake = {
        x: 100,
        y: 200,
        dpi: 300,
        channels: [{ name: "Cyan", percent: 50 }],
        tac: 50,
        tac_limit: 300,
        limit_exceeded: false,
      };
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify(fake), { status: 200 }),
        );
      const result = await services.densitometer.sampleAt({
        pageNum: 1,
        pdfX: 100.456,
        pdfY: 200.123,
        tacLimit: 300,
      });
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/lintpdf/viewer/job-1/pages/1/densitometer?x=100.5&y=200.1&dpi=300&tac_limit=300",
      );
      expect(result).toEqual(fake);
      fetchSpy.mockRestore();
    });

    it("sampleAt throws the engine's detail on 422", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ detail: "Custom: no CMYK" }), {
            status: 422,
          }),
        );
      await expect(
        services.densitometer.sampleAt({
          pageNum: 1,
          pdfX: 0,
          pdfY: 0,
          tacLimit: 300,
        }),
      ).rejects.toThrow("Custom: no CMYK");
      fetchSpy.mockRestore();
    });

    it("sampleAt falls back to friendly message when 422 body lacks detail", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("not json", { status: 422 }));
      await expect(
        services.densitometer.sampleAt({
          pageNum: 1,
          pdfX: 0,
          pdfY: 0,
          tacLimit: 300,
        }),
      ).rejects.toThrow("No separations");
      fetchSpy.mockRestore();
    });

    it("sampleAt throws 'Sampling failed (NNN)' on other non-2xx", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("err", { status: 503 }));
      await expect(
        services.densitometer.sampleAt({
          pageNum: 1,
          pdfX: 0,
          pdfY: 0,
          tacLimit: 300,
        }),
      ).rejects.toThrow("Sampling failed (503)");
      fetchSpy.mockRestore();
    });

    it("sampleAt throws 'Network error' on fetch rejection", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockRejectedValueOnce(new TypeError("nope"));
      await expect(
        services.densitometer.sampleAt({
          pageNum: 1,
          pdfX: 0,
          pdfY: 0,
          tacLimit: 300,
        }),
      ).rejects.toThrow("Network error");
      fetchSpy.mockRestore();
    });
  });

  describe("annotations", () => {
    const ANNO_BASE = "/api/lintpdf/annotations/job-1";

    it("list fetches the annotations base URL and returns the JSON array", async () => {
      const fake = [
        {
          id: "a1",
          jobId: "job-1",
          pageNum: 1,
          authorEmail: "a@b.com",
          authorName: null,
          createdAt: "2026-04-30",
          updatedAt: "2026-04-30",
        },
      ];
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify(fake), { status: 200 }),
        );
      const result = await services.annotations.list();
      expect(fetchSpy).toHaveBeenCalledWith(ANNO_BASE);
      expect(result).toEqual(fake);
      fetchSpy.mockRestore();
    });

    it("list returns [] on non-2xx (silent swallow)", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("nope", { status: 500 }));
      expect(await services.annotations.list()).toEqual([]);
      fetchSpy.mockRestore();
    });

    it("list returns [] on network error", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockRejectedValueOnce(new TypeError("fail"));
      expect(await services.annotations.list()).toEqual([]);
      fetchSpy.mockRestore();
    });

    it("getForPage returns the first entry from the per-page response", async () => {
      const fake = [
        {
          id: "a1",
          jobId: "job-1",
          pageNum: 3,
          authorEmail: "a@b.com",
          authorName: null,
          createdAt: "2026-04-30",
          updatedAt: "2026-04-30",
          fabricJson: { version: "6.0.0" },
        },
      ];
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify(fake), { status: 200 }),
        );
      const result = await services.annotations.getForPage(3);
      expect(fetchSpy).toHaveBeenCalledWith(`${ANNO_BASE}/3`);
      expect(result?.id).toBe("a1");
      fetchSpy.mockRestore();
    });

    it("getForPage returns null when the response array is empty", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("[]", { status: 200 }));
      expect(await services.annotations.getForPage(3)).toBeNull();
      fetchSpy.mockRestore();
    });

    it("getForPage returns null on non-2xx (silent swallow)", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("nope", { status: 500 }));
      expect(await services.annotations.getForPage(3)).toBeNull();
      fetchSpy.mockRestore();
    });

    it("saveForPage POSTs the fabricJson to /annotations/{job}/{page}", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response("ok", { status: 200 }));
      await services.annotations.saveForPage(7, { foo: "bar" });
      expect(fetchSpy).toHaveBeenCalledWith(`${ANNO_BASE}/7`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fabricJson: { foo: "bar" } }),
      });
      fetchSpy.mockRestore();
    });

    it("saveForPage swallows network errors (best-effort autosave)", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockRejectedValueOnce(new TypeError("fail"));
      // Should not throw.
      await services.annotations.saveForPage(1, {});
      fetchSpy.mockRestore();
    });

    it("remove DELETEs /annotations/{job}/{annotationId}", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(new Response(null, { status: 204 }));
      await services.annotations.remove("a1");
      expect(fetchSpy).toHaveBeenCalledWith(`${ANNO_BASE}/a1`, {
        method: "DELETE",
      });
      fetchSpy.mockRestore();
    });
  });

  describe("reports", () => {
    it("getHtmlReportUrl points at /api/lintpdf/reports/{jobId}/html", () => {
      expect(services.reports.getHtmlReportUrl()).toBe(
        "/api/lintpdf/reports/job-1/html",
      );
    });

    it("getPdfDownloadUrl points at /api/lintpdf/reports/{jobId}/download", () => {
      expect(services.reports.getPdfDownloadUrl()).toBe(
        "/api/lintpdf/reports/job-1/download",
      );
    });
  });

  describe("telemetry / i18n / tokens", () => {
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
