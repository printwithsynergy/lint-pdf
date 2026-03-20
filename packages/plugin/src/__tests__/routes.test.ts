import { describe, it, expect, vi, beforeEach } from "vitest";
import type { RouteRequest } from "@thinkneverland/pixie-dust-fairy-ring";

// Mock the index module to control getClient()
vi.mock("../index", () => ({
  getClient: vi.fn(),
}));

import { getClient } from "../index";
import { jobRoutes } from "../routes/jobs";
import { profileRoutes } from "../routes/profiles";

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

      const res = await handler!({
        query: {},
        params: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323
      expect(res.status).toBe(503);
      expect(res.body).toEqual({ error: "Grounded API not configured" });
    });

    it("lists jobs with default pagination", async () => {
      const mockJobs = {
        jobs: [{ job_id: "j1" }],
        total: 1,
        page: 1,
        page_size: 20,
      };
      const mockClient = { listJobs: vi.fn().mockResolvedValue(mockJobs) };
      vi.mocked(getClient).mockReturnValue(
        mockClient as unknown as ReturnType<typeof getClient>,
      ); // skipcq: JS-0323

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;
      const res = await handler!({
        query: {},
        params: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockJobs);
      expect(mockClient.listJobs).toHaveBeenCalledWith(1, 20);
    });

    it("lists jobs with custom pagination from query params", async () => {
      const mockClient = { listJobs: vi.fn().mockResolvedValue({ jobs: [] }) };
      vi.mocked(getClient).mockReturnValue(
        mockClient as unknown as ReturnType<typeof getClient>,
      ); // skipcq: JS-0323

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs",
      )?.handler;
      await handler!({
        query: { page: "3", page_size: "10" },
        params: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323

      expect(mockClient.listJobs).toHaveBeenCalledWith(3, 10);
    });
  });

  describe("GET /jobs/:jobId handler", () => {
    it("returns 503 when client is not configured", async () => {
      vi.mocked(getClient).mockReturnValue(null);
      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs/:jobId",
      )?.handler;

      const res = await handler!({
        params: { jobId: "abc" },
        query: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323
      expect(res.status).toBe(503);
    });

    it("returns job by ID", async () => {
      const mockJob = { job_id: "abc", status: "complete" };
      const mockClient = { getJob: vi.fn().mockResolvedValue(mockJob) };
      vi.mocked(getClient).mockReturnValue(
        mockClient as unknown as ReturnType<typeof getClient>,
      ); // skipcq: JS-0323

      const handler = routes.find(
        (r) => r.method === "GET" && r.path === "/jobs/:jobId",
      )?.handler;
      const res = await handler!({
        params: { jobId: "abc" },
        query: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockJob);
      expect(mockClient.getJob).toHaveBeenCalledWith("abc");
    });
  });

  describe("DELETE /jobs/:jobId handler", () => {
    it("returns 503 when client is not configured", async () => {
      vi.mocked(getClient).mockReturnValue(null);
      const handler = routes.find(
        (r) => r.method === "DELETE" && r.path === "/jobs/:jobId",
      )?.handler;

      const res = await handler!({
        params: { jobId: "abc" },
        query: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323
      expect(res.status).toBe(503);
    });

    it("deletes job and returns 204", async () => {
      // skipcq: JS-W1042 — mockResolvedValue requires an explicit value
      const mockClient = { deleteJob: vi.fn().mockResolvedValue(undefined) };
      vi.mocked(getClient).mockReturnValue(
        mockClient as unknown as ReturnType<typeof getClient>,
      ); // skipcq: JS-0323

      const handler = routes.find(
        (r) => r.method === "DELETE" && r.path === "/jobs/:jobId",
      )?.handler;
      const res = await handler!({
        params: { jobId: "del_123" },
        query: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323

      expect(res.status).toBe(204);
      expect(mockClient.deleteJob).toHaveBeenCalledWith("del_123");
    });
  });
});

describe("profileRoutes", () => {
  let routes: ReturnType<typeof profileRoutes>;

  beforeEach(() => {
    vi.clearAllMocks();
    routes = profileRoutes();
  });

  it("returns 1 route definition", () => {
    expect(routes).toHaveLength(1);
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

      const res = await handler({
        query: {},
        params: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323
      expect(res.status).toBe(503);
      expect(res.body).toEqual({ error: "Grounded API not configured" });
    });

    it("returns profiles list", async () => {
      const mockProfiles = { profiles: [{ id: "p1", name: "PDF/X-1a" }] };
      const mockClient = {
        listProfiles: vi.fn().mockResolvedValue(mockProfiles),
      };
      vi.mocked(getClient).mockReturnValue(
        mockClient as unknown as ReturnType<typeof getClient>,
      ); // skipcq: JS-0323

      const handler = routes[0].handler;
      const res = await handler({
        query: {},
        params: {},
        body: {},
        auth: {},
      } as unknown as RouteRequest); // skipcq: JS-0323

      expect(res.status).toBe(200);
      expect(res.body).toEqual(mockProfiles);
      expect(mockClient.listProfiles).toHaveBeenCalled();
    });
  });
});
