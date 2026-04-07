/**
 * Shared test helpers for the app service E2E tests.
 * Uses the MCP backdoor endpoint for automated authentication.
 */
import type { APIRequestContext, Browser } from "@playwright/test";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";
import type { TestState } from "./fixtures/test-setup";

const MCP_SECRET_KEY = process.env.MCP_SECRET_KEY ?? "";
const DEFAULT_TEST_EMAIL = "e2e-test@lintpdf.com";
const STATE_FILE = resolve(__dirname, ".test-state.json");

export interface McpAuthResult {
  success: boolean;
  userId: string;
  sessionToken: string;
  expiresAt: string;
  tenantId?: string;
}

/**
 * Authenticate via the MCP backdoor endpoint.
 * Returns session details including the token for cookie-based auth.
 */
export async function authenticateViaMcpBackdoor(
  request: APIRequestContext,
  email: string = DEFAULT_TEST_EMAIL,
  options?: { tenantSlug?: string; role?: string },
): Promise<McpAuthResult> {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await request.post("/api/auth/mcp-backdoor", {
      data: {
        email,
        mcpSecretKey: MCP_SECRET_KEY,
        ...(options?.tenantSlug ? { tenantSlug: options.tenantSlug } : {}),
        ...(options?.role ? { role: options.role } : {}),
      },
      headers: { "Content-Type": "application/json" },
    });

    if (res.ok()) {
      return res.json() as Promise<McpAuthResult>;
    }

    if (res.status() === 429 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 2000 * (attempt + 1)));
      continue;
    }

    const body = await res.text();
    throw new Error(`MCP backdoor auth failed (${res.status()}): ${body}`);
  }

  throw new Error("MCP backdoor auth failed after retries");
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

  const auth = await authenticateViaMcpBackdoor(request, email, {
    tenantSlug: TEST_TENANT_SLUG,
    role: "MEMBER",
  });

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

// ---------- Test state helpers ----------

let _testState: TestState | null = null;

export function loadTestState(): TestState | null {
  if (_testState) return _testState;
  if (existsSync(STATE_FILE)) {
    _testState = JSON.parse(readFileSync(STATE_FILE, "utf-8"));
    return _testState;
  }
  return null;
}

export function getTestTenantSlug(): string {
  return loadTestState()?.tenantSlug ?? "e2e-test-org";
}

export function getTestTenantId(): string {
  return loadTestState()?.tenantId ?? "";
}

export function getEngineApiKey(): string {
  return loadTestState()?.engineApiKey ?? process.env.ENGINE_API_KEY ?? "";
}

export function getAdminApiKey(): string {
  return loadTestState()?.adminApiKey ?? process.env.ADMIN_API_KEY ?? "";
}

// ---------- Role-specific auth ----------

export type TestRole = "super-admin" | "owner" | "admin" | "operator" | "member" | "viewer";

const ROLE_EMAILS: Record<TestRole, string> = {
  "super-admin": "super-admin@e2e.lintpdf.com",
  owner: "owner@e2e.lintpdf.com",
  admin: "admin@e2e.lintpdf.com",
  operator: "operator@e2e.lintpdf.com",
  member: "member@e2e.lintpdf.com",
  viewer: "viewer@e2e.lintpdf.com",
};

const ROLE_TO_TENANT_ROLE: Record<TestRole, string> = {
  "super-admin": "OWNER",
  owner: "OWNER",
  admin: "ADMIN",
  operator: "OPERATOR",
  member: "MEMBER",
  viewer: "VIEWER",
};

const TEST_TENANT_SLUG = "e2e-test-org";

/**
 * Get email for a specific test role.
 */
export function getRoleEmail(role: TestRole): string {
  return ROLE_EMAILS[role];
}

/**
 * Create an authenticated browser context for a specific role.
 */
export async function createRoleContext(
  browser: Browser,
  baseURL: string,
  role: TestRole,
) {
  const email = ROLE_EMAILS[role];
  const context = await browser.newContext({ baseURL });
  const request = context.request;

  const auth = await authenticateViaMcpBackdoor(request, email, {
    tenantSlug: TEST_TENANT_SLUG,
    role: ROLE_TO_TENANT_ROLE[role],
  });

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
 * Authenticate via MCP backdoor for a specific role (API context).
 */
export async function authenticateRole(
  request: APIRequestContext,
  role: TestRole,
): Promise<McpAuthResult> {
  return authenticateViaMcpBackdoor(request, ROLE_EMAILS[role], {
    tenantSlug: TEST_TENANT_SLUG,
    role: ROLE_TO_TENANT_ROLE[role],
  });
}

// ---------- Engine helpers ----------

const ENGINE_BASE = process.env.ENGINE_BASE_URL ?? "https://engine.lintpdf.com";

export function getEngineBase(): string {
  return ENGINE_BASE;
}

/**
 * Poll a job via the plugin route until it reaches a terminal status.
 */
export async function pollJobViaApp(
  request: APIRequestContext,
  jobId: string,
  sessionToken: string,
  maxWaitMs = 60_000,
  intervalMs = 2_000,
): Promise<Record<string, unknown>> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const res = await request.get(`/api/lintpdf/jobs/${jobId}`, {
      headers: { Cookie: `pixie-dust-session=${sessionToken}` },
    });
    if (res.ok()) {
      const data = await res.json();
      if (data.status === "complete" || data.status === "failed") {
        return data;
      }
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Job ${jobId} did not complete within ${maxWaitMs}ms`);
}

/**
 * Poll a job via the engine API until it reaches a terminal status.
 */
export async function pollJobViaEngine(
  request: APIRequestContext,
  jobId: string,
  apiKey: string,
  maxWaitMs = 60_000,
  intervalMs = 2_000,
): Promise<Record<string, unknown>> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const res = await request.get(`${ENGINE_BASE}/api/v1/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (res.ok()) {
      const data = await res.json();
      if (data.status === "complete" || data.status === "failed") {
        return data;
      }
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Job ${jobId} did not complete within ${maxWaitMs}ms`);
}
