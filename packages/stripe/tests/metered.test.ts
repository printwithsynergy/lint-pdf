import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Mock } from "vitest";
import { reportOverageUsage } from "../src/metered.js";

interface MockStripe {
  subscriptionItems: {
    createUsageRecord: Mock;
  };
}

describe("reportOverageUsage", () => {
  let mockStripe: MockStripe;

  beforeEach(() => {
    mockStripe = {
      subscriptionItems: {
        createUsageRecord: vi.fn(),
      },
    };
  });

  it("should call createUsageRecord with correct params", async () => {
    const mockUsageRecord = {
      id: "mbur_123",
      object: "usage_record",
      quantity: 5,
      subscription_item: "si_abc",
      timestamp: 1234567890,
    };
    mockStripe.subscriptionItems.createUsageRecord.mockResolvedValue(
      mockUsageRecord,
    );

    const result = await reportOverageUsage(
      mockStripe,
      "si_abc",
      5,
      1234567890,
    );

    expect(mockStripe.subscriptionItems.createUsageRecord).toHaveBeenCalledWith(
      "si_abc",
      {
        quantity: 5,
        timestamp: 1234567890,
        action: "increment",
      },
    );
    expect(result).toEqual(mockUsageRecord);
  });

  it("should use current timestamp when not provided", async () => {
    mockStripe.subscriptionItems.createUsageRecord.mockResolvedValue({
      id: "mbur_456",
    });

    const before = Math.floor(Date.now() / 1000);
    await reportOverageUsage(mockStripe, "si_abc", 1);
    const after = Math.floor(Date.now() / 1000);

    const call = mockStripe.subscriptionItems.createUsageRecord.mock.calls[0];
    expect(call[0]).toBe("si_abc");
    expect(call[1].quantity).toBe(1);
    expect(call[1].action).toBe("increment");
    expect(call[1].timestamp).toBeGreaterThanOrEqual(before);
    expect(call[1].timestamp).toBeLessThanOrEqual(after);
  });

  it("should pass through the subscription item ID", async () => {
    mockStripe.subscriptionItems.createUsageRecord.mockResolvedValue({
      id: "mbur_789",
    });

    await reportOverageUsage(mockStripe, "si_xyz_999", 10, 1000000);

    expect(mockStripe.subscriptionItems.createUsageRecord).toHaveBeenCalledWith(
      "si_xyz_999",
      expect.objectContaining({ quantity: 10 }),
    );
  });

  it("should return the usage record from Stripe", async () => {
    const expected = {
      id: "mbur_abc",
      object: "usage_record",
      quantity: 42,
      subscription_item: "si_item",
      timestamp: 9999999,
    };
    mockStripe.subscriptionItems.createUsageRecord.mockResolvedValue(expected);

    const result = await reportOverageUsage(mockStripe, "si_item", 42, 9999999);
    expect(result).toBe(expected);
  });

  it("should propagate errors from Stripe API", async () => {
    mockStripe.subscriptionItems.createUsageRecord.mockRejectedValue(
      new Error("Stripe: subscription item not found"),
    );

    await expect(
      reportOverageUsage(mockStripe, "si_invalid", 1, 1000),
    ).rejects.toThrow("Stripe: subscription item not found");
  });

  it("should handle zero quantity", async () => {
    mockStripe.subscriptionItems.createUsageRecord.mockResolvedValue({
      id: "mbur_zero",
    });

    await reportOverageUsage(mockStripe, "si_abc", 0, 1000);

    expect(mockStripe.subscriptionItems.createUsageRecord).toHaveBeenCalledWith(
      "si_abc",
      {
        quantity: 0,
        timestamp: 1000,
        action: "increment",
      },
    );
  });
});
