import { test, expect } from "@playwright/test";
import {
  getEngineApiKey,
  getEngineBase,
  pollJobViaEngine,
} from "../helpers";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const TEST_PDF = resolve(
  __dirname,
  "../../../engine/tests/fixtures/test-sample.pdf",
);

const VIEWER_ENDPOINTS = [
  "pages",
  "separations",
] as const;

test.describe("Preflight: Viewer Integration", () => {
  let engineApiKey: string;
  let engineBase: string;
  let jobId: string;

  test.beforeAll(async ({ request }) => {
    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();

    test.skip(!engineApiKey, "Engine API key not available");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    // Submit a job directly to the engine and wait for completion
    const pdfBuffer = readFileSync(TEST_PDF);
    const submitRes = await request.post(`${engineBase}/api/v1/jobs`, {
      headers: { Authorization: `Bearer ${engineApiKey}` },
      multipart: {
        file: {
          name: "test-sample.pdf",
          mimeType: "application/pdf",
          buffer: pdfBuffer,
        },
        profile_id: "lintpdf-default",
      },
    });

    expect(
      [200, 201, 202].includes(submitRes.status()),
      `Engine submit failed: ${submitRes.status()} ${await submitRes.text()}`,
    ).toBe(true);

    const submitData = await submitRes.json();
    jobId = submitData.job_id ?? submitData.id;
    expect(jobId, "No job ID returned from engine").toBeTruthy();

    const result = await pollJobViaEngine(
      request,
      jobId,
      engineApiKey,
      120_000,
    );
    test.skip(
      result.status !== "complete",
      `Job did not complete successfully: ${result.status}`,
    );
  });

  test.describe("Page list", () => {
    test("GET /api/v1/viewer/jobs/{id}/pages returns page list", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok(), `Pages endpoint failed: ${res.status()}`).toBe(true);
      const data = await res.json();
      const pages = Array.isArray(data) ? data : data.pages;
      expect(Array.isArray(pages)).toBe(true);
      expect(pages.length).toBeGreaterThan(0);

      for (const page of pages) {
        // Each page should have a page number and dimensions
        expect(page.page_num ?? page.page_number ?? page.index).toBeDefined();
        if (page.width !== undefined) {
          expect(typeof page.width).toBe("number");
          expect(page.width).toBeGreaterThan(0);
        }
        if (page.height !== undefined) {
          expect(typeof page.height).toBe("number");
          expect(page.height).toBeGreaterThan(0);
        }
      }
    });
  });

  test.describe("Tile rendering", () => {
    test("GET /api/v1/viewer/jobs/{id}/pages/1/tile returns image data", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/tile`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok(), `Tile endpoint failed: ${res.status()}`).toBe(true);
      const contentType = res.headers()["content-type"] ?? "";
      expect(
        contentType.includes("image/png") || contentType.includes("image/jpeg"),
        `Expected image content-type, got: ${contentType}`,
      ).toBe(true);

      const body = await res.body();
      expect(body.length).toBeGreaterThan(100); // Non-trivial image data
    });

    test("GET /api/v1/viewer/jobs/{id}/pages/1/tile?dpi=72 returns lower DPI tile", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/tile?dpi=72`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok(), `Low-DPI tile failed: ${res.status()}`).toBe(true);
      const contentType = res.headers()["content-type"] ?? "";
      expect(
        contentType.includes("image/png") || contentType.includes("image/jpeg"),
        `Expected image content-type, got: ${contentType}`,
      ).toBe(true);

      const body = await res.body();
      expect(body.length).toBeGreaterThan(0);
    });
  });

  test.describe("Page info", () => {
    test("GET /api/v1/viewer/jobs/{id}/pages/1/info returns page metadata", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/info`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok(), `Page info failed: ${res.status()}`).toBe(true);
      const info = await res.json();

      // Page info should contain dimensional data
      expect(info).toBeTruthy();
      if (info.width !== undefined) {
        expect(typeof info.width).toBe("number");
        expect(info.width).toBeGreaterThan(0);
      }
      if (info.height !== undefined) {
        expect(typeof info.height).toBe("number");
        expect(info.height).toBeGreaterThan(0);
      }
      // Media box and trim box may be present
      if (info.media_box ?? info.mediaBox) {
        const mediaBox = info.media_box ?? info.mediaBox;
        expect(Array.isArray(mediaBox)).toBe(true);
        expect(mediaBox.length).toBe(4);
      }
      if (info.trim_box ?? info.trimBox) {
        const trimBox = info.trim_box ?? info.trimBox;
        expect(Array.isArray(trimBox)).toBe(true);
        expect(trimBox.length).toBe(4);
      }
    });
  });

  test.describe("Separations", () => {
    test("GET /api/v1/viewer/jobs/{id}/separations returns channel list", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/separations`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok(), `Separations failed: ${res.status()}`).toBe(true);
      const data = await res.json();
      const channels = Array.isArray(data) ? data : data.channels ?? data.separations;
      expect(Array.isArray(channels)).toBe(true);

      // CMYK should be present for most PDFs
      const channelNames = channels.map(
        (c: Record<string, unknown>) =>
          ((c.name ?? c.channel ?? c) as string).toString().toLowerCase(),
      );
      const cmyk = ["cyan", "magenta", "yellow", "black"];
      for (const color of cmyk) {
        expect(
          channelNames.some((n: string) => n.includes(color)),
          `Expected channel "${color}" in separations`,
        ).toBe(true);
      }
    });

    test("GET /api/v1/viewer/jobs/{id}/pages/1/channel/cyan returns channel image", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/channel/cyan`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok(), `Cyan channel failed: ${res.status()}`).toBe(true);
      const contentType = res.headers()["content-type"] ?? "";
      expect(
        contentType.includes("image/png") || contentType.includes("image/jpeg"),
        `Expected image content-type for channel, got: ${contentType}`,
      ).toBe(true);

      const body = await res.body();
      expect(body.length).toBeGreaterThan(0);
    });
  });

  test.describe("TAC heatmap", () => {
    test("GET /api/v1/viewer/jobs/{id}/pages/1/tac-heatmap returns overlay", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/tac-heatmap`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok(), `TAC heatmap failed: ${res.status()}`).toBe(true);
      const contentType = res.headers()["content-type"] ?? "";
      expect(
        contentType.includes("image/png") || contentType.includes("image/jpeg"),
        `Expected image content-type for TAC heatmap, got: ${contentType}`,
      ).toBe(true);

      const body = await res.body();
      expect(body.length).toBeGreaterThan(0);
    });
  });

  test.describe("Error handling", () => {
    test("GET /api/v1/viewer/jobs/{id}/pages/999/tile returns 404 for non-existent page", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/999/tile`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok()).toBe(false);
      expect(
        [404, 400, 422].includes(res.status()),
        `Expected 404 for invalid page, got ${res.status()}`,
      ).toBe(true);
    });

    test("all viewer endpoints return 401 without auth", async ({
      request,
    }) => {
      const endpoints = [
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages`,
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/tile`,
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/info`,
        `${engineBase}/api/v1/viewer/jobs/${jobId}/separations`,
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/channel/cyan`,
        `${engineBase}/api/v1/viewer/jobs/${jobId}/pages/1/tac-heatmap`,
      ];

      for (const endpoint of endpoints) {
        const res = await request.get(endpoint, {
          headers: { Authorization: "" },
        });
        expect(res.ok()).toBe(false);
        expect(
          [401, 403].includes(res.status()),
          `Expected 401/403 for ${endpoint}, got ${res.status()}`,
        ).toBe(true);
      }
    });

    test("all viewer endpoints return 404 for non-existent job", async ({
      request,
    }) => {
      const fakeJobId = "nonexistent-job-id-000";
      const endpoints = [
        `${engineBase}/api/v1/viewer/jobs/${fakeJobId}/pages`,
        `${engineBase}/api/v1/viewer/jobs/${fakeJobId}/pages/1/tile`,
        `${engineBase}/api/v1/viewer/jobs/${fakeJobId}/pages/1/info`,
        `${engineBase}/api/v1/viewer/jobs/${fakeJobId}/separations`,
        `${engineBase}/api/v1/viewer/jobs/${fakeJobId}/pages/1/channel/cyan`,
        `${engineBase}/api/v1/viewer/jobs/${fakeJobId}/pages/1/tac-heatmap`,
      ];

      for (const endpoint of endpoints) {
        const res = await request.get(endpoint, {
          headers: { Authorization: `Bearer ${engineApiKey}` },
        });
        expect(res.ok()).toBe(false);
        expect(
          [404, 400].includes(res.status()),
          `Expected 404 for non-existent job at ${endpoint}, got ${res.status()}`,
        ).toBe(true);
      }
    });
  });
});
