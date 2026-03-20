import { describe, it, expect, vi, beforeEach } from "vitest";
import { GroundedClient } from "../client";

const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("GroundedClient", () => {
  let client: GroundedClient;

  beforeEach(() => {
    client = new GroundedClient({
      apiUrl: "https://api.lintpdf.com",
      webhookSecret: "test-secret-long-enough",
      apiKey: "lpdf_test",
    });
    mockFetch.mockReset();
  });

  it("getJob sends correct request", async () => {
    const job = { job_id: "abc", status: "complete" };
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(job) });

    const result = await client.getJob("abc");
    expect(result).toEqual(job);
    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.lintpdf.com/api/v1/jobs/abc",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer lpdf_test" }),
      }),
    );
  });

  it("listJobs sends pagination params", async () => {
    const list = { jobs: [], total: 0, page: 2, page_size: 10 };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(list),
    });

    await client.listJobs(2, 10);
    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.lintpdf.com/api/v1/jobs?page=2&page_size=10",
      expect.anything(),
    );
  });

  it("deleteJob sends DELETE", async () => {
    mockFetch.mockResolvedValue({ ok: true });

    await client.deleteJob("abc");
    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.lintpdf.com/api/v1/jobs/abc",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("listProfiles calls correct endpoint", async () => {
    const profiles = { profiles: [] };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(profiles),
    });

    const result = await client.listProfiles();
    expect(result).toEqual(profiles);
    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.lintpdf.com/api/v1/profiles",
      expect.anything(),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });
    await expect(client.getJob("abc")).rejects.toThrow("LintPDF API: 500");
  });
});
