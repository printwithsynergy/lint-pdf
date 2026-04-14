/**
 * UI coverage for the viewer tile-warming hooks + progress badge.
 *
 * These tests intercept the engine endpoints via ``page.route`` rather
 * than standing up a real preflight pipeline — the goal is to verify
 * the client-side behaviour of ``useTileWarmingStatus`` +
 * ``useTilePrefetch`` + the badge rendered by ``PdfViewer``.
 *
 * The viewer is mounted via the public share-link path
 * ``/view/:token`` so no auth is required; every request the page
 * makes to ``/api/lintpdf/viewer/public/…`` is fulfilled locally.
 */

import { test, expect } from "@playwright/test";
import type { Page, Route } from "@playwright/test";

const TOKEN = "tile-warming-test-token";

interface RouteStub {
  url: string | RegExp;
  fulfill: (route: Route) => Promise<void> | void;
}

async function installStubs(page: Page, stubs: RouteStub[]): Promise<void> {
  for (const stub of stubs) {
    await page.route(stub.url, async (route) => {
      await stub.fulfill(route);
    });
  }
}

function jsonFulfill<T>(body: T, status = 200): (route: Route) => Promise<void> {
  return async (route) => {
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  };
}

function baseStubs(opts: {
  pages: number;
  anonymous?: boolean;
  annotations?: Array<{ id: string; page_num: number; kind: string }>;
}): RouteStub[] {
  const pageList = Array.from({ length: opts.pages }, (_, i) => ({
    num: i + 1,
    width_pts: 612,
    height_pts: 792,
  }));

  return [
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/job`,
      fulfill: jsonFulfill({
        jobId: "job-abc",
        tenantId: "tenant-abc",
        fileName: "sample.pdf",
        emailRequired: false,
        anonymous: opts.anonymous ?? true,
      }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/config`,
      fulfill: jsonFulfill({
        anonymous: opts.anonymous ?? true,
        allow_annotations: false,
        capabilities: {},
      }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/pages`,
      fulfill: jsonFulfill({ pages: pageList }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/findings`,
      fulfill: jsonFulfill({ findings: [] }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/approval-chain`,
      fulfill: async (route) =>
        route.fulfill({ status: 404, body: "" }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/annotations`,
      fulfill: jsonFulfill({ annotations: opts.annotations ?? [] }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/separations`,
      fulfill: jsonFulfill({ channels: [] }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/layers`,
      fulfill: jsonFulfill({ layers: [] }),
    },
    {
      url: `**/api/lintpdf/viewer/public/${TOKEN}/identify`,
      fulfill: async (route) =>
        route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
    },
  ];
}

async function stubTile(page: Page, capture?: string[]): Promise<void> {
  // A 1x1 PNG is plenty for prefetch assertions — the prefetcher only
  // cares about status + the fact that bytes were fetched.
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
    "base64",
  );
  await page.route(
    `**/api/lintpdf/viewer/public/${TOKEN}/pages/*/tile**`,
    async (route) => {
      if (capture) capture.push(route.request().url());
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        headers: { "Cache-Control": "public, max-age=86400" },
        body: png,
      });
    },
  );
}

