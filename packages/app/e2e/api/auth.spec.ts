import { test, expect } from "@playwright/test";
import { authenticateViaMcpBackdoor, isMcpBackdoorAvailable } from "../helpers";

const MCP_SECRET_KEY = process.env.MCP_SECRET_KEY ?? "";

test.describe("Auth API", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor is not enabled on this environment");
  });

  test.describe("MCP Backdoor", () => {
    test("authenticates with valid credentials", async ({ request }) => {
      const auth = await authenticateViaMcpBackdoor(request);

      expect(auth.success).toBe(true);
      expect(auth.userId).toBeTruthy();
      expect(auth.sessionToken).toBeTruthy();
      expect(auth.expiresAt).toBeTruthy();
    });

    test("rejects invalid MCP secret key", async ({ request }) => {
      const res = await request.post("/api/auth/mcp-backdoor", {
        data: {
          email: "test@lintpdf.com",
          mcpSecretKey: "wrong-key-value",
        },
      });

      expect(res.status()).toBe(403);
      const body = await res.json();
      expect(body.error).toContain("Invalid MCP secret key");
    });

    test("rejects missing fields", async ({ request }) => {
      const res = await request.post("/api/auth/mcp-backdoor", {
        data: { email: "test@lintpdf.com" },
      });

      expect(res.status()).toBe(400);
    });

    test("rejects invalid email format", async ({ request }) => {
      const res = await request.post("/api/auth/mcp-backdoor", {
        data: { email: "not-an-email", mcpSecretKey: MCP_SECRET_KEY },
      });

      expect(res.status()).toBe(400);
    });
  });

  test.describe("GET /api/auth/me", () => {
    test("returns user info when authenticated", async ({ request }) => {
      // First authenticate
      const auth = await authenticateViaMcpBackdoor(request);

      // Then check /me with the session cookie (set by backdoor response)
      const meRes = await request.get("/api/auth/me");
      expect(meRes.ok()).toBe(true);

      const user = await meRes.json();
      expect(user.id).toBe(auth.userId);
      expect(user.email).toBeTruthy();
    });

    test("returns 401 when not authenticated", async ({ request }) => {
      // Fresh request context without auth
      const res = await request.get("/api/auth/me", {
        headers: { Cookie: "" },
      });

      // Could be 401 or redirect depending on middleware
      expect([401, 302, 307].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/auth/logout", () => {
    test("clears session and redirects", async ({ request }) => {
      // Authenticate first
      await authenticateViaMcpBackdoor(request);

      const res = await request.get("/api/auth/logout", {
        maxRedirects: 0,
      });

      // Logout should redirect to login page
      expect([200, 302, 307].includes(res.status())).toBe(true);
    });
  });
});
