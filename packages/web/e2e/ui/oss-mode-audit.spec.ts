/**
 * OSS-mode public-surface audit.
 *
 * Detects which mode the running site is in by inspecting /robots.txt:
 *   - SaaS mode  → robots is permissive, audit skipped (test passes).
 *   - OSS mode   → robots.txt explicitly disallows hidden routes.
 *
 * In OSS mode, asserts the three-layer indexing defense:
 *   1. /sitemap.xml only enumerates OSS-public routes.
 *   2. Each OSS-public page renders no internal anchor to a hidden route.
 *   3. Each hidden route returns an HTML body with
 *      `<meta name="robots" content="noindex, ...">`.
 *
 * The test is browser-less (uses Playwright's `request` context only) so
 * it runs fast and doesn't depend on Chromium hydration.
 */

import { test, expect } from "@playwright/test";

const OSS_PUBLIC = [
  "/",
  "/features",
  "/engine",
  "/about",
  "/contact",
  "/status",
  "/compliance",
] as const;

const HIDDEN_PREFIXES = [
  "/pricing",
  "/try-it",
  "/blog",
  "/changelog",
  "/integrations",
  "/swagger",
  "/ai",
  "/email-signature",
  "/beta",
  "/docs",
] as const;

function isHiddenPath(path: string): boolean {
  if (!path.startsWith("/")) return false;
  return HIDDEN_PREFIXES.some(
    (p) => path === p || path.startsWith(`${p}/`) || path.startsWith(`${p}#`),
  );
}

async function fetchText(request: import("@playwright/test").APIRequestContext, path: string): Promise<string> {
  const res = await request.get(path);
  expect(res.status(), `GET ${path} unexpected status`).toBeLessThan(500);
  return res.text();
}

test.describe("OSS-mode public-surface audit", () => {
  test("audit only runs in OSS mode", async ({ request }) => {
    const robots = await fetchText(request, "/robots.txt");
    const ossMode = robots.includes("Disallow: /pricing");

    if (!ossMode) {
      test.skip(true, "Site is in SaaS mode — OSS audit not applicable.");
    }
  });

  test("sitemap.xml only lists OSS-public routes", async ({ request }) => {
    const robots = await fetchText(request, "/robots.txt");
    test.skip(
      !robots.includes("Disallow: /pricing"),
      "SaaS mode — skipping",
    );

    const xml = await fetchText(request, "/sitemap.xml");
    const urls = Array.from(xml.matchAll(/<loc>([^<]+)<\/loc>/g)).map(
      (m) => new URL(m[1]).pathname,
    );

    expect(urls.length, "sitemap should not be empty").toBeGreaterThan(0);

    for (const path of urls) {
      const normalized = path === "" ? "/" : path.replace(/\/+$/, "") || "/";
      expect(
        (OSS_PUBLIC as readonly string[]).includes(normalized),
        `sitemap leaks non-public route: ${path}`,
      ).toBe(true);
    }
  });

  test("OSS-public pages link only to OSS-public routes", async ({
    request,
  }) => {
    const robots = await fetchText(request, "/robots.txt");
    test.skip(
      !robots.includes("Disallow: /pricing"),
      "SaaS mode — skipping",
    );

    for (const path of OSS_PUBLIC) {
      const html = await fetchText(request, path);
      const hrefs = Array.from(html.matchAll(/href="([^"]+)"/g))
        .map((m) => m[1])
        .filter((h) => h.startsWith("/") && !h.startsWith("//"));

      const leaks = hrefs.filter(isHiddenPath);
      expect(
        leaks,
        `${path} links to hidden routes: ${leaks.join(", ")}`,
      ).toEqual([]);
    }
  });

  test("hidden routes emit noindex meta", async ({ request }) => {
    const robots = await fetchText(request, "/robots.txt");
    test.skip(
      !robots.includes("Disallow: /pricing"),
      "SaaS mode — skipping",
    );

    // One representative path per hidden top-level segment that has a
    // page.tsx in this repo.
    const samples = [
      "/pricing",
      "/try-it",
      "/blog",
      "/changelog",
      "/integrations",
      "/swagger",
      "/ai",
      "/docs",
      "/beta/join",
    ];

    for (const path of samples) {
      const html = await fetchText(request, path);
      const hasNoindex = /name=["']robots["'][^>]*content=["'][^"']*noindex/i.test(
        html,
      );
      expect(hasNoindex, `${path} missing noindex meta`).toBe(true);
    }
  });
});
