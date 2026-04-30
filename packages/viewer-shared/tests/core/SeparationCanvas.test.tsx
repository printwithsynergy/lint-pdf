/**
 * SeparationCanvas — Q7-A snapshot backfill.
 *
 * Composites per-channel ink images via multiply blending. Tests
 * focus on the canvas wrapper + service-URL plumbing for the
 * channel-image lookups; canvas pixel composition isn't visible
 * to jsdom.
 */

import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

import { SeparationCanvas } from "../../src/core/components/SeparationCanvas";
import { makeStubServices, withServices } from "../_helpers/services";

const baseProps = {
  jobId: "job-1",
  pageNum: 1,
  enabledChannels: new Set<string>(),
  allChannels: ["Cyan", "Magenta", "Yellow", "Black"],
  width: 612,
  height: 792,
};

describe("SeparationCanvas", () => {
  it("renders a canvas at the given width/height", () => {
    const services = makeStubServices();
    const { container } = render(
      withServices(<SeparationCanvas {...baseProps} />, services),
    );
    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();
    expect(canvas?.getAttribute("width")).toBe("612");
    expect(canvas?.getAttribute("height")).toBe("792");
    expect(container.firstChild).toMatchSnapshot();
  });

  it("calls services.separations.getChannelImageUrl for each enabled channel", () => {
    const getChannelImageUrl = vi.fn(() => "blob:test");
    const services = makeStubServices({
      separations: { getChannelImageUrl },
    });
    render(
      withServices(
        <SeparationCanvas
          {...baseProps}
          enabledChannels={new Set(["Cyan", "Black"])}
        />,
        services,
      ),
    );
    expect(getChannelImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      channelName: "Cyan",
      dpi: 150,
    });
    expect(getChannelImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      channelName: "Black",
      dpi: 150,
    });
    expect(getChannelImageUrl).toHaveBeenCalledTimes(2);
  });

  it("passes spot-color channel names through unchanged (factory percent-encodes)", () => {
    const getChannelImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      separations: { getChannelImageUrl },
    });
    render(
      withServices(
        <SeparationCanvas
          {...baseProps}
          enabledChannels={new Set(["Pantone Reflex Blue C"])}
          allChannels={["Pantone Reflex Blue C"]}
        />,
        services,
      ),
    );
    expect(getChannelImageUrl).toHaveBeenCalledWith({
      pageNum: 1,
      channelName: "Pantone Reflex Blue C",
      dpi: 150,
    });
  });

  it("honors a custom dpi", () => {
    const getChannelImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      separations: { getChannelImageUrl },
    });
    render(
      withServices(
        <SeparationCanvas
          {...baseProps}
          enabledChannels={new Set(["Cyan"])}
          dpi={300}
        />,
        services,
      ),
    );
    expect(getChannelImageUrl).toHaveBeenCalledWith(
      expect.objectContaining({ dpi: 300 }),
    );
  });

  it("does not call getChannelImageUrl when no channels are enabled", () => {
    const getChannelImageUrl = vi.fn(() => "");
    const services = makeStubServices({
      separations: { getChannelImageUrl },
    });
    render(withServices(<SeparationCanvas {...baseProps} />, services));
    expect(getChannelImageUrl).not.toHaveBeenCalled();
  });
});
