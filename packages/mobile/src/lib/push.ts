import { apiFetch } from "./api";
import {
  PushUnsupportedError,
  isTauri,
  registerForPush,
  requestPushPermission,
} from "./tauri";

const REGISTERED_TOKEN_KEY = "lintpdf.mobile.last_registered_push_token";

/**
 * Register the device with the LintPDF backend so the
 * `/api/internal/approval-webhook` fan-out can target it for
 * approval-needed pushes. Idempotent: skips the registration call
 * when the same `(token, tenantId)` pair is already on record in
 * localStorage from a previous launch.
 *
 * Errors are swallowed and logged — push is a nice-to-have, never
 * a blocker for the core approve / view flows. Web preview and
 * desktop builds short-circuit before hitting the platform code.
 */
export async function registerDeviceForPush(tenantId: string): Promise<void> {
  if (!isTauri()) return;

  try {
    const status = await requestPushPermission();
    if (status === "denied") {
      // User chose to opt out. Don't call registerForPush — APNs /
      // FCM still hands back a token but display would be silenced
      // and we'd have a phantom row in MobileDevice.
      return;
    }

    const { token, platform } = await registerForPush();

    // Avoid hammering /api/mobile/devices on every launch when
    // nothing changed. Token rotation is rare on iOS / Android, so
    // a localStorage cache keyed on (tenantId, token) is enough to
    // dedupe — a stale entry just means one extra POST after a
    // re-onboard, which is fine.
    const cacheKey = `${tenantId}:${token}`;
    if (typeof window !== "undefined") {
      const last = window.localStorage.getItem(REGISTERED_TOKEN_KEY);
      if (last === cacheKey) return;
    }

    const res = await apiFetch("/api/mobile/devices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ pushToken: token, platform, tenantId }),
    });

    if (!res.ok) {
      console.warn(
        `Push device registration failed (HTTP ${res.status}). ` +
          "User will still see in-app banners but won't receive remote pushes.",
      );
      return;
    }

    if (typeof window !== "undefined") {
      window.localStorage.setItem(REGISTERED_TOKEN_KEY, cacheKey);
    }
  } catch (err) {
    if (err instanceof PushUnsupportedError) return;
    console.warn("Push registration error:", err);
  }
}

/**
 * Drop the cached registered-token marker so the next call to
 * `registerDeviceForPush` re-POSTs. Used by the Settings → "Change
 * tenant" flow so the new tenant's push fan-out picks up this
 * device immediately.
 */
export function clearPushRegistrationCache(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(REGISTERED_TOKEN_KEY);
  }
}
