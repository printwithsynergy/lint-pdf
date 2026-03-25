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

  beforeEach(() => {
    vi.clearAllMocks();
    routes = jobRoutes();
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
    it("returns 503 when client is not configured", async () => {
      vi.mocked(getClient).mockReturnValue(null);
      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;

      const res = await handler!(createMockRequest());
      expect(res.status).toBe(503);
      expect(res.body).toEqual({ error: "LintPDF API not configured" });
    });

    it("lists jobs with default pagination", async () => {
      const mockJobs = {
        jobs: [{ job_id: "j1" }],
        total: 1,
        page: 1,
        page_size: 20,
      };
      const mockClient = createMockClient({
        listJobs: vi.fn().mockResolvedValue(mockJobs),
      });
      vi.mocked(getClient).mockReturnValue(mockClient);

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;
      const res = await handler!(createMockRequest());

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockJobs);
      expect(
        (mockClient as unknown as Record<string, ReturnType<typeof vi.fn>>)
          .listJobs,
      ).toHaveBeenCalledWith(1, 20);
    });

    it("lists jobs with custom pagination from query params", async () => {
      const mockClient = createMockClient({
        listJobs: vi.fn().mockResolvedValue({ jobs: [] }),
      });
      vi.mocked(getClient).mockReturnValue(mockClient);

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;
      await handler!(
        createMockRequest({ query: { page: "3", page_size: "10" } }),
      );

      expect(
        (mockClient as unknown as Record<string, ReturnType<typeof vi.fn>>)
          .listJobs,
      ).toHaveBeenCalledWith(3, 10);
    });
  });

  describe("GET /jobs/:jobId handler", () => {
    it("returns 503 when client is not configured", async () => {
      vi.mocked(getClient).mockReturnValue(null);
      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs/:jobId",
      )?.handler;

      const res = await handler!(
        createMockRequest({ params: { jobId: "abc" } }),
      );
      expect(res.status).toBe(503);
    });

    it("returns job by ID", async () => {
      const mockJob = { job_id: "abc", status: "complete" };
      const mockClient = createMockClient({
        getJob: vi.fn().mockResolvedValue(mockJob),
      });
      vi.mocked(getClient).mockReturnValue(mockClient);

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs/:jobId",
      )?.handler;
      const res = await handler!(
        createMockRequest({ params: { jobId: "abc" } }),
      );

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockJob);
      expect(
        (mockClient as unknown as Record<string, ReturnType<typeof vi.fn>>)
          .getJob,
      ).toHaveBeenCalledWith("abc");
    });
  });

  describe("DELETE /jobs/:jobId handler", () => {
    it("returns 503 when client is not configured", async () => {
      vi.mocked(getClient).mockReturnValue(null);
      const handler = routes.find(
        (r) => r.method === "DELETE" && r.path === "/jobs/:jobId",
      )?.handler;

      const res = await handler!(
        createMockRequest({ params: { jobId: "abc" } }),
      );
      expect(res.status).toBe(503);
    });

    it("deletes job and returns 204", async () => {
      const mockClient = createMockClient({
        deleteJob: vi.fn().mockResolvedValue(undefined),
      });
      vi.mocked(getClient).mockReturnValue(mockClient);

      const handler = routes.find(
        (r) => r.method === "DELETE" && r.path === "/jobs/:jobId",
      )?.handler;
      const res = await handler!(
        createMockRequest({ params: { jobId: "del_123" } }),
      );

      expect(res.status).toBe(204);
      expect(
        (mockClient as unknown as Record<string, ReturnType<typeof vi.fn>>)
          .deleteJob,
      ).toHaveBeenCalledWith("del_123");
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
