import { describe, it, expect, vi, beforeEach } from "vitest";
import type { RouteRequest } from "@thinkneverland/pixie-dust-fairy-ring";

// Mock the index module to control getClient()
vi.mock("../index", () => ({
  getClient: vi.fn(),
}));

import { getClient } from "../index";
import { jobRoutes } from "../routes/jobs";
import { profileRoutes } from "../routes/profiles";

/** Create a mock RouteRequest with sensible defaults. */
function createMockRequest(
  overrides: {
    query?: Record<string, string>;
    params?: Record<string, string>;
    body?: Record<string, unknown>;
    auth?: Record<string, unknown>;
  } = {},
): RouteRequest {
  return {
    query: overrides.query ?? {},
    params: overrides.params ?? {},
    body: overrides.body ?? {},
    auth: overrides.auth ?? {},
  } as RouteRequest;
}

/** Create a mock client typed to match getClient()'s return type. */
function createMockClient(
  methods: Record<string, ReturnType<typeof vi.fn>>,
): ReturnType<typeof getClient> {
  return methods as unknown as ReturnType<typeof getClient>;
}

describe("jobRoutes", () => {
  let routes: ReturnType<typeof jobRoutes>;
  let fetchSpy: ReturnType<typeof vi.fn>;

  /** Build a fetch implementation that resolves to a fake ``Response``. */
  function fakeFetch(
    status: number,
    body: unknown,
  ): () => Promise<Response> {
    return () =>
      Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
        text: async () =>
          typeof body === "string" ? body : JSON.stringify(body),
      } as Response);
  }

  beforeEach(() => {
    vi.clearAllMocks();
    routes = jobRoutes();
    // jobs.ts calls global ``fetch`` directly via ``engineFetch``; replace it
    // with a vi.fn() so we can both stub the response and assert the URL.
    fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof globalThis.fetch;
  });

  it("returns 3 route definitions", () => {
    expect(routes).toHaveLength(3);
  });

  it("defines GET /jobs route with correct metadata", () => {
    const route = routes.find((r) => r.method === "GET" && r.path === "/jobs");
    expect(route).toBeDefined();
    expect(route?.auth).toBe(true);
    expect(route?.permission).toBe("preflight:view");
  });

  it("defines GET /jobs/:jobId route", () => {
    const route = routes.find(
      (r) => r.method === "GET" && r.path === "/jobs/:jobId",
    );
    expect(route).toBeDefined();
    expect(route?.auth).toBe(true);
    expect(route?.permission).toBe("preflight:view");
  });

  it("defines DELETE /jobs/:jobId route", () => {
    const route = routes.find(
      (r) => r.method === "DELETE" && r.path === "/jobs/:jobId",
    );
    expect(route).toBeDefined();
    expect(route?.auth).toBe(true);
    expect(route?.permission).toBe("preflight:submit");
  });

  describe("GET /jobs handler", () => {
    it("lists jobs with default pagination", async () => {
      const mockJobs = {
        jobs: [{ job_id: "j1" }],
        total: 1,
        page: 1,
        page_size: 20,
      };
      fetchSpy.mockImplementation(fakeFetch(200, mockJobs));

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;
      const res = await handler!(createMockRequest());

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockJobs);
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/jobs?page=1&page_size=20"),
        expect.any(Object),
      );
    });

    it("lists jobs with custom pagination from query params", async () => {
      fetchSpy.mockImplementation(fakeFetch(200, { jobs: [] }));

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;
      await handler!(
        createMockRequest({ query: { page: "3", page_size: "10" } }),
      );

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/jobs?page=3&page_size=10"),
        expect.any(Object),
      );
    });

    it("propagates engine error status codes", async () => {
      fetchSpy.mockImplementation(fakeFetch(503, "engine down"));

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;
      const res = await handler!(createMockRequest());
      expect(res.status).toBe(503);
    });
  });

  describe("GET /jobs/:jobId handler", () => {
    it("returns job by ID", async () => {
      const mockJob = { job_id: "abc", status: "complete" };
      fetchSpy.mockImplementation(fakeFetch(200, mockJob));

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs/:jobId",
      )?.handler;
      const res = await handler!(
        createMockRequest({ params: { jobId: "abc" } }),
      );

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockJob);
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/jobs/abc"),
        expect.any(Object),
      );
    });

    it("returns 404 when engine returns 404", async () => {
      fetchSpy.mockImplementation(
        fakeFetch(404, { detail: "not found" }),
      );

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs/:jobId",
      )?.handler;
      const res = await handler!(
        createMockRequest({ params: { jobId: "missing" } }),
      );
      expect(res.status).toBe(404);
    });
  });

  describe("DELETE /jobs/:jobId handler", () => {
    it("deletes job and returns 204", async () => {
      fetchSpy.mockImplementation(fakeFetch(204, null));

      const handler = routes.find(
        (r) => r.method === "DELETE" && r.path === "/jobs/:jobId",
      )?.handler;
      const res = await handler!(
        createMockRequest({ params: { jobId: "del_123" } }),
      );

      expect(res.status).toBe(204);
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/jobs/del_123"),
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });
});

describe("profileRoutes", () => {
  let routes: ReturnType<typeof profileRoutes>;

  beforeEach(() => {
    vi.clearAllMocks();
    routes = profileRoutes();
  });

  it("returns 4 route definitions", () => {
    expect(routes).toHaveLength(4);
  });

  it("defines GET /profiles route with correct metadata", () => {
    const route = routes[0];
    expect(route.method).toBe("GET");
    expect(route.path).toBe("/profiles");
    expect(route.auth).toBe(true);
    expect(route.permission).toBe("preflight:view");
  });

  describe("GET /profiles handler", () => {
    it("returns 503 when client is not configured", async () => {
      vi.mocked(getClient).mockReturnValue(null);
      const handler = routes[0].handler;

      const res = await handler(createMockRequest());
      expect(res.status).toBe(503);
      expect(res.body).toEqual({ error: "LintPDF API not configured" });
    });

    it("returns profiles list", async () => {
      const mockProfiles = { profiles: [{ id: "p1", name: "PDF/X-1a" }] };
      const mockClient = createMockClient({
        listProfiles: vi.fn().mockResolvedValue(mockProfiles),
      });
      vi.mocked(getClient).mockReturnValue(mockClient);

      const handler = routes[0].handler;
      const res = await handler(createMockRequest());

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockProfiles);
      expect(
        (mockClient as unknown as Record<string, ReturnType<typeof vi.fn>>)
          .listProfiles,
      ).toHaveBeenCalled();
    });
  });
});
