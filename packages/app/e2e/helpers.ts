/**
 * Shared test helpers for the app service E2E tests.
 * Uses the MCP backdoor endpoint for automated authentication.
 */
import type { APIRequestContext, Browser } from "@playwright/test";

const MCP_SECRET_KEY = process.env.MCP_SECRET_KEY ?? "";
const DEFAULT_TEST_EMAIL = "e2e-test@nevergrounded.io";

export interface McpAuthResult {
  success: boolean;
  userId: string;
  sessionToken: string;
  expiresAt: string;
}

/**
 * Authenticate via the MCP backdoor endpoint.
 * Returns session details including the token for cookie-based auth.
 */
export async function authenticateViaMcpBackdoor(
  request: APIRequestContext,
  email: string = DEFAULT_TEST_EMAIL,
): Promise<McpAuthResult> {
  const res = await request.post("/api/auth/mcp-backdoor", {
    data: { email, mcpSecretKey: MCP_SECRET_KEY },
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok()) {
    const body = await res.text();
    throw new Error(`MCP backdoor auth failed (${res.status()}): ${body}`);
  }

  return res.json() as Promise<McpAuthResult>;
}

/**
 * Create a browser context pre-authenticated via the MCP backdoor.
 * Sets the session cookie so all subsequent page navigations are authenticated.
 */
export async function createAuthenticatedContext(
  browser: Browser,
  baseURL: string,
  email: string = DEFAULT_TEST_EMAIL,
) {
  const context = await browser.newContext({ baseURL });
  const request = context.request;

  const auth = await authenticateViaMcpBackdoor(request, email);

  // The MCP backdoor sets the cookie via Set-Cookie header,
  // but we also set it explicitly in case of cross-origin issues
  const url = new URL(baseURL);
  await context.addCookies([
    {
      name: "pixie-dust-session",
      value: auth.sessionToken,
      domain: url.hostname,
      path: "/",
      httpOnly: true,
      secure: url.protocol === "https:",
      sameSite: "Lax",
    },
  ]);

  return { context, auth };
}

/**
 * Check if the MCP backdoor is available and properly configured.
 * Returns false if: MCP_SECRET_KEY not set, backdoor disabled (404), or server error (500).
 */
export async function isMcpBackdoorAvailable(
  request: APIRequestContext,
): Promise<boolean> {
  if (!MCP_SECRET_KEY) {
    return false;
  }

  try {
    const res = await request.post("/api/auth/mcp-backdoor", {
      data: { email: "probe@test.io", mcpSecretKey: "probe" },
      headers: { "Content-Type": "application/json" },
    });
    // 404 = backdoor disabled, 500 = server issue, 400/403 = enabled but creds wrong
    return res.status() !== 404 && res.status() < 500;
  } catch {
    return false;
  }
}
