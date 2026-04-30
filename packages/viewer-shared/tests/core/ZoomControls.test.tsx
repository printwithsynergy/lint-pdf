/**
 * ZoomControls — Phase 2 smoke snapshot.
 *
 * First test under tests/core/. Establishes the snapshot pattern future
 * core-component PRs will follow: render the component, snapshot the
 * resulting DOM tree, exercise one user interaction, snapshot again.
 *
 * Phase 2 follow-ups will move ZoomControls (and the other 15 pure-core
 * components) into src/core/components/. This snapshot survives the
 * move because the import path here uses the legacy flat barrel; the
 * test still locks in the pre-move output so the move PR can verify
 * the snapshot stays identical.
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { ZoomControls } from "../../src/core/components/ZoomControls";

describe("ZoomControls", () => {
  it("renders default mode at 100%", () => {
    const { container } = render(
      <ZoomControls zoom={100} onZoomChange={() => {}} />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders compact mode at 100%", () => {
    const { container } = render(
      <ZoomControls zoom={100} onZoomChange={() => {}} compact />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders compact dark mode at 75%", () => {
    const { container } = render(
      <ZoomControls zoom={75} onZoomChange={() => {}} compact dark />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("disables the minus button at the lowest zoom step (25)", () => {
    const { getByTitle } = render(
      <ZoomControls zoom={25} onZoomChange={() => {}} />,
    );
    expect(getByTitle("Zoom out")).toBeDisabled();
    expect(getByTitle("Zoom in")).not.toBeDisabled();
  });

  it("disables the plus button at the highest zoom step (400)", () => {
    const { getByTitle } = render(
      <ZoomControls zoom={400} onZoomChange={() => {}} />,
    );
    expect(getByTitle("Zoom out")).not.toBeDisabled();
    expect(getByTitle("Zoom in")).toBeDisabled();
  });

  it("calls onZoomChange with the next step when plus is clicked", () => {
    const onZoomChange = vi.fn();
    const { getByTitle } = render(
      <ZoomControls zoom={100} onZoomChange={onZoomChange} />,
    );
    fireEvent.click(getByTitle("Zoom in"));
    expect(onZoomChange).toHaveBeenCalledWith(125);
  });

  it("calls onZoomChange with the previous step when minus is clicked", () => {
    const onZoomChange = vi.fn();
    const { getByTitle } = render(
      <ZoomControls zoom={100} onZoomChange={onZoomChange} />,
    );
    fireEvent.click(getByTitle("Zoom out"));
    expect(onZoomChange).toHaveBeenCalledWith(75);
  });
});
