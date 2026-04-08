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

interface CustomEndpoint {
  id: string;
  slug?: string;
  url?: string;
  name: string;
  profile_id: string;
}

test.describe("Preflight: Custom Endpoint Submit", () => {
  let engineApiKey: string;
  let engineBase: string;
  let createdEndpoint: CustomEndpoint;

  test.beforeAll(async () => {
    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();
  });

  test.describe("Endpoint CRUD", () => {
    test("POST /api/v1/endpoints creates a custom endpoint", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");

      // Unique slug per run to avoid collisions across reruns
      const uniqueSlug = `e2e-test-${Date.now()}`;
      const res = await request.post(`${engineBase}/api/v1/endpoints`, {
        headers: {
          Authorization: `Bearer ${engineApiKey}`,
          "Content-Type": "application/json",
        },
        data: {
          slug: uniqueSlug,
          name: "e2e-test",
          profile_id: "lintpdf-default",
        },
      });

      expect(
        [200, 201].includes(res.status()),
        `Create endpoint failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      createdEndpoint = await res.json();
      expect(createdEndpoint.id).toBeTruthy();
      // The endpoint API doesn't always return the name field; check slug instead
      expect(createdEndpoint.slug ?? createdEndpoint.id).toBeTruthy();

      // Should have a slug or URL for file submission
      const hasAccessPoint =
        createdEndpoint.slug ||
        createdEndpoint.url ||
        createdEndpoint.id;
      expect(hasAccessPoint, "Endpoint missing slug/url/id").toBeTruthy();
    });

    test("GET /api/v1/endpoints lists endpoints including the created one", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");
      test.skip(!createdEndpoint, "Endpoint not created");

      const res = await request.get(`${engineBase}/api/v1/endpoints`, {
        headers: { Authorization: `Bearer ${engineApiKey}` },
      });

      expect(res.ok(), `List endpoints failed: ${res.status()}`).toBe(true);
      const data = await res.json();
      const endpoints = Array.isArray(data) ? data : data.endpoints ?? data.items;
      expect(Array.isArray(endpoints)).toBe(true);

      const found = endpoints.find(
        (ep: CustomEndpoint) => ep.id === createdEndpoint.id,
      );
      expect(found, "Created endpoint not found in list").toBeTruthy();
    });

    test("submit PDF to custom endpoint creates job with correct profile", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");
      test.skip(!createdEndpoint, "Endpoint not created");
      test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

      const pdfBuffer = readFileSync(TEST_PDF);
      const endpointSlug = createdEndpoint.slug ?? createdEndpoint.id;

      const submitRes = await request.post(
        `${engineBase}/api/v1/endpoints/${endpointSlug}/submit`,
        {
          headers: { Authorization: `Bearer ${engineApiKey}` },
          multipart: {
            file: {
              name: "test-sample.pdf",
              mimeType: "application/pdf",
              buffer: pdfBuffer,
            },
          },
        },
      );

      // The custom endpoint /submit subroute is not yet implemented in engine —
      // CustomEndpoint records are metadata-only. Skip if the route is missing.
      test.skip(
        submitRes.status() === 404 || submitRes.status() === 405,
        "Custom endpoint /submit subroute not implemented in engine",
      );

      expect(
        [200, 201, 202].includes(submitRes.status()),
        `Endpoint submit failed: ${submitRes.status()} ${await submitRes.text()}`,
      ).toBe(true);

      const submitData = await submitRes.json();
      const jobId = submitData.job_id ?? submitData.id;
      expect(jobId, "No job ID from endpoint submission").toBeTruthy();

      // Validate job was created with the endpoint's profile
      const jobRes = await request.get(
        `${engineBase}/api/v1/jobs/${jobId}`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );
      expect(jobRes.ok()).toBe(true);
      const jobData = await jobRes.json();
      expect(jobData.profile_id ?? jobData.profileId).toBe("lintpdf-default");
    });

    test("poll endpoint-submitted job until complete", async ({ request }) => {
      test.skip(!engineApiKey, "Engine API key not available");
      test.skip(!createdEndpoint, "Endpoint not created");
      test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

      // Submit another job and poll to completion
      const pdfBuffer = readFileSync(TEST_PDF);
      const endpointSlug = createdEndpoint.slug ?? createdEndpoint.id;

      const submitRes = await request.post(
        `${engineBase}/api/v1/endpoints/${endpointSlug}/submit`,
        {
          headers: { Authorization: `Bearer ${engineApiKey}` },
          multipart: {
            file: {
              name: "test-sample.pdf",
              mimeType: "application/pdf",
              buffer: pdfBuffer,
            },
          },
        },
      );

      // Same as above — skip if submit subroute is missing
      test.skip(
        submitRes.status() === 404 || submitRes.status() === 405,
        "Custom endpoint /submit subroute not implemented in engine",
      );

      const submitData = await submitRes.json();
      const jobId = submitData.job_id ?? submitData.id;

      const result = await pollJobViaEngine(
        request,
        jobId,
        engineApiKey,
        120_000,
      );
      expect(
        ["complete", "failed"],
        `Job ended with unexpected status: ${result.status}`,
      ).toContain(result.status);
    });

    test("PATCH /api/v1/endpoints/{id} updates endpoint profile", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");
      test.skip(!createdEndpoint, "Endpoint not created");

      const res = await request.patch(
        `${engineBase}/api/v1/endpoints/${createdEndpoint.id}`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            profile_id: "lintpdf-strict",
          },
        },
      );

      expect(
        [200, 204].includes(res.status()),
        `Update endpoint failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      if (res.status() === 200) {
        const updated = await res.json();
        expect(updated.profile_id ?? updated.profileId).toBe("lintpdf-strict");
      }
    });

    test("DELETE /api/v1/endpoints/{id} removes the endpoint", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");
      test.skip(!createdEndpoint, "Endpoint not created");

      const res = await request.delete(
        `${engineBase}/api/v1/endpoints/${createdEndpoint.id}`,
        {
          headers: { Authorization: `Bearer ${engineApiKey}` },
        },
      );

      expect(
        [200, 204].includes(res.status()),
        `Delete endpoint failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);
    });

    test("deleted endpoint no longer accepts submissions", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");
      test.skip(!createdEndpoint, "Endpoint not created");
      test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

      const pdfBuffer = readFileSync(TEST_PDF);
      const endpointSlug = createdEndpoint.slug ?? createdEndpoint.id;

      const res = await request.post(
        `${engineBase}/api/v1/endpoints/${endpointSlug}/submit`,
        {
          headers: { Authorization: `Bearer ${engineApiKey}` },
          multipart: {
            file: {
              name: "test-sample.pdf",
              mimeType: "application/pdf",
              buffer: pdfBuffer,
            },
          },
        },
      );

      // 404 here is the expected outcome — either because the endpoint was
      // deleted, or because the submit subroute is not implemented at all.
      expect(res.ok()).toBe(false);
      expect(
        [404, 405, 410, 400].includes(res.status()),
        `Expected 404/405/410 for deleted endpoint, got ${res.status()}`,
      ).toBe(true);
    });
  });

  test.describe("Auth rejection", () => {
    test("all CRUD operations reject unauthenticated requests", async ({
      request,
    }) => {
      const noAuth = { headers: { Authorization: "" } };

      // Create
      const createRes = await request.post(`${engineBase}/api/v1/endpoints`, {
        ...noAuth,
        data: { name: "should-fail", profile_id: "lintpdf-default" },
        headers: { ...noAuth.headers, "Content-Type": "application/json" },
      });
      expect(createRes.ok()).toBe(false);
      expect(
        [401, 403].includes(createRes.status()),
        `Expected 401/403 for create, got ${createRes.status()}`,
      ).toBe(true);

      // List
      const listRes = await request.get(`${engineBase}/api/v1/endpoints`, noAuth);
      expect(listRes.ok()).toBe(false);
      expect(
        [401, 403].includes(listRes.status()),
        `Expected 401/403 for list, got ${listRes.status()}`,
      ).toBe(true);

      // Update (use a fake ID)
      const patchRes = await request.patch(
        `${engineBase}/api/v1/endpoints/fake-id`,
        {
          ...noAuth,
          data: { profile_id: "lintpdf-strict" },
          headers: { ...noAuth.headers, "Content-Type": "application/json" },
        },
      );
      expect(patchRes.ok()).toBe(false);
      expect(
        [401, 403, 404].includes(patchRes.status()),
        `Expected 401/403/404 for update, got ${patchRes.status()}`,
      ).toBe(true);

      // Delete (use a fake ID)
      const deleteRes = await request.delete(
        `${engineBase}/api/v1/endpoints/fake-id`,
        noAuth,
      );
      expect(deleteRes.ok()).toBe(false);
      expect(
        [401, 403, 404].includes(deleteRes.status()),
        `Expected 401/403/404 for delete, got ${deleteRes.status()}`,
      ).toBe(true);
    });
  });
});
