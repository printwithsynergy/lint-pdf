import { describe, it, expect } from "vitest";
import { groundedConfigSchema } from "../config";

describe("groundedConfigSchema", () => {
  it("parses valid config", () => {
    const result = groundedConfigSchema.parse({
      apiUrl: "https://api.grounded.dev",
      webhookSecret: "a-long-enough-secret",
      apiKey: "grd_abc123",
    });
    expect(result.apiUrl).toBe("https://api.grounded.dev");
    expect(result.webhookSecret).toBe("a-long-enough-secret");
    expect(result.apiKey).toBe("grd_abc123");
  });

  it("allows missing apiKey", () => {
    const result = groundedConfigSchema.parse({
      apiUrl: "https://api.grounded.dev",
      webhookSecret: "a-long-enough-secret",
    });
    expect(result.apiKey).toBeUndefined();
  });

  it("rejects invalid URL", () => {
    expect(() =>
      groundedConfigSchema.parse({
        apiUrl: "not-a-url",
        webhookSecret: "a-long-enough-secret",
      }),
    ).toThrow();
  });

  it("rejects short webhook secret", () => {
    expect(() =>
      groundedConfigSchema.parse({
        apiUrl: "https://api.grounded.dev",
        webhookSecret: "short",
      }),
    ).toThrow();
  });
});
