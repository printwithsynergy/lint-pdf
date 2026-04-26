/**
 * firebase-admin push helper for the LintPDF mobile companion app.
 *
 * Reads `FIREBASE_SERVICE_ACCOUNT_JSON` (full JSON string of the
 * service-account credentials downloaded from the Firebase Console)
 * on first use and lazy-inits the admin SDK. APNs keys are uploaded
 * to the same Firebase project so a single FCM `send` call reaches
 * both iOS and Android — no separate APNs path is needed here.
 *
 * If the env var is missing the helper throws `PushNotConfiguredError`
 * so callers can decide whether to ignore (e.g., dev environments) or
 * surface as a 500. We deliberately do NOT silently no-op — silent
 * push failures are the worst kind of regression, because users get
 * the email notification but no badge / no in-app banner, and ops
 * has no signal anything is wrong.
 */

import { cert, getApps, initializeApp, type App } from "firebase-admin/app";
import { getMessaging, type Messaging } from "firebase-admin/messaging";

export class PushNotConfiguredError extends Error {
  constructor() {
    super(
      "FIREBASE_SERVICE_ACCOUNT_JSON is not set. Set it on the App service " +
        "to enable mobile push notifications.",
    );
    this.name = "PushNotConfiguredError";
  }
}

const APP_NAME = "lintpdf-mobile";

let cachedApp: App | null = null;
let cachedMessaging: Messaging | null = null;

function getApp(): App {
  if (cachedApp) return cachedApp;

  const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (!raw || raw.trim().length === 0) {
    throw new PushNotConfiguredError();
  }

  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(raw) as Record<string, unknown>;
  } catch (err) {
    throw new Error(
      `FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  }

  // Reuse an existing named app on hot-reload (Next.js dev) so we
  // don't pile up duplicate apps on every import.
  const existing = getApps().find((a) => a.name === APP_NAME);
  if (existing) {
    cachedApp = existing;
    return existing;
  }

  cachedApp = initializeApp(
    {
      credential: cert(parsed as Parameters<typeof cert>[0]),
    },
    APP_NAME,
  );
  return cachedApp;
}

function messaging(): Messaging {
  if (cachedMessaging) return cachedMessaging;
  cachedMessaging = getMessaging(getApp());
  return cachedMessaging;
}

export interface PushPayload {
  /** Short, displayed in the notification heading. */
  title: string;
  /** Longer body text under the title. */
  body: string;
  /**
   * Deep link the app should open when the user taps the
   * notification. Goes into the `data` payload so the mobile shell's
   * notification handler can `router.navigate(linkPath)`.
   */
  linkPath?: string;
  /** Free-form additional data the mobile app may use. */
  data?: Record<string, string>;
}

export interface PushResult {
  pushToken: string;
  ok: boolean;
  /** Set when `ok === false` so callers can decide whether to retry or prune. */
  error?: string;
  /**
   * True when the FCM error indicates the token is permanently
   * invalid (expired, unregistered, mis-formatted). Callers should
   * delete the corresponding `MobileDevice` row.
   */
  invalid?: boolean;
}

const INVALID_TOKEN_CODES = new Set([
  "messaging/invalid-registration-token",
  "messaging/registration-token-not-registered",
  "messaging/invalid-argument",
]);

/**
 * Send a push payload to a list of FCM/APNs registration tokens.
 * Each token is dispatched independently so a single bad token
 * doesn't poison the batch — return value reports per-token status
 * so callers can prune invalid rows.
 */
export async function sendPushToTokens(
  pushTokens: string[],
  payload: PushPayload,
): Promise<PushResult[]> {
  if (pushTokens.length === 0) return [];

  const m = messaging();
  const data: Record<string, string> = { ...(payload.data ?? {}) };
  if (payload.linkPath) data.linkPath = payload.linkPath;

  return Promise.all(
    pushTokens.map(async (token) => {
      try {
        await m.send({
          token,
          notification: {
            title: payload.title,
            body: payload.body,
          },
          data,
        });
        return { pushToken: token, ok: true };
      } catch (err) {
        const code =
          err && typeof err === "object" && "code" in err
            ? String((err as { code: unknown }).code)
            : "";
        const message = err instanceof Error ? err.message : String(err);
        return {
          pushToken: token,
          ok: false,
          error: message,
          invalid: INVALID_TOKEN_CODES.has(code),
        };
      }
    }),
  );
}
