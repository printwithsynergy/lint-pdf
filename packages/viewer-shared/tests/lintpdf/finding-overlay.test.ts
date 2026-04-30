/**
 * findingsToOverlayItems / findingToOverlayItem — Phase 2 abstraction.
 *
 * Locks in the adapter contract that PageCanvas + PageNavigator depend
 * on. The Phase-2 PageCanvas migration extended OverlayItem with
 * `description`, `code`, and an optional `bbox` (so page-level
 * findings still produce an item that the renderer can show via a
 * page-level indicator).
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
      code: "LPDF_TEST_001",
      label: "test finding",
      description: "test finding",
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

  it("still returns an OverlayItem when bbox is missing (page-level finding)", () => {
    const item = findingToOverlayItem(sample({ bbox: undefined as any }));
    expect(item).not.toBeNull();
    expect(item?.bbox).toBeUndefined();
    expect(item?.id).toBe("LPDF_TEST_001:1");
    expect(item?.tier).toBe("error");
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

  it("truncates labels to 80 chars but keeps full description", () => {
    const longMessage = "x".repeat(120);
    const item = findingToOverlayItem(sample({ message: longMessage }));
    expect(item?.label).toHaveLength(80);
    expect(item?.description).toHaveLength(120);
  });

  it("strips long PDF object references from description + label", () => {
    const item = findingToOverlayItem(
      sample({
        message:
          "Form 'FormXob.6b8351906abcdef0123456789abcdef0' missing /BBox",
      }),
    );
    // Object reference 'FormXob.6b835...' stripped, runs of whitespace
    // collapsed back to a single space.
    expect(item?.description).toBe("Form missing /BBox");
    expect(item?.label).toBe("Form missing /BBox");
  });

  it("populates code from inspection_id", () => {
    const item = findingToOverlayItem(sample({ inspection_id: "LPDF_PRINT_BLEED" }));
    expect(item?.code).toBe("LPDF_PRINT_BLEED");
  });
});

describe("findingsToOverlayItems", () => {
  it("filters out only findings with no page_num — bbox-less still flow through", () => {
    const items = findingsToOverlayItems([
      sample(),
      sample({ bbox: undefined as any, inspection_id: "LPDF_PAGE_LEVEL" }),
      sample({ page_num: 0 }),
      sample({ inspection_id: "LPDF_OK_002" }),
    ]);
    expect(items).toHaveLength(3);
    expect(items[0]?.id).toBe("LPDF_TEST_001:1:10,20,30,40");
    expect(items[1]?.id).toBe("LPDF_PAGE_LEVEL:1");
    expect(items[1]?.bbox).toBeUndefined();
    expect(items[2]?.id).toBe("LPDF_OK_002:1:10,20,30,40");
  });

  it("returns an empty array for an empty input", () => {
    expect(findingsToOverlayItems([])).toEqual([]);
  });
});
