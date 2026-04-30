/**
 * DensitometerTool — Q7-A snapshot backfill.
 *
 * Click-to-sample CMYK densitometer. Uses
 * services.densitometer.sampleAt() (PR #341); throws Error with a
 * user-facing message on failure. Tests cover the click → sampleAt
 * call shape, the readout popover on success, and the error banner
 * for "no separations" / "Sampling failed" / "Network error".
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { DensitometerTool } from "../../src/core/components/DensitometerTool";
import { makeStubServices, withServices } from "../_helpers/services";
import type { DensitometerSample } from "../../src/core/types";

const baseProps = {
  jobId: "job-1",
  pageNum: 1,
  pageWidthPts: 612,
  pageHeightPts: 792,
  canvasWidth: 612,
  canvasHeight: 792,
};

describe("DensitometerTool", () => {
  it("renders the empty pick area as the initial state", () => {
    const services = makeStubServices();
    const { container } = render(
      withServices(<DensitometerTool {...baseProps} />, services),
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("calls services.densitometer.sampleAt with PDF coords + tacLimit on click", async () => {
    const sampleAt = vi.fn(async () => {
      throw new Error("No separations available for this page.");
    });
    const services = makeStubServices({ densitometer: { sampleAt } });
    const { container, findByText } = render(
      withServices(<DensitometerTool {...baseProps} />, services),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 100,
      clientY: 200,
    });
    await findByText(/no separations available/i);
    expect(sampleAt).toHaveBeenCalledWith({
      pageNum: 1,
      pdfX: 100,
      pdfY: 592,
      tacLimit: 300, // default
    });
  });

  it("honors a custom tacLimit", async () => {
    const sampleAt = vi.fn(async () => {
      throw new Error("nope");
    });
    const services = makeStubServices({ densitometer: { sampleAt } });
    const { container, findByText } = render(
      withServices(
        <DensitometerTool {...baseProps} tacLimit={280} />,
        services,
      ),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 100,
      clientY: 200,
    });
    await findByText("nope");
    expect(sampleAt).toHaveBeenCalledWith(
      expect.objectContaining({ tacLimit: 280 }),
    );
  });

  it("renders the readout (channels + TAC) on a successful sample", async () => {
    const sample: DensitometerSample = {
      x: 100,
      y: 200,
      dpi: 300,
      channels: [
        { name: "Cyan", percent: 62.3 },
        { name: "Magenta", percent: 18.1 },
        { name: "Yellow", percent: 4.7 },
        { name: "Black", percent: 91.5 },
      ],
      tac: 176.6,
      tac_limit: 300,
      limit_exceeded: false,
    };
    const sampleAt = vi.fn(async () => sample);
    const services = makeStubServices({ densitometer: { sampleAt } });
    const { container, findByText } = render(
      withServices(<DensitometerTool {...baseProps} />, services),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 100,
      clientY: 200,
    });
    await findByText("Densitometer");
    expect(container.textContent).toContain("62.3%");
    expect(container.textContent).toContain("91.5%");
    expect(container.textContent).toContain("176.6%");
    expect(container.textContent).toContain("under 300% limit");
  });

  it("flags TAC over the limit in red", async () => {
    const sample: DensitometerSample = {
      x: 0,
      y: 0,
      dpi: 300,
      channels: [{ name: "Cyan", percent: 100 }],
      tac: 320,
      tac_limit: 300,
      limit_exceeded: true,
    };
    const sampleAt = vi.fn(async () => sample);
    const services = makeStubServices({ densitometer: { sampleAt } });
    const { container, findByText } = render(
      withServices(<DensitometerTool {...baseProps} />, services),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 0,
      clientY: 0,
    });
    await findByText("over 300% limit");
    expect(container.textContent).toContain("320.0%");
  });

  it("renders a 'Sampling failed (NNN)' banner on non-422 server error", async () => {
    const sampleAt = vi.fn(async () => {
      throw new Error("Sampling failed (503)");
    });
    const services = makeStubServices({ densitometer: { sampleAt } });
    const { container, findByText } = render(
      withServices(<DensitometerTool {...baseProps} />, services),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 100,
      clientY: 200,
    });
    await findByText("Sampling failed (503)");
  });

  it("renders 'Network error' on rejection", async () => {
    const sampleAt = vi.fn(async () => {
      throw new Error("Network error");
    });
    const services = makeStubServices({ densitometer: { sampleAt } });
    const { container, findByText } = render(
      withServices(<DensitometerTool {...baseProps} />, services),
    );
    fireEvent.click(container.firstChild as HTMLElement, {
      clientX: 100,
      clientY: 200,
    });
    await findByText("Network error");
  });
});
