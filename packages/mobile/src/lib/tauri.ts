/**
 * Tauri 2 bridge. The mobile package runs in two modes:
 *
 *   1. Web preview (`pnpm dev`) — `window.__TAURI_INTERNALS__` is
 *      undefined; calls fall back to localStorage. This keeps the
 *      dev loop fast and keeps the JS code testable without a
 *      simulator running.
 *   2. Native shell (`tauri ios dev` / `tauri android dev`) —
 *      `invoke()` round-trips to the Rust commands in
 *      `src-tauri/src/lib.rs`, which persist via
 *      `tauri-plugin-store` (sandboxed, OS-encrypted at rest).
 *
 * `isTauri()` is the single source of truth — every helper below
 * branches on it so the rest of the app never has to think about
 * which mode it's in.
 */

import type { CapturedTenant } from "./types";

const LS_TENANT_KEY = "lintpdf.mobile.tenant";
const LS_API_KEY = "lintpdf.mobile.api_key";

interface TauriInternals {
  invoke?: (...args: unknown[]) => unknown;
}

interface TauriWindow {
  __TAURI_INTERNALS__?: TauriInternals;
}

export function isTauri(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as unknown as TauriWindow;
  return Boolean(w.__TAURI_INTERNALS__);
}

async function tauriInvoke<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  // Lazy-import @tauri-apps/api so the web preview bundle doesn't
  // pay the import cost when isTauri() is false.
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(cmd, args);
}

export async function getPlatform(): Promise<string> {
  if (!isTauri()) return "web";
  return tauriInvoke<string>("get_platform");
}

// ── Tenant persistence ─────────────────────────────────────────────

interface RustCapturedTenant {
  tenant_id: string;
  name: string;
  slug: string;
  domain: string | null;
  branding: unknown;
  captured_at: string;
}

function toRust(t: CapturedTenant): RustCapturedTenant {
  return {
    tenant_id: t.tenantId,
    name: t.name,
    slug: t.slug,
    domain: t.domain,
    branding: t.branding,
    captured_at: t.capturedAt,
  };
}

function fromRust(t: RustCapturedTenant | null): CapturedTenant | null {
  if (!t) return null;
  return {
    tenantId: t.tenant_id,
    name: t.name,
    slug: t.slug,
    domain: t.domain,
    branding: (t.branding ?? {}) as CapturedTenant["branding"],
    capturedAt: t.captured_at,
  };
}

export async function loadTenant(): Promise<CapturedTenant | null> {
  if (isTauri()) {
    const rust = await tauriInvoke<RustCapturedTenant | null>("get_tenant");
    return fromRust(rust);
  }
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LS_TENANT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CapturedTenant;
    if (!parsed.tenantId || !parsed.name) return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function saveTenant(t: CapturedTenant): Promise<void> {
  if (isTauri()) {
    await tauriInvoke<void>("set_tenant", { tenant: toRust(t) });
    return;
  }
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LS_TENANT_KEY, JSON.stringify(t));
}

export async function clearTenant(): Promise<void> {
  if (isTauri()) {
    await tauriInvoke<void>("clear_tenant");
    return;
  }
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LS_TENANT_KEY);
  window.localStorage.removeItem(LS_API_KEY);
}

// ── API key ────────────────────────────────────────────────────────

export async function getApiKey(): Promise<string | null> {
  if (isTauri()) {
    return tauriInvoke<string | null>("get_api_key");
  }
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(LS_API_KEY);
}

export async function setApiKey(key: string): Promise<void> {
  if (isTauri()) {
    await tauriInvoke<void>("set_api_key", { apiKey: key });
    return;
  }
  if (typeof window === "undefined") return;
  if (!key) {
    window.localStorage.removeItem(LS_API_KEY);
  } else {
    window.localStorage.setItem(LS_API_KEY, key);
  }
}

// ── Push registration ──────────────────────────────────────────────

export type PermissionStatus = "granted" | "denied" | "provisional";

export interface PushTokenResponse {
  token: string;
  platform: "ios" | "android";
}

/**
 * Prompt the user for permission to display push notifications.
 * iOS shows the standard system prompt; Android 13+ shows the
 * runtime POST_NOTIFICATIONS prompt; older Android short-circuits
 * to "granted". Web preview and desktop builds throw an
 * `unsupported` error which `registerForPushIfPossible` swallows.
 */
export async function requestPushPermission(): Promise<PermissionStatus> {
  if (!isTauri()) throw new PushUnsupportedError();
  const r = await tauriInvoke<{ status: PermissionStatus }>(
    "plugin:lintpdf-push|request_permission",
  );
  return r.status;
}

/**
 * Register with FCM (Android) / APNs (iOS) and resolve with the
 * device token. Should be called after `requestPushPermission`
 * returned `granted` or `provisional`. Throws on desktop / web.
 */
export async function registerForPush(): Promise<PushTokenResponse> {
  if (!isTauri()) throw new PushUnsupportedError();
  return tauriInvoke<PushTokenResponse>(
    "plugin:lintpdf-push|register_for_push",
  );
}

export class PushUnsupportedError extends Error {
  constructor() {
    super("Push notifications are not supported on this platform.");
    this.name = "PushUnsupportedError";
  }
}

// ── Deep-link routing ──────────────────────────────────────────────

export type DeepLinkHandler = (path: string) => void;

/**
 * Register a listener for deep-link events. The native shell receives
 * universal-link / App Link taps via `tauri-plugin-deep-link`; we
 * normalize the absolute URL to a path string so the React router
 * can `navigate(path)` without re-parsing.
 *
 * In web preview this is a no-op — the browser already handles
 * `https://app.lintpdf.com/view/{token}` links via standard
 * navigation.
 */
export async function onDeepLink(
  handler: DeepLinkHandler,
): Promise<() => void> {
  if (!isTauri()) return () => {};

  const { onOpenUrl } = await import("@tauri-apps/plugin-deep-link");
  const unlisten = await onOpenUrl((urls: string[]) => {
    for (const url of urls) {
      const path = absoluteToPath(url);
      if (path) handler(path);
    }
  });
  return unlisten;
}

function absoluteToPath(url: string): string | null {
  try {
    const parsed = new URL(url);
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    // Custom-scheme deep links (`lintpdf://...`) on the desktop side
    // arrive without a host — strip the scheme and treat what's left
    // as a path so `lintpdf:///view/abc` still routes to /view/abc.
    const idx = url.indexOf("://");
    if (idx >= 0) {
      const tail = url.slice(idx + 3);
      const slash = tail.indexOf("/");
      return slash >= 0 ? tail.slice(slash) : `/${tail}`;
    }
    return null;
  }
}
