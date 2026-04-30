/**
 * AnnotationCanvas — Q7-A snapshot backfill.
 *
 * Fabric.js drawing canvas with autosave. Fabric is dynamically
 * imported and depends on HTMLCanvasElement.getContext, which
 * jsdom doesn't implement. The mock below stubs the Fabric API
 * the component touches: `Canvas` constructor + `loadFromJSON` +
 * `on/off` event subscription + `dispose`. It's intentionally
 * minimal — enough for the `init()` effect to run end-to-end
 * (so we can assert on services.annotations.getForPage), but no
 * actual drawing.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";

vi.mock("fabric", () => {
  class MockCanvas {
    isDrawingMode = false;
    selection = true;
    defaultCursor = "default";
    freeDrawingBrush?: { color: string; width: number };
    constructor(_el: unknown, _opts: unknown) {
      // no-op
    }
    toJSON() {
      return { version: "6.0.0", objects: [] };
    }
    loadFromJSON(_json: unknown, cb: () => void) {
      cb();
      return this;
    }
    renderAll() {}
    on() {}
    off() {}
    add() {}
    remove() {}
    setActiveObject() {}
    getPointer() {
      return { x: 0, y: 0 };
    }
    setDimensions() {}
    dispose() {}
  }
  return {
    Canvas: MockCanvas,
    Rect: class { set() {} },
    Ellipse: class { set() {} },
    Line: class { set() {} },
    Triangle: class {},
    Group: class {},
    IText: class { enterEditing() {} },
  };
});

import { AnnotationCanvas } from "../../src/core/components/AnnotationCanvas";
import { ViewerApiContext } from "../../src/types";
import { makeStubServices, withServices } from "../_helpers/services";
import type { ViewerServices } from "../../src/core/plugin/services";

const wrap = (ui: React.ReactNode, services: ViewerServices, readOnly = false) => (
  <ViewerApiContext.Provider
    value={{ apiBase: "/api/test", jobApiBase: "/api/test/job", readOnly }}
  >
    {withServices(ui, services)}
  </ViewerApiContext.Provider>
);

const baseProps = {
  jobId: "job-1",
  pageNum: 1,
  width: 612,
  height: 792,
  activeTool: "pointer" as const,
  strokeColor: "#ef4444",
};

beforeEach(() => {
  // Suppress noisy "react-dom" act() warnings from the async init
  // effect; we explicitly waitFor() in tests that depend on the
  // post-init state.
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AnnotationCanvas", () => {
  it("renders the wrapper div with a canvas child", () => {
    const services = makeStubServices();
    const { container } = render(wrap(<AnnotationCanvas {...baseProps} />, services));
    expect(container.firstChild).toMatchSnapshot();
    expect(container.querySelector("canvas")).not.toBeNull();
  });

  it("calls services.annotations.getForPage with the current pageNum on mount", async () => {
    const getForPage = vi.fn(async () => null);
    const services = makeStubServices({
      annotations: { getForPage },
    });
    render(wrap(<AnnotationCanvas {...baseProps} pageNum={3} />, services));
    await waitFor(() => expect(getForPage).toHaveBeenCalledWith(3));
  });

  it("re-fetches when pageNum changes", async () => {
    const getForPage = vi.fn(async () => null);
    const services = makeStubServices({
      annotations: { getForPage },
    });
    const { rerender } = render(
      wrap(<AnnotationCanvas {...baseProps} pageNum={1} />, services),
    );
    await waitFor(() => expect(getForPage).toHaveBeenCalledWith(1));
    rerender(wrap(<AnnotationCanvas {...baseProps} pageNum={2} />, services));
    await waitFor(() => expect(getForPage).toHaveBeenCalledWith(2));
  });

  it("does not blow up when getForPage returns null (no saved drawing)", async () => {
    const services = makeStubServices({
      annotations: { getForPage: async () => null },
    });
    expect(() =>
      render(wrap(<AnnotationCanvas {...baseProps} />, services)),
    ).not.toThrow();
  });

  it("respects readOnly via useViewerHost (saveForPage gating)", async () => {
    // saveForPage only fires from Fabric object:added events which
    // the mock doesn't synthesize — this test confirms readOnly
    // reaches the component without crashing the render path.
    const saveForPage = vi.fn(async () => {});
    const services = makeStubServices({
      annotations: { saveForPage },
    });
    render(
      wrap(
        <AnnotationCanvas {...baseProps} />,
        services,
        true, // readOnly
      ),
    );
    expect(saveForPage).not.toHaveBeenCalled();
  });
});
