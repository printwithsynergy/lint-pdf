import type { CapturedTenant, TenantLookupResponse } from "./types";
import { getApiBaseUrl } from "./api";

const STORAGE_KEY = "lintpdf.mobile.tenant";

/**
 * Load the captured tenant from localStorage, or null if Onboarding
 * hasn't completed yet. On a Tauri shell this will move to
 * `tauri-plugin-store`; for the web preview we use plain localStorage
 * so the dev experience matches a real install.
 */
export function loadTenant(): CapturedTenant | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CapturedTenant;
    if (!parsed.tenantId || !parsed.name) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveTenant(t: CapturedTenant): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
}

export function clearTenant(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

/**
 * Resolve a free-form tenant identifier (id, slug, domain, or display
 * name) by hitting the public lookup endpoint. Throws on network error
 * and on non-200 responses.
 */
export async function lookupTenant(query: string): Promise<TenantLookupResponse> {
  const url = new URL("/api/public/tenant-lookup", getApiBaseUrl());
  url.searchParams.set("q", query);
  const res = await fetch(url.toString(), { method: "GET" });
  if (res.status === 404) {
    throw new TenantNotFoundError(query);
  }
  if (!res.ok) {
    throw new TenantLookupError(`Lookup failed (HTTP ${res.status})`);
  }
  return (await res.json()) as TenantLookupResponse;
}

export class TenantNotFoundError extends Error {
  constructor(public query: string) {
    super(`Tenant not found for query "${query}"`);
    this.name = "TenantNotFoundError";
  }
}

export class TenantLookupError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TenantLookupError";
  }
}