test.describe("Viewer tile warming UI", () => {
  test("in-progress warming shows the preparing-pages badge", async ({
    page,
  }) => {
    await installStubs(page, baseStubs({ pages: 6 }));
    await stubTile(page);

    // Warming reports 3 / 6 pages rendered so the badge should read
    // "Preparing pages 3 / 6...".
    await page.route(
      `**/api/lintpdf/viewer/public/${TOKEN}/tile-warming`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-abc",
            status: "in_progress",
            rendered: 3,
            total: 6,
            dpi: 150,
            percent: 50,
          }),
        });
      },
    );

    await page.goto(`/view/${TOKEN}`);

    const badge = page.getByText(/Preparing pages 3 \/ 6/i);
    await expect(badge).toBeVisible({ timeout: 10_000 });
  });

  test("tile-warming is polled approximately every 1.5 s", async ({
    page,
  }) => {
    await installStubs(page, baseStubs({ pages: 4 }));
    await stubTile(page);

    const pollTimes: number[] = [];
    await page.route(
      `**/api/lintpdf/viewer/public/${TOKEN}/tile-warming`,
      async (route) => {
        pollTimes.push(Date.now());
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-abc",
            status: "in_progress",
            rendered: 1,
            total: 4,
            dpi: 150,
            percent: 25,
          }),
        });
      },
    );

    await page.goto(`/view/${TOKEN}`);
    // Wait long enough to see at least two polls (first + next tick).
    await page.waitForTimeout(3_500);

    expect(pollTimes.length).toBeGreaterThanOrEqual(2);
    const gap = pollTimes[1]! - pollTimes[0]!;
    // Polling interval is 1500 ms. Allow a generous window for CI jitter.
    expect(gap).toBeGreaterThan(800);
    expect(gap).toBeLessThan(3_000);
  });

  test("warming complete hides the badge and kicks off prefetch", async ({
    page,
  }) => {
    await installStubs(page, baseStubs({ pages: 3 }));
    const tileUrls: string[] = [];
    await stubTile(page, tileUrls);

    await page.route(
      `**/api/lintpdf/viewer/public/${TOKEN}/tile-warming`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-abc",
            status: "complete",
            rendered: 3,
            total: 3,
            dpi: 150,
            percent: 100,
          }),
        });
      },
    );

    await page.goto(`/view/${TOKEN}`);

    // Allow the prefetch pass to complete.
    await page.waitForFunction(
      () =>
        !document.body.textContent?.match(/Preparing pages|Caching locally/),
      { timeout: 10_000 },
    );

    // The prefetcher should have requested a tile for every page.
    const pagesTouched = new Set<string>();
    for (const url of tileUrls) {
      const m = /\/pages\/(\d+)\/tile/.exec(url);
      if (m) pagesTouched.add(m[1]!);
    }
    expect(pagesTouched.size).toBe(3);
    expect(pagesTouched).toEqual(new Set(["1", "2", "3"]));
  });

  test("warming failed renders the red error chip", async ({ page }) => {
    await installStubs(page, baseStubs({ pages: 5 }));
    await stubTile(page);

    await page.route(
      `**/api/lintpdf/viewer/public/${TOKEN}/tile-warming`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-abc",
            status: "failed",
            rendered: 1,
            total: 5,
            dpi: 150,
            percent: 20,
            error: "render crash",
          }),
        });
      },
    );

    await page.goto(`/view/${TOKEN}`);

    const chip = page.getByText(/Tile pre-cache failed/i);
    await expect(chip).toBeVisible({ timeout: 10_000 });
    // Red tone comes from the bg-rose-600 class on the chip container.
    const locator = chip.locator("xpath=ancestor::div[1]");
    await expect(locator).toHaveClass(/bg-rose-600/);
  });

  test("redis disabled hides the badge but prefetch still runs", async ({
    page,
  }) => {
    await installStubs(page, baseStubs({ pages: 4 }));
    const tileUrls: string[] = [];
    await stubTile(page, tileUrls);

    await page.route(
      `**/api/lintpdf/viewer/public/${TOKEN}/tile-warming`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-abc",
            status: "disabled",
            rendered: 0,
            total: 0,
            dpi: 150,
            percent: 0,
          }),
        });
      },
    );

    await page.goto(`/view/${TOKEN}`);

    // Give prefetch a chance to fire.
    await page.waitForTimeout(2_000);

    // Badge should never show "Preparing pages …".
    const prepBadge = page.getByText(/Preparing pages/);
    await expect(prepBadge).toHaveCount(0);

    // Prefetcher still populates the browser cache for every page.
    const pagesTouched = new Set<string>();
    for (const url of tileUrls) {
      const m = /\/pages\/(\d+)\/tile/.exec(url);
      if (m) pagesTouched.add(m[1]!);
    }
    expect(pagesTouched.size).toBe(4);
  });

  test("deep-link #ann=<uuid> flips to the annotation's page", async ({
    page,
  }) => {
    const annotationId = "11111111-2222-3333-4444-555555555555";
    const annotations = [
      {
        id: annotationId,
        page_num: 3,
        kind: "rect",
        color: "#dc2626",
        geometry: { x0: 100, y0: 100, x1: 200, y1: 200 },
        author_email: "test@example.com",
        author_name: "Test",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];
    await installStubs(
      page,
      baseStubs({ pages: 5, annotations: annotations as never }),
    );
    await stubTile(page);
    await page.route(
      `**/api/lintpdf/viewer/public/${TOKEN}/tile-warming`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-abc",
            status: "complete",
            rendered: 5,
            total: 5,
            dpi: 150,
            percent: 100,
          }),
        });
      },
    );

    await page.goto(`/view/${TOKEN}#ann=${annotationId}`);

    // The current-page indicator in the toolbar should land on page 3
    // once the annotation list loads. Waits for up to 10 s to cover
    // initial mount + annotation fetch.
    await expect(async () => {
      const marker = await page
        .getByText(/\bPage\s*3\s*\/\s*5\b/i)
        .or(page.locator('input[type="number"][value="3"]'))
        .first()
        .isVisible({ timeout: 200 })
        .catch(() => false);
      expect(marker).toBeTruthy();
    }).toPass({ timeout: 10_000 });
  });
});
