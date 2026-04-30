/**
 * ColorPickerTool — Q7-A snapshot backfill.
 *
 * Click-to-sample colour picker. Uses
 * services.colorSample.sampleAt() (PR #341); silent-swallow
 * contract returns null on failure. Tests cover the click → sampleAt
 * call shape + the popover render after a successful sample.
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, waitFor } from "@testing-library/react";

import { ColorPickerTool } from "../../src/core/components/ColorPickerTool";
import { makeStubServices, withServices } from "../_helpers/services";
import type { ColorSample } from "../../src/core/types";

const baseProps = {
  jobId: "job-1",
  pageNum: 1,
  pageWidthPts: 612,
  pageHeightPts: 792,
  canvasWidth: 612,
  canvasHeight: 792,
};

describe("ColorPickerTool", () => {
  it("renders the empty pick area as the initial state", () => {
    const services = makeStubServices();
    const { container } = render(
      withServices(<ColorPickerTool {...baseProps} />, services),
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("calls services.colorSample.sampleAt on click with PDF coordinates", async () => {
    const sampleAt = vi.fn(async () => null);
    const services = makeStubServices({ colorSample: { sampleAt } });
    const { container } = render(
      withServices(<ColorPickerTool {...baseProps} />, services),
    );
    const overlay = container.firstChild as HTMLElement;
    // jsdom getBoundingClientRect returns zeros; clientX/clientY are
    // therefore the PDF-coord values directly. Pass 100,200 →
    // expects pdfX=100, pdfY=792-200=592.
    fireEvent.click(overlay, { clientX: 100, clientY: 200 });
    await waitFor(() =>
      expect(sampleAt).toHaveBeenCalledWith({
        pageNum: 1,
        pdfX: 100,
        pdfY: 592,
      }),
    );
  });

  it("renders the colour popover after a successful sample", async () => {
    const sample: ColorSample = {
      x: 100,
      y: 200,
      rgb: [0, 183, 235],
      hex: "#00b7eb",
      tac: 65.4,
    };
    const sampleAt = vi.fn(async () => sample);
    const services = makeStubServices({ colorSample: { sampleAt } });
    const { container, findByText } = render(
      withServices(<ColorPickerTool {...baseProps} />, services),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 100,
      clientY: 200,
    });
    await findByText("#00B7EB"); // hex uppercased in render
    expect(container.textContent).toContain("RGB: 0, 183, 235");
    expect(container.textContent).toContain("TAC: 65.4%");
  });

  it("does not render a popover when sampleAt returns null", async () => {
    const sampleAt = vi.fn(async () => null);
    const services = makeStubServices({ colorSample: { sampleAt } });
    const { container } = render(
      withServices(<ColorPickerTool {...baseProps} />, services),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 100,
      clientY: 200,
    });
    await waitFor(() => expect(sampleAt).toHaveBeenCalled());
    // Crosshair indicator is present (position set), but no hex
    // popover — presence check via a class that only appears in
    // the popover.
    expect(container.querySelector(".bg-black\\/90")).toBeNull();
  });
});
