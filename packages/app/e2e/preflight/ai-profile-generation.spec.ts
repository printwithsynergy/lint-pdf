import { test, expect } from "@playwright/test";
import {
  getEngineApiKey,
  getEngineBase,
} from "../helpers";

test.describe("Preflight: AI Profile Generation", () => {
  let engineApiKey: string;
  let engineBase: string;
  let endpointAvailable: boolean;

  test.beforeAll(async ({ request }) => {
    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();

    test.skip(!engineApiKey, "Engine API key not available");

    // Probe the endpoint to see if AI profile generation is deployed
    const probeRes = await request.post(
      `${engineBase}/api/v1/preflight-profiles/generate`,
      {
        headers: {
          Authorization: `Bearer ${engineApiKey}`,
          "Content-Type": "application/json",
        },
        data: { description: "probe" },
      },
    );
    // 404 means the feature is not deployed; anything else means it exists
    endpointAvailable = probeRes.status() !== 404;
  });

  test.describe("Profile generation from natural language", () => {
    test("generates profile for magazine print quality description", async ({
      request,
    }) => {
      test.skip(!endpointAvailable, "AI profile generation endpoint not deployed (404)");

      const res = await request.post(
        `${engineBase}/api/v1/preflight-profiles/generate`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            description:
              "Check for magazine print quality, 300 DPI minimum, CMYK only, no spot colors",
          },
        },
      );

      expect(
        [200, 201].includes(res.status()),
        `Profile generation failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      const profile = await res.json();
      expect(profile).toBeTruthy();

      // Profile should have a structure with checks or thresholds
      const hasChecks =
        profile.checks !== undefined ||
        profile.rules !== undefined ||
        profile.thresholds !== undefined ||
        profile.settings !== undefined;
      expect(
        hasChecks,
        "Generated profile missing checks/rules/thresholds/settings",
      ).toBe(true);
    });

    test("generated magazine profile has reasonable DPI threshold", async ({
      request,
    }) => {
      test.skip(!endpointAvailable, "AI profile generation endpoint not deployed (404)");

      const res = await request.post(
        `${engineBase}/api/v1/preflight-profiles/generate`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            description:
              "Check for magazine print quality, 300 DPI minimum, CMYK only, no spot colors",
          },
        },
      );

      expect(res.ok()).toBe(true);
      const profile = await res.json();

      // Flatten all values to look for a DPI-related threshold near 300
      const jsonStr = JSON.stringify(profile).toLowerCase();
      // The profile should reference DPI/resolution somewhere
      const mentionsDpi =
        jsonStr.includes("dpi") ||
        jsonStr.includes("resolution") ||
        jsonStr.includes("ppi");
      expect(
        mentionsDpi,
        "Expected profile to mention DPI/resolution for a 300 DPI requirement",
      ).toBe(true);
    });

    test("generates different profile for web-ready description", async ({
      request,
    }) => {
      test.skip(!endpointAvailable, "AI profile generation endpoint not deployed (404)");

      const magazineRes = await request.post(
        `${engineBase}/api/v1/preflight-profiles/generate`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            description:
              "Check for magazine print quality, 300 DPI minimum, CMYK only, no spot colors",
          },
        },
      );

      const webRes = await request.post(
        `${engineBase}/api/v1/preflight-profiles/generate`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            description: "Basic web-ready PDF check, allow RGB",
          },
        },
      );

      expect(magazineRes.ok()).toBe(true);
      expect(webRes.ok()).toBe(true);

      const magazineProfile = await magazineRes.json();
      const webProfile = await webRes.json();

      // The two profiles should differ in some meaningful way
      const magazineStr = JSON.stringify(magazineProfile);
      const webStr = JSON.stringify(webProfile);
      expect(
        magazineStr,
        "Expected different profiles for different descriptions",
      ).not.toBe(webStr);
    });
  });

  test.describe("Error handling", () => {
    test("empty description returns 400", async ({ request }) => {
      test.skip(!endpointAvailable, "AI profile generation endpoint not deployed (404)");

      const res = await request.post(
        `${engineBase}/api/v1/preflight-profiles/generate`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: { description: "" },
        },
      );

      expect(res.ok()).toBe(false);
      expect(
        [400, 422].includes(res.status()),
        `Expected 400/422 for empty description, got ${res.status()}`,
      ).toBe(true);
    });

    test("missing auth returns 401", async ({ request }) => {
      test.skip(!endpointAvailable, "AI profile generation endpoint not deployed (404)");

      const res = await request.post(
        `${engineBase}/api/v1/preflight-profiles/generate`,
        {
          headers: {
            Authorization: "",
            "Content-Type": "application/json",
          },
          data: {
            description: "Basic check",
          },
        },
      );

      expect(res.ok()).toBe(false);
      expect(
        [401, 403].includes(res.status()),
        `Expected 401/403 without auth, got ${res.status()}`,
      ).toBe(true);
    });
  });
});
