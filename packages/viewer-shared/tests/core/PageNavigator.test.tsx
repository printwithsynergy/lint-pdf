/**
 * PageNavigator — Phase 2 OverlayItem migration snapshot.
 *
 * Locks in the rendered DOM after PageNavigator's prop swap from
 * `findings: ViewerFinding[]` → `items: OverlayItem[]`. The
 * per-page error/warning badge counts are derived from the
 * generic `tier` field (was `severity`); the snapshot proves the
 * visible output is identical pre/post-migration.
 *
 * The component reads `apiBase` from `ViewerApiContext` to build
 * thumbnail URLs — tests wrap with a stub provider so the URL is
 * deterministic.
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { PageNavigator } from "../../src/core/components/PageNavigator";
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

const mkPage = (n: number): PageInfo => ({
  page_num: n,
  width_pts: 612,
  height_pts: 792,
  media_box: { x0: 0, y0: 0, x1: 612, y1: 792 },
});

const mkItem = (overrides: Partial<OverlayItem> & { page: number }): OverlayItem => ({
  id: `item-${overrides.page}-${overrides.tier ?? "neutral"}`,
  page: overrides.page,
  bbox: [0, 0, 100, 100],
  ...overrides,
});

describe("PageNavigator", () => {
  it("renders the vertical list with page count header", () => {
    const { container } = render(
      wrap(
        <PageNavigator
          pages={[mkPage(1), mkPage(2), mkPage(3)]}
          currentPage={1}
          items={[]}
          onPageChange={() => {}}
        />,
      ),
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders the horizontal strip without page count header", () => {
    // Horizontal mode renders a fragment of <button>s with no wrapper,
    // so snapshot the whole container to capture every page tile.
    const { container } = render(
      wrap(
        <PageNavigator
          pages={[mkPage(1), mkPage(2)]}
          currentPage={2}
          items={[]}
          onPageChange={() => {}}
          horizontal
        />,
      ),
    );
    expect(container).toMatchSnapshot();
  });

  it("shows error + warning badge counts derived from item.tier", () => {
    const items: OverlayItem[] = [
      mkItem({ page: 1, tier: "error" }),
      mkItem({ page: 1, tier: "error", id: "item-1-error-2" }),
      mkItem({ page: 1, tier: "warning" }),
      mkItem({ page: 2, tier: "warning" }),
      mkItem({ page: 2, tier: "advisory" }), // not counted
      mkItem({ page: 3, tier: "info" }), // not counted
    ];
    const { container } = render(
      wrap(
        <PageNavigator
          pages={[mkPage(1), mkPage(2), mkPage(3)]}
          currentPage={1}
          items={items}
          onPageChange={() => {}}
        />,
      ),
    );
    const errorBadges = container.querySelectorAll(".bg-destructive");
    const warningBadges = container.querySelectorAll(".bg-warning");
    expect(errorBadges).toHaveLength(1); // only page 1
    expect(errorBadges[0]?.textContent).toBe("2");
    expect(warningBadges).toHaveLength(2); // pages 1 + 2
    expect(Array.from(warningBadges, (b) => b.textContent)).toEqual(["1", "1"]);
  });

  it("ignores items without a page number", () => {
    const items: OverlayItem[] = [
      // page 0 / undefined -> ignored
      { id: "stray", page: 0, bbox: [0, 0, 1, 1], tier: "error" },
    ];
    const { container } = render(
      wrap(
        <PageNavigator
          pages={[mkPage(1)]}
          currentPage={1}
          items={items}
          onPageChange={() => {}}
        />,
      ),
    );
    // No badges should render
    expect(container.querySelector(".bg-destructive")).toBeNull();
    expect(container.querySelector(".bg-warning")).toBeNull();
  });

  it("calls onPageChange with the clicked page number", () => {
    const onPageChange = vi.fn();
    const { getByAltText } = render(
      wrap(
        <PageNavigator
          pages={[mkPage(1), mkPage(2)]}
          currentPage={1}
          items={[]}
          onPageChange={onPageChange}
        />,
      ),
    );
    fireEvent.click(getByAltText("Page 2"));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("builds thumbnail URLs through the ViewerServices.pageImages adapter", () => {
    const { getByAltText } = render(
      wrap(
        <PageNavigator
          pages={[mkPage(1)]}
          currentPage={1}
          items={[]}
          onPageChange={() => {}}
        />,
      ),
    );
    const img = getByAltText("Page 1") as HTMLImageElement;
    expect(img.src).toContain("/api/test/pages/1/tile?dpi=");
  });
});
