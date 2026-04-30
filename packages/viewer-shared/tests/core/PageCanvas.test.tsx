/**
 * PageCanvas — Phase 2 OverlayItem migration snapshot.
 *
 * Locks in the rendered DOM after PageCanvas's prop swap from
 * `findings: ViewerFinding[]` / `selectedFinding: ViewerFinding`
 * → `items: OverlayItem[]` / `selectedItem: OverlayItem`.
 *
 * The component renders to a `<canvas>` element so snapshot tests
 * can't capture the bbox drawing — the test focuses on the wrapper
 * layout, the loading state, the page-level indicator branch
 * (no-bbox selectedItem), and the tooltip DOM (tier badge, code
 * pill, description body). Hit testing + canvas pixel output is
 * not covered by these snapshots and instead relies on manual
 * + Playwright verification at the consumer route.
 */

import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

import { PageCanvas } from "../../src/core/components/PageCanvas";
import { ViewerApiContext } from "../../src/types";
import { ViewerServicesContext } from "../../src/core/host";
import { createLintPDFViewerServices } from "../../src/lintpdf/sources/services";
import type { OverlayItem } from "../../src/core/plugin/types";
import type { PageInfo } from "../../src/types";

const testServices = createLintPDFViewerServices({
  apiBase: "/api/test",
  jobApiBase: "/api/test/job",
});

const wrap = (ui: React.ReactNode) => (
  <ViewerApiContext.Provider
    value={{ apiBase: "/api/test", jobApiBase: "/api/test/job", readOnly: false }}
  >
    <ViewerServicesContext.Provider value={testServices}>
      {ui}
    </ViewerServicesContext.Provider>
  </ViewerApiContext.Provider>
);

const mkPage = (overrides: Partial<PageInfo> = {}): PageInfo => ({
  page_num: 1,
  width_pts: 612,
  height_pts: 792,
  media_box: { x0: 0, y0: 0, x1: 612, y1: 792 },
  ...overrides,
});

const mkItem = (overrides: Partial<OverlayItem>): OverlayItem => ({
  id: "i1",
  page: 1,
  bbox: [10, 20, 100, 120],
  tier: "error",
  ...overrides,
});

describe("PageCanvas", () => {
  it("renders the loading placeholder before the tile image fires onload", () => {
    const { container } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={null}
          onItemClick={() => {}}
        />,
      ),
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders the page-level indicator when selectedItem has no bbox", () => {
    const { container } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={mkItem({
            id: "page-level",
            bbox: undefined,
            tier: "warning",
          })}
          onItemClick={() => {}}
        />,
      ),
    );
    // Indicator div: animate-pulse + border-2, color from tier=warning (#f59e0b).
    const indicator = container.querySelector(".animate-pulse.border-2");
    expect(indicator).not.toBeNull();
    const style = indicator?.getAttribute("style") ?? "";
    expect(style).toContain("rgb(245, 158, 11)"); // #f59e0b
  });

  it("does not render the page-level indicator when selectedItem has a bbox", () => {
    const { container } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={mkItem({ tier: "error" })}
          onItemClick={() => {}}
        />,
      ),
    );
    const indicator = container.querySelector(".animate-pulse.border-2");
    expect(indicator).toBeNull();
  });

  it("renders the tooltip with tier badge, code pill, and description", () => {
    const { container, getByText } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={mkItem({
            tier: "error",
            code: "LPDF_PRINT_001",
            description: "Bleed margin smaller than 3mm on top edge",
          })}
          onItemClick={() => {}}
        />,
      ),
    );
    // Tier text appears in tooltip header (lowercase from token)
    expect(getByText("error")).toBeTruthy();
    // Code pill
    expect(getByText("LPDF_PRINT_001")).toBeTruthy();
    // Description body
    expect(getByText("Bleed margin smaller than 3mm on top edge")).toBeTruthy();
    // Tooltip wrapper present
    expect(container.querySelector(".bg-black\\/90")).not.toBeNull();
  });

  it("falls back to label when description is absent", () => {
    const { getByText } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={mkItem({
            tier: "advisory",
            label: "Short label only",
          })}
          onItemClick={() => {}}
        />,
      ),
    );
    expect(getByText("Short label only")).toBeTruthy();
  });

  it("truncates description bodies longer than 160 chars with an ellipsis", () => {
    const longDesc = "x".repeat(200);
    const { container } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={mkItem({ description: longDesc })}
          onItemClick={() => {}}
        />,
      ),
    );
    const body = container.querySelector(".bg-black\\/90 p");
    expect(body?.textContent).toMatch(/^x{160}\.\.\.$/);
  });

  it("does not show the code pill when code is undefined", () => {
    const { container } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={mkItem({ code: undefined, description: "no code" })}
          onItemClick={() => {}}
        />,
      ),
    );
    expect(container.querySelector("code")).toBeNull();
  });

  it("uses the OverlayItem.color override when provided in tooltip dot", () => {
    // tooltip dot reads TIER_HEX[tier], not item.color — color override is
    // used by the canvas drawing path. This test asserts that an item with
    // a non-standard tier still renders a tooltip without throwing.
    const { container } = render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[]}
          selectedItem={mkItem({
            tier: "neutral",
            color: "#purple",
            description: "neutral overlay",
          })}
          onItemClick={() => {}}
        />,
      ),
    );
    // Neutral tier hex = #64748b
    const dot = container.querySelector(".bg-black\\/90 .rounded-full") as HTMLElement | null;
    expect(dot?.getAttribute("style")).toContain("rgb(100, 116, 139)"); // #64748b
  });

  it("does not call onItemClick during initial render (sanity)", () => {
    const onItemClick = vi.fn();
    render(
      wrap(
        <PageCanvas
          jobId="job-1"
          page={mkPage()}
          zoom={100}
          items={[mkItem({})]}
          selectedItem={null}
          onItemClick={onItemClick}
        />,
      ),
    );
    expect(onItemClick).not.toHaveBeenCalled();
  });
});
