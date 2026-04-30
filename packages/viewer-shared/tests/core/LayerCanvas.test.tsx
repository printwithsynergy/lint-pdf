/**
 * LayerCanvas — Q7-A snapshot backfill.
 *
 * Composites isolated layer-PNG tiles into a `<canvas>` via
 * source-over blending. Snapshots can only capture the wrapper
 * markup (jsdom doesn't render canvas pixels); the tests focus on
 * the wrapper structure + service-URL plumbing.
 */

import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

import { LayerCanvas } from "../../src/core/components/LayerCanvas";
import { makeStubServices, withServices } from "../_helpers/services";

const baseProps = {
  jobId: "job-1",
  pageNum: 1,
  enabledLayers: new Set<number>(),
  allLayers: [0, 1, 2],
  width: 612,
  height: 792,
};

describe("LayerCanvas", () => {
  it("renders a canvas at the given width/height", () => {
    const services = makeStubServices();
    const { container } = render(withServices(<LayerCanvas {...baseProps} />, services));
    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();
    expect(canvas?.getAttribute("width")).toBe("612");
    expect(canvas?.getAttribute("height")).toBe("792");
    expect(container.firstChild).toMatchSnapshot();
  });

  it("calls services.layers.getLayerImageUrl for each enabled layer", () => {
    const getLayerImageUrl = vi.fn(() => "blob:test");
    const services = makeStubServices({
      layers: { getLayerImageUrl, listLayers: async () => [] },
    });
    render(
      withServices(
        <LayerCanvas
          {...baseProps}
          enabledLayers={new Set([0, 2])}
        />,
        services,
      ),
    );
    // Each enabled layer triggers a load attempt.
    expect(getLayerImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      layerIndex: 0,
      dpi: 150,
    });
    expect(getLayerImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      layerIndex: 2,
      dpi: 150,
    });
    expect(getLayerImageUrl).toHaveBeenCalledTimes(2);
  });

  it("honors a custom dpi", () => {
    const getLayerImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      layers: { getLayerImageUrl, listLayers: async () => [] },
    });
    render(
      withServices(
        <LayerCanvas
          {...baseProps}
          enabledLayers={new Set([1])}
          dpi={300}
        />,
        services,
      ),
    );
    expect(getLayerImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      layerIndex: 1,
      dpi: 300,
    });
  });

  it("does not call getLayerImageUrl when no layers are enabled", () => {
    const getLayerImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      layers: { getLayerImageUrl, listLayers: async () => [] },
    });
    render(withServices(<LayerCanvas {...baseProps} />, services));
    expect(getLayerImageUrl).not.toHaveBeenCalled();
  });

  it("re-fetches when pageNum changes (cache cleared on page flip)", () => {
    const getLayerImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      layers: { getLayerImageUrl, listLayers: async () => [] },
    });
    const { rerender } = render(
      withServices(
        <LayerCanvas {...baseProps} enabledLayers={new Set([0])} />,
        services,
      ),
    );
    expect(getLayerImageUrl).toHaveBeenCalledWith(
      expect.objectContaining({ pageNum: 1, layerIndex: 0 }),
    );

    rerender(
      withServices(
        <LayerCanvas {...baseProps} pageNum={2} enabledLayers={new Set([0])} />,
        services,
      ),
    );
    expect(getLayerImageUrl).toHaveBeenCalledWith(
      expect.objectContaining({ pageNum: 2, layerIndex: 0 }),
    );
  });
});
