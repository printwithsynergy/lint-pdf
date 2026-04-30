/**
 * BoxOverlay — Q7-A snapshot backfill.
 *
 * Renders SVG rect outlines for trim/bleed/crop boxes plus
 * clickable info icons that reveal a per-box mm × inch popover.
 * Pure presentational; no services / context required.
 */

import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { BoxOverlay } from "../../src/core/components/BoxOverlay";
import type { PageInfo } from "../../src/core/types";

const mkPage = (overrides: Partial<PageInfo> = {}): PageInfo => ({
  page_num: 1,
  width_pts: 612,
  height_pts: 792,
  rotation: 0,
  media_box: { x0: 0, y0: 0, x1: 612, y1: 792 },
  trim_box: { x0: 36, y0: 36, x1: 576, y1: 756 },
  bleed_box: { x0: 18, y0: 18, x1: 594, y1: 774 },
  crop_box: { x0: 0, y0: 0, x1: 612, y1: 792 },
  ...overrides,
});

describe("BoxOverlay", () => {
  it("renders trim + bleed + crop SVG outlines + legend", () => {
    const { container } = render(
      <BoxOverlay page={mkPage()} canvasWidth={612} canvasHeight={792} />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("returns null when no boxes are declared", () => {
    const { container } = render(
      <BoxOverlay
        page={mkPage({ trim_box: null, bleed_box: null, crop_box: null })}
        canvasWidth={612}
        canvasHeight={792}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders only the boxes that are present", () => {
    const { container } = render(
      <BoxOverlay
        page={mkPage({ bleed_box: null, crop_box: null })}
        canvasWidth={612}
        canvasHeight={792}
      />,
    );
    // Only "Trim" should appear — bleed + crop excluded.
    const text = container.textContent ?? "";
    expect(text).toContain("Trim");
    expect(text).not.toContain("Bleed");
    expect(text).not.toContain("Crop");
  });

  it("opens a popover with mm + inch sizes when an info icon is clicked", () => {
    const { container, getByLabelText } = render(
      <BoxOverlay
        page={mkPage({ bleed_box: null, crop_box: null })}
        canvasWidth={612}
        canvasHeight={792}
      />,
    );
    fireEvent.click(getByLabelText("Trim size"));
    // Trim is 540 × 720 pt = 190.50 × 254.00 mm = 7.500 × 10.000 in
    const text = container.textContent ?? "";
    expect(text).toContain("190.50 × 254.00 mm");
    expect(text).toContain("7.500 × 10.000 in");
  });

  it("renders dieline-region info icons + popovers for each region", () => {
    const { container, getAllByLabelText } = render(
      <BoxOverlay
        page={mkPage({ bleed_box: null, crop_box: null })}
        canvasWidth={612}
        canvasHeight={792}
        dieline={{
          source: "name",
          polylines: [],
          spot_name: "CutContour",
          confidence: 1.0,
          regions: [
            {
              x0: 50,
              y0: 50,
              x1: 200,
              y1: 200,
              width_mm: 52.92,
              height_mm: 52.92,
            },
            {
              x0: 300,
              y0: 300,
              x1: 500,
              y1: 500,
              width_mm: 70.56,
              height_mm: 70.56,
            },
          ],
        }}
      />,
    );
    // Two dieline icons + the trim icon = 3 info buttons total.
    const dielineButtons = getAllByLabelText(/Dieline \d size/);
    expect(dielineButtons).toHaveLength(2);
    fireEvent.click(dielineButtons[0]!);
    expect(container.textContent).toContain("Dieline 1");
  });

  it("colours dieline icons red when multi_color is true", () => {
    // Keep trim_box so BoxOverlay doesn't short-circuit (the
    // entire component returns null when no page boxes are
    // declared, dieline-region icons included).
    const { getByLabelText } = render(
      <BoxOverlay
        page={mkPage({ bleed_box: null, crop_box: null })}
        canvasWidth={612}
        canvasHeight={792}
        dieline={{
          source: "name",
          polylines: [],
          spot_name: "CutContour",
          confidence: 1.0,
          multi_color: true,
          regions: [
            {
              x0: 50,
              y0: 50,
              x1: 200,
              y1: 200,
              width_mm: 52.92,
              height_mm: 52.92,
            },
          ],
        }}
      />,
    );
    const btn = getByLabelText("Dieline 1 size");
    expect(btn.getAttribute("style")).toContain("rgb(239, 68, 68)"); // #ef4444
  });
});
