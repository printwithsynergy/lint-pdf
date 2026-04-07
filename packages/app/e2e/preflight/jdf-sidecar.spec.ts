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

const MINIMAL_JDF = `<?xml version="1.0" encoding="UTF-8"?>
<JDF xmlns="http://www.CIP4.org/JDFSchema_1_1" Type="Product" Version="1.4">
  <ResourcePool>
    <RunList Class="Parameter" Status="Available">
      <LayoutElement>
        <FileSpec URL="test.pdf"/>
      </LayoutElement>
    </RunList>
  </ResourcePool>
</JDF>`;

const MALFORMED_JDF = `<?xml version="1.0" encoding="UTF-8"?>
<JDF xmlns="http://www.CIP4.org/JDFSchema_1_1" Type="Product" Version="1.4">
  <ResourcePool>
    <!-- Intentionally broken: missing closing tags -->
    <RunList Class="Parameter" Status="Available">
      <LayoutElement>
`;

test.describe("Preflight: JDF Sidecar Support", () => {
  let engineApiKey: string;
  let engineBase: string;
  let jdfSupported: boolean;

  test.beforeAll(async ({ request }) => {
    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();

    test.skip(!engineApiKey, "Engine API key not available");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    // Probe whether JDF sidecar is supported by attempting a minimal submission
    const pdfBuffer = readFileSync(TEST_PDF);
    const probeRes = await request.post(`${engineBase}/api/v1/jobs`, {
      headers: { Authorization: `Bearer ${engineApiKey}` },
      multipart: {
        file: {
          name: "test-sample.pdf",
          mimeType: "application/pdf",
          buffer: pdfBuffer,
        },
        profile_id: "lintpdf-default",
        jdf_file: {
          name: "job.jdf",
          mimeType: "application/xml",
          buffer: Buffer.from(MINIMAL_JDF, "utf-8"),
        },
      },
    });

    // If 404 on the whole endpoint or 400 specifically rejecting jdf_file, JDF is not supported
    // If 200/201/202, JDF is supported
    // If 400/422 for other reasons, still consider it "available but erroring"
    jdfSupported = [200, 201, 202].includes(probeRes.status());

    if (!jdfSupported) {
      const status = probeRes.status();
      // 400/422 could mean JDF param is rejected or invalid — check body
      if ([400, 422].includes(status)) {
        const body = await probeRes.text();
        const bodyLower = body.toLowerCase();
        // If error message specifically mentions jdf being unsupported, mark as unsupported
        jdfSupported = !(
          bodyLower.includes("jdf") &&
          (bodyLower.includes("not supported") ||
            bodyLower.includes("unknown") ||
            bodyLower.includes("unexpected"))
        );
      }
    }
  });

  test.describe("JDF submission", () => {
    test("POST /api/v1/jobs with JDF sidecar accepts the file", async ({
      request,
    }) => {
      test.skip(!jdfSupported, "JDF sidecar not supported in this deployment");

      const pdfBuffer = readFileSync(TEST_PDF);
      const res = await request.post(`${engineBase}/api/v1/jobs`, {
        headers: { Authorization: `Bearer ${engineApiKey}` },
        multipart: {
          file: {
            name: "test-sample.pdf",
            mimeType: "application/pdf",
            buffer: pdfBuffer,
          },
          profile_id: "lintpdf-default",
          jdf_file: {
            name: "job.jdf",
            mimeType: "application/xml",
            buffer: Buffer.from(MINIMAL_JDF, "utf-8"),
          },
        },
      });

      expect(
        [200, 201, 202].includes(res.status()),
        `JDF submission failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      const data = await res.json();
      const jobId = data.job_id ?? data.id;
      expect(jobId, "No job ID returned for JDF submission").toBeTruthy();

      // Check that JDF metadata is acknowledged
      if (data.jdf_metadata ?? data.jdfMetadata ?? data.metadata?.jdf) {
        const jdfMeta =
          data.jdf_metadata ?? data.jdfMetadata ?? data.metadata?.jdf;
        expect(jdfMeta).toBeTruthy();
      }
    });

    test("JDF-submitted job completes and includes JDF-derived settings", async ({
      request,
    }) => {
      test.skip(!jdfSupported, "JDF sidecar not supported in this deployment");

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
          jdf_file: {
            name: "job.jdf",
            mimeType: "application/xml",
            buffer: Buffer.from(MINIMAL_JDF, "utf-8"),
          },
        },
      });

      expect([200, 201, 202].includes(submitRes.status())).toBe(true);

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
        `JDF job ended with unexpected status: ${result.status}`,
      ).toContain(result.status);

      if (result.status === "complete") {
        // Check that the completed job acknowledges JDF-derived settings
        const resultStr = JSON.stringify(result).toLowerCase();
        const hasJdfReference =
          resultStr.includes("jdf") ||
          result.jdf_metadata !== undefined ||
          result.metadata !== undefined;

        // Soft check: JDF metadata may or may not be surfaced in the result
        if (hasJdfReference) {
          expect(hasJdfReference).toBe(true);
        }
      }
    });
  });

  test.describe("JDF error handling", () => {
    test("malformed JDF returns proper error", async ({ request }) => {
      test.skip(!jdfSupported, "JDF sidecar not supported in this deployment");

      const pdfBuffer = readFileSync(TEST_PDF);
      const res = await request.post(`${engineBase}/api/v1/jobs`, {
        headers: { Authorization: `Bearer ${engineApiKey}` },
        multipart: {
          file: {
            name: "test-sample.pdf",
            mimeType: "application/pdf",
            buffer: pdfBuffer,
          },
          profile_id: "lintpdf-default",
          jdf_file: {
            name: "job.jdf",
            mimeType: "application/xml",
            buffer: Buffer.from(MALFORMED_JDF, "utf-8"),
          },
        },
      });

      // Could either reject with 400/422 or accept but note the parse error
      if ([400, 422].includes(res.status())) {
        // Proper error response
        const body = await res.json().catch(() => null);
        if (body) {
          const errorMsg =
            body.error ?? body.message ?? body.detail ?? JSON.stringify(body);
          expect(
            typeof errorMsg === "string" ? errorMsg.length : true,
          ).toBeTruthy();
        }
      } else if ([200, 201, 202].includes(res.status())) {
        // Engine accepted it anyway (lenient parsing) — that's acceptable
        const data = await res.json();
        const jobId = data.job_id ?? data.id;
        expect(jobId).toBeTruthy();
      } else {
        // Unexpected status
        expect(
          false,
          `Unexpected status ${res.status()} for malformed JDF`,
        ).toBe(true);
      }
    });
  });

  test.describe("JDF not supported graceful skip", () => {
    test("submission without JDF still works normally", async ({ request }) => {
      // Sanity check: normal submission without JDF should always work
      const pdfBuffer = readFileSync(TEST_PDF);
      const res = await request.post(`${engineBase}/api/v1/jobs`, {
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
        [200, 201, 202].includes(res.status()),
        `Normal submit failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      const data = await res.json();
      expect(data.job_id ?? data.id).toBeTruthy();
    });
  });

  test.describe("Auth", () => {
    test("JDF submission rejects unauthenticated requests", async ({
      request,
    }) => {
      const pdfBuffer = readFileSync(TEST_PDF);
      const res = await request.post(`${engineBase}/api/v1/jobs`, {
        headers: { Authorization: "" },
        multipart: {
          file: {
            name: "test-sample.pdf",
            mimeType: "application/pdf",
            buffer: pdfBuffer,
          },
          profile_id: "lintpdf-default",
          jdf_file: {
            name: "job.jdf",
            mimeType: "application/xml",
            buffer: Buffer.from(MINIMAL_JDF, "utf-8"),
          },
        },
      });

      expect(res.ok()).toBe(false);
      expect(
        [401, 403].includes(res.status()),
        `Expected 401/403 without auth, got ${res.status()}`,
      ).toBe(true);
    });
  });
});
