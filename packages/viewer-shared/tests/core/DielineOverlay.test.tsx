/**
 * DielineOverlay — Q7-A snapshot backfill.
 *
 * Standalone info-icon overlay for dieline regions. Renders one
 * red `i` chip at the centroid of each region; click to reveal
 * a mm × inch popover. Returns null when no regions present.
 */

import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { DielineOverlay } from "../../src/core/components/DielineOverlay";
import type { DielineResult, PageInfo } from "../../src/core/types";

const mkPage = (): PageInfo => ({
  page_num: 1,
  width_pts: 612,
  height_pts: 792,
  rotation: 0,
  media_box: { x0: 0, y0: 0, x1: 612, y1: 792 },
  trim_box: null,
  bleed_box: null,
  crop_box: null,
});

const mkDieline = (overrides: Partial<DielineResult> = {}): DielineResult => ({
  source: "name",
  polylines: [],
  spot_name: "CutContour",
  confidence: 1.0,
  regions: [
    { x0: 50, y0: 50, x1: 200, y1: 200, width_mm: 52.92, height_mm: 52.92 },
  ],
  ...overrides,
});

describe("DielineOverlay", () => {
  it("returns null when dieline is undefined", () => {
    const { container } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={undefined}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("returns null when dieline.regions is empty", () => {
    const { container } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={mkDieline({ regions: [] })}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders a single icon labeled 'Dieline' for one region", () => {
    const { container, getByLabelText } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={mkDieline()}
      />,
    );
    expect(getByLabelText("Dieline size")).toBeTruthy();
    expect(container.firstChild).toMatchSnapshot();
  });

  it("numbers icons 'Dieline 1', 'Dieline 2' when multiple regions", () => {
    const { getByLabelText } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={mkDieline({
          regions: [
            { x0: 0, y0: 0, x1: 100, y1: 100, width_mm: 35.28, height_mm: 35.28 },
            { x0: 200, y0: 200, x1: 400, y1: 400, width_mm: 70.56, height_mm: 70.56 },
          ],
        })}
      />,
    );
    expect(getByLabelText("Dieline 1 size")).toBeTruthy();
    expect(getByLabelText("Dieline 2 size")).toBeTruthy();
  });

  it("opens a popover with mm + inch sizes when an icon is clicked", () => {
    const { container, getByLabelText } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={mkDieline({
          regions: [
            { x0: 0, y0: 0, x1: 144, y1: 72, width_mm: 50.8, height_mm: 25.4 },
          ],
        })}
      />,
    );
    fireEvent.click(getByLabelText("Dieline size"));
    // 144 × 72 pt = 50.80 × 25.40 mm = 2.000 × 1.000 in
    const text = container.textContent ?? "";
    expect(text).toContain("50.80 × 25.40 mm");
    expect(text).toContain("2.000 × 1.000 in");
  });

  it("renders the multi-colour badge inside the popover when multi_color is true", () => {
    const { container, getByLabelText } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={mkDieline({ multi_color: true })}
      />,
    );
    fireEvent.click(getByLabelText("Dieline size"));
    expect(container.textContent).toContain("multi-colour");
  });

  it("uses red icon colour when multi_color is true", () => {
    const { getByLabelText } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={mkDieline({ multi_color: true })}
      />,
    );
    const btn = getByLabelText("Dieline size");
    expect(btn.getAttribute("style")).toContain("rgb(239, 68, 68)"); // #ef4444
  });

  it("uses default red colour (darker) when multi_color is false", () => {
    const { getByLabelText } = render(
      <DielineOverlay
        page={mkPage()}
        canvasWidth={612}
        canvasHeight={792}
        dieline={mkDieline()}
      />,
    );
    const btn = getByLabelText("Dieline size");
    expect(btn.getAttribute("style")).toContain("rgb(220, 38, 38)"); // #dc2626
  });
});
