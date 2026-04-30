/**
 * AnnotationToolbar — Q7-A snapshot backfill.
 *
 * Pure presentational tool palette: 7 tool buttons, 7 preset
 * colour swatches + custom-colour input, undo/redo, save indicator.
 * No services / context required. Snapshots lock in the
 * markup so palette/icon changes are caught at PR review.
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { AnnotationToolbar } from "../../src/core/components/AnnotationToolbar";

const baseProps = {
  activeTool: "pointer" as const,
  onToolChange: () => {},
  strokeColor: "#ef4444",
  onStrokeColorChange: () => {},
  onUndo: () => {},
  onRedo: () => {},
  canUndo: false,
  canRedo: false,
  saving: false,
};

describe("AnnotationToolbar", () => {
  it("renders the default state (pointer active, undo+redo disabled, Saved indicator)", () => {
    const { container } = render(<AnnotationToolbar {...baseProps} />);
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders with the pen tool active + Saving... indicator", () => {
    const { container } = render(
      <AnnotationToolbar {...baseProps} activeTool="pen" saving />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("enables undo + redo when canUndo / canRedo are true", () => {
    const { getByTitle } = render(
      <AnnotationToolbar {...baseProps} canUndo canRedo />,
    );
    expect(getByTitle("Undo")).not.toBeDisabled();
    expect(getByTitle("Redo")).not.toBeDisabled();
  });

  it("disables undo + redo when canUndo / canRedo are false", () => {
    const { getByTitle } = render(<AnnotationToolbar {...baseProps} />);
    expect(getByTitle("Undo")).toBeDisabled();
    expect(getByTitle("Redo")).toBeDisabled();
  });

  it("calls onToolChange when a tool button is clicked", () => {
    const onToolChange = vi.fn();
    const { getByTitle } = render(
      <AnnotationToolbar {...baseProps} onToolChange={onToolChange} />,
    );
    fireEvent.click(getByTitle("Rectangle"));
    expect(onToolChange).toHaveBeenCalledWith("rectangle");
  });

  it("calls onStrokeColorChange when a preset colour swatch is clicked", () => {
    const onStrokeColorChange = vi.fn();
    const { getByTitle } = render(
      <AnnotationToolbar
        {...baseProps}
        onStrokeColorChange={onStrokeColorChange}
      />,
    );
    fireEvent.click(getByTitle("#22c55e"));
    expect(onStrokeColorChange).toHaveBeenCalledWith("#22c55e");
  });

  it("calls onUndo when the undo button is clicked", () => {
    const onUndo = vi.fn();
    const { getByTitle } = render(
      <AnnotationToolbar {...baseProps} canUndo onUndo={onUndo} />,
    );
    fireEvent.click(getByTitle("Undo"));
    expect(onUndo).toHaveBeenCalledTimes(1);
  });
});
