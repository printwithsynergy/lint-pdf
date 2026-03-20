/**
 * Shared test helpers and credentials loader.
 */
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";
import type { APIRequestContext } from "@playwright/test";

interface JobResult {
  status: string;
  [key: string]: unknown;
}

export interface TenantCreds {
  id: string;
  name: string;
  api_key: string;
}

export interface TestCredentials {
  admin_key: string;
  tenants: Record<string, TenantCreds>;
}

let _creds: TestCredentials | null = null;

export function loadCredentials(): TestCredentials {
  if (_creds) return _creds;

  // Try multiple locations
  const candidates = [
    resolve(__dirname, "../test-credentials.json"),
    resolve(__dirname, "../../test-credentials.json"),
  ];

  for (const p of candidates) {
    if (existsSync(p)) {
      _creds = JSON.parse(readFileSync(p, "utf-8"));
      return _creds as TestCredentials;
    }
  }

  // Fall back to env vars
  _creds = {
    admin_key:
      process.env.ADMIN_API_KEY ??
      "gx0B011GFHNLxx4q8KOfafMcCgLifHgec-u1TKpPOpA",
    tenants: {},
  };
  return _creds;
}

export function getAdminKey(): string {
  return loadCredentials().admin_key;
}

export function getTenant(plan: string): TenantCreds | undefined {
  return loadCredentials().tenants[plan];
}

export function getAnyTenantKey(): string {
  const creds = loadCredentials();
  // Prefer a tenant with higher rate limits to avoid 429 during tests
  const preferred =
    creds.tenants["enterprise"] ||
    creds.tenants["scale"] ||
    creds.tenants["growth"] ||
    creds.tenants["starter"];
  if (preferred) return preferred.api_key;
  const first = Object.values(creds.tenants)[0];
  return first?.api_key ?? "";
}

/** Poll a job until it reaches a terminal status or timeout. */
export async function pollJob(
  request: APIRequestContext,
  jobId: string,
  apiKey: string,
  maxWaitMs = 30_000,
  intervalMs = 1_000,
): Promise<JobResult> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const res = await request.get(`/api/v1/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    const data = (await res.json()) as JobResult;
    if (data.status === "complete" || data.status === "failed") {
      return data;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Job ${jobId} did not complete within ${maxWaitMs}ms`);
}
