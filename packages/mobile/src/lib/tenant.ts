import type { CapturedTenant, TenantLookupResponse } from "./types";
import { getApiBaseUrl } from "./api";
import {
  clearTenant as bridgeClearTenant,
  loadTenant as bridgeLoadTenant,
  saveTenant as bridgeSaveTenant,
} from "./tauri";

/**
 * Storage delegate. The bridge (`./tauri.ts`) decides at runtime
 * whether to use `tauri-plugin-store` (native shell) or
 * localStorage (web preview), so the rest of the app just calls
 * these helpers without thinking about transport.
 */
export const loadTenant = bridgeLoadTenant;
export const saveTenant = bridgeSaveTenant;
export const clearTenant = bridgeClearTenant;

/**
 * Resolve a free-form tenant identifier (id, slug, domain, or display
 * name) by hitting the public lookup endpoint. Throws on network error
 * and on non-200 responses.
 */
export async function lookupTenant(
  query: string,
): Promise<TenantLookupResponse> {
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

/**
 * Capture and persist a tenant lookup result in one step. Used by
 * the Onboarding route after the user picks a tenant.
 */
export async function captureTenant(
  data: TenantLookupResponse,
): Promise<CapturedTenant> {
  const captured: CapturedTenant = {
    tenantId: data.tenantId,
    name: data.name,
    slug: data.slug,
    domain: data.domain,
    branding: data.branding,
    capturedAt: new Date().toISOString(),
  };
  await saveTenant(captured);
  return captured;
}
