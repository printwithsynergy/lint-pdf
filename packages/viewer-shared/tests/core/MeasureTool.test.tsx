/**
 * MeasureTool — Q7-A snapshot backfill.
 *
 * Click-and-drag distance ruler with pluggable units (mm/in/pt by
 * default). Measurement-unit math has its own coverage in
 * tests/core/measurement-units.test.ts; this file covers the
 * component wrapper + the readout-format integration with units.
 */

import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { MeasureTool } from "../../src/core/components/MeasureTool";
import { allMeasurementUnits } from "../../src/core/units";

const baseProps = {
  pageWidthPts: 612,
  pageHeightPts: 792,
  canvasWidth: 612,
  canvasHeight: 792,
};

describe("MeasureTool", () => {
  it("renders the empty drag-hint state on first render", () => {
    const { container } = render(<MeasureTool {...baseProps} />);
    expect(container.firstChild).toMatchSnapshot();
    // Hint text is "Click and drag" or "Tap and drag" depending on
    // touch-detection in the runtime; jsdom's environment trips the
    // touch path so accept either.
    expect(container.textContent).toMatch(/(Click|Tap) and drag/i);
  });

  it("renders a measurement readout after a click + drag (default mm/in/pt)", () => {
    const { container } = render(<MeasureTool {...baseProps} />);
    const overlay = container.firstChild as HTMLElement;
    // jsdom getBoundingClientRect returns zeros so client coords ≡
    // canvas-pixel coords. Drag from (0,0) to (72, 0) → 72 px = 72
    // pt = 25.4 mm = 1.000 in.
    fireEvent.mouseDown(overlay, { clientX: 0, clientY: 0 });
    fireEvent.mouseMove(overlay, { clientX: 72, clientY: 0 });
    fireEvent.mouseUp(overlay);
    const text = container.textContent ?? "";
    expect(text).toContain("25.4 mm");
    expect(text).toContain("1 in"); // 1.000 rounds to 1
    expect(text).toContain("72 pt");
  });

  it("uses all 5 units when units={allMeasurementUnits}", () => {
    const { container } = render(
      <MeasureTool {...baseProps} units={allMeasurementUnits} />,
    );
    const overlay = container.firstChild as HTMLElement;
    // 72 pt drag → 25.4 mm · 1 in · 72 pt · 6 pc · 13.09 ag
    fireEvent.mouseDown(overlay, { clientX: 0, clientY: 0 });
    fireEvent.mouseMove(overlay, { clientX: 72, clientY: 0 });
    fireEvent.mouseUp(overlay);
    const text = container.textContent ?? "";
    expect(text).toContain("25.4 mm");
    expect(text).toContain("1 in");
    expect(text).toContain("72 pt");
    expect(text).toContain("6 pc");
    expect(text).toContain("13.09 ag");
  });

  it("rounds inches to 3 decimals (small fractions matter visually)", () => {
    const { container } = render(<MeasureTool {...baseProps} />);
    const overlay = container.firstChild as HTMLElement;
    // 36 pt = 0.5 in exactly. Need to test a fractional case:
    // 50 pt = 17.6388... mm = 0.69444... in. Round to 3 dec = 0.694.
    fireEvent.mouseDown(overlay, { clientX: 0, clientY: 0 });
    fireEvent.mouseMove(overlay, { clientX: 50, clientY: 0 });
    fireEvent.mouseUp(overlay);
    expect(container.textContent).toContain("0.694 in");
  });

  it("returns null measurement when mouseUp fires without prior mouseDown", () => {
    const { container } = render(<MeasureTool {...baseProps} />);
    const overlay = container.firstChild as HTMLElement;
    // Just mouseUp without down/move — no measurement should appear.
    fireEvent.mouseUp(overlay);
    expect(container.textContent ?? "").not.toMatch(/\d+\s+(mm|in|pt)/);
  });
});
