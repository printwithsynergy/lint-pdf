/**
 * Webhook signature validation for Grounded events.
 */

import { createHmac } from "crypto";
import type { PixieDustPayload } from "./types";

export function validateWebhookSignature(
  payload: string,
  signature: string,
  secret: string,
): boolean {
  const expected = createHmac("sha256", secret).update(payload).digest("hex");
  if (expected.length !== signature.length) return false;
  let result = 0;
  for (let i = 0; i < expected.length; i++) {
    result |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
  }
  return result === 0;
}

export function parseWebhookEvent(body: unknown): PixieDustPayload | null {
  if (
    typeof body === "object" &&
    body !== null &&
    "event" in body &&
    "job_id" in body
  ) {
    return body as PixieDustPayload;
  }
  return null;
}
