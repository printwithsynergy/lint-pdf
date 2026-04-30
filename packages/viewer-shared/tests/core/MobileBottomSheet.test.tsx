/**
 * MobileBottomSheet — Q7-A snapshot backfill.
 *
 * Touch-drag snap-position bottom sheet with 3 positions:
 * collapsed, half, full. Tests focus on the controlled-snap
 * rendering and the onSnapChange wiring; touch-drag pixel math
 * isn't reliably testable in jsdom (no real touch events,
 * ResizeObserver returns the stub).
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { MobileBottomSheet } from "../../src/core/components/MobileBottomSheet";

describe("MobileBottomSheet", () => {
  it("renders with the default collapsed snap position", () => {
    const { container } = render(
      <MobileBottomSheet summary={<span>Summary</span>}>
        <div>Body content</div>
      </MobileBottomSheet>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders with the controlled half snap position", () => {
    const { container } = render(
      <MobileBottomSheet
        summary={<span>Summary</span>}
        snap="half"
      >
        <div>Body content</div>
      </MobileBottomSheet>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders with the controlled full snap position", () => {
    const { container } = render(
      <MobileBottomSheet
        summary={<span>Summary</span>}
        snap="full"
      >
        <div>Body content</div>
      </MobileBottomSheet>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders the summary node in every snap position", () => {
    for (const snap of ["collapsed", "half", "full"] as const) {
      const { getByText, unmount } = render(
        <MobileBottomSheet snap={snap} summary={<span>Find me</span>}>
          <div>Body</div>
        </MobileBottomSheet>,
      );
      expect(getByText("Find me")).toBeTruthy();
      unmount();
    }
  });

  it("renders body content in half + full positions", () => {
    for (const snap of ["half", "full"] as const) {
      const { getByText, unmount } = render(
        <MobileBottomSheet snap={snap} summary={<span>Summary</span>}>
          <div>Body content here</div>
        </MobileBottomSheet>,
      );
      expect(getByText("Body content here")).toBeTruthy();
      unmount();
    }
  });

  it("does not call onSnapChange on render alone (sanity)", () => {
    const onSnapChange = vi.fn();
    render(
      <MobileBottomSheet
        summary={<span>Summary</span>}
        snap="collapsed"
        onSnapChange={onSnapChange}
      >
        <div>Body</div>
      </MobileBottomSheet>,
    );
    // Snap-position changes are touch-drag-driven; jsdom doesn't
    // synthesize touch events reliably so the actual drag behaviour
    // is exercised manually + via Playwright at the consumer route.
    // This test just guards against accidental controlled-render
    // re-emissions.
    expect(onSnapChange).not.toHaveBeenCalled();
  });
});
