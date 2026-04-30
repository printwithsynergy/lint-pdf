/**
 * findingsToOverlayItems / findingToOverlayItem — Phase 2 abstraction.
 *
 * Locks in the adapter contract that subsequent PRs rely on when they
 * migrate `PageCanvas` and `PageNavigator` from
 * `findings: ViewerFinding[]` props to `items: OverlayItem[]`.
 */

import { describe, expect, it } from "vitest";

import {
  findingToOverlayItem,
  findingsToOverlayItems,
} from "../../src/lintpdf/sources/finding-overlay";
import type { ViewerFinding } from "../../src/types";

const sample = (overrides: Partial<ViewerFinding> = {}): ViewerFinding => ({
  inspection_id: "LPDF_TEST_001",
  severity: "error",
  message: "test finding",
  page_num: 1,
  bbox: [10, 20, 30, 40],
  details: {},
  ...overrides,
});

describe("findingToOverlayItem", () => {
  it("maps an error finding to an OverlayItem with tier=error", () => {
    const item = findingToOverlayItem(sample());
    expect(item).not.toBeNull();
    expect(item).toMatchObject({
      page: 1,
      bbox: [10, 20, 30, 40],
      tier: "error",
      label: "test finding",
    });
  });

  it("maps a warning to tier=warning", () => {
    const item = findingToOverlayItem(sample({ severity: "warning" }));
    expect(item?.tier).toBe("warning");
  });

  it("maps an advisory to tier=advisory", () => {
    const item = findingToOverlayItem(sample({ severity: "advisory" }));
    expect(item?.tier).toBe("advisory");
  });

  it("returns null when bbox is missing", () => {
    const item = findingToOverlayItem(sample({ bbox: undefined as any }));
    expect(item).toBeNull();
  });

  it("returns null when page_num is missing or zero", () => {
    expect(findingToOverlayItem(sample({ page_num: 0 }))).toBeNull();
  });

  it("includes the original finding in data for round-trip lookups", () => {
    const f = sample({ inspection_id: "LPDF_FOO_002" });
    const item = findingToOverlayItem(f);
    expect(item?.data?.finding).toBe(f);
    expect(item?.data?.inspection_id).toBe("LPDF_FOO_002");
  });

  it("derives a stable id from inspection_id + page + bbox", () => {
    const item = findingToOverlayItem(sample());
    expect(item?.id).toBe("LPDF_TEST_001:1:10,20,30,40");
  });

  it("truncates labels to 80 chars", () => {
    const longMessage = "x".repeat(120);
    const item = findingToOverlayItem(sample({ message: longMessage }));
    expect(item?.label).toHaveLength(80);
  });
});

describe("findingsToOverlayItems", () => {
  it("filters out unrenderable findings", () => {
    const items = findingsToOverlayItems([
      sample(),
      sample({ bbox: undefined as any }),
      sample({ page_num: 0 }),
      sample({ inspection_id: "LPDF_OK_002" }),
    ]);
    expect(items).toHaveLength(2);
    expect(items[0]?.id).toBe("LPDF_TEST_001:1:10,20,30,40");
    expect(items[1]?.id).toBe("LPDF_OK_002:1:10,20,30,40");
  });

  it("returns an empty array for an empty input", () => {
    expect(findingsToOverlayItems([])).toEqual([]);
  });
});
