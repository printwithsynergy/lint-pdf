import { describe, it, expect } from "vitest";
import { createHmac } from "crypto";
import { validateWebhookSignature, parseWebhookEvent } from "../webhook";

describe("validateWebhookSignature", () => {
  const secret = "test-secret-that-is-long-enough";

  it("accepts valid signature", () => {
    const payload = JSON.stringify({
      event: "preflight.complete",
      job_id: "123",
    });
    const sig = createHmac("sha256", secret).update(payload).digest("hex"); // nosemgrep: hardcoded-hmac-key
    expect(validateWebhookSignature(payload, sig, secret)).toBe(true);
  });

  it("rejects invalid signature", () => {
    const payload = JSON.stringify({
      event: "preflight.complete",
      job_id: "123",
    });
    expect(validateWebhookSignature(payload, "invalid", secret)).toBe(false);
  });

  it("rejects tampered payload", () => {
    const payload = JSON.stringify({
      event: "preflight.complete",
      job_id: "123",
    });
    const sig = createHmac("sha256", secret).update(payload).digest("hex"); // nosemgrep: hardcoded-hmac-key
    const tampered = JSON.stringify({
      event: "preflight.complete",
      job_id: "456",
    });
    expect(validateWebhookSignature(tampered, sig, secret)).toBe(false);
  });

  it("rejects wrong secret", () => {
    const payload = JSON.stringify({
      event: "preflight.complete",
      job_id: "123",
    });
    const sig = createHmac("sha256", "wrong-secret-blah-blah")
      .update(payload)
      .digest("hex"); // nosemgrep: hardcoded-hmac-key
    expect(validateWebhookSignature(payload, sig, secret)).toBe(false);
  });
});

describe("parseWebhookEvent", () => {
  it("parses valid event", () => {
    const payload = {
      event: "preflight.complete",
      job_id: "123",
      passed: true,
      badge: "pass",
    };
    const result = parseWebhookEvent(payload);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("preflight.complete");
    expect(result?.job_id).toBe("123");
  });

  it("returns null for missing event", () => {
    expect(parseWebhookEvent({ job_id: "123" })).toBeNull();
  });

  it("returns null for missing job_id", () => {
    expect(parseWebhookEvent({ event: "preflight.complete" })).toBeNull();
  });

  it("returns null for non-object", () => {
    expect(parseWebhookEvent("string")).toBeNull();
    expect(parseWebhookEvent(null)).toBeNull();
    expect(parseWebhookEvent(undefined)).toBeNull(); // skipcq: JS-W1042 — explicitly testing undefined input
  });
});
