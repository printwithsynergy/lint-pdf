import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable, getEngineApiKey, getEngineBase } from "../helpers";

test.describe("Usage API", () => {
  let sessionToken: string;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  const headers = () => ({ Cookie: `pixie-dust-session=${sessionToken}` });

  test("GET /api/v1/usage returns usage stats via engine API", async ({ request }) => {
    const apiKey = getEngineApiKey();
    test.skip(!apiKey, "No engine API key available");

    const res = await request.get(`${getEngineBase()}/api/v1/usage`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("daily_limit");
    expect(body).toHaveProperty("daily_usage");
    expect(typeof body.daily_limit).toBe("number");
    expect(typeof body.daily_usage).toBe("number");
  });

  test("usage endpoint shows rate limit info", async ({ request }) => {
    const apiKey = getEngineApiKey();
    test.skip(!apiKey, "No engine API key available");

    const res = await request.get(`${getEngineBase()}/api/v1/usage`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.daily_usage).toBeLessThanOrEqual(body.daily_limit);
  });

  test("usage without API key returns 401", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/usage`);
    expect(res.status()).toBe(401);
  });
});
