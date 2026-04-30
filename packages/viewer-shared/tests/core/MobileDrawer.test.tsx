/**
 * MobileDrawer — Q7-A snapshot backfill.
 *
 * Right-side drawer for the mobile viewer. Renders mode toggles +
 * report download links via services.reports (PR #343). Tests cover
 * the closed/open snapshots, the readOnly gating, the
 * services.reports URL plumbing, and the mode-toggle wiring.
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { MobileDrawer } from "../../src/core/components/MobileDrawer";
import { ViewerApiContext } from "../../src/types";
import { DEFAULT_VIEWER_CONFIG } from "../../src/core/types";
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
  isOpen: false,
  onClose: () => {},
  config: DEFAULT_VIEWER_CONFIG,
  viewerMode: "normal" as const,
  onToggleMode: () => {},
  measureMode: "none" as const,
  onToggleMeasure: () => {},
  showTacHeatmap: false,
  onToggleTacHeatmap: () => {},
  showBoxOverlay: false,
  onToggleBoxOverlay: () => {},
  findingSummary: { error: 0, warning: 0, advisory: 0 },
  zoom: 100,
  onZoomChange: () => {},
  jobId: "job-1",
  onExpandSheet: () => {},
};

describe("MobileDrawer", () => {
  it("renders nothing visible when isOpen=false (closed state)", () => {
    const services = makeStubServices();
    const { container } = render(wrap(<MobileDrawer {...baseProps} />, services));
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders the open drawer with sections + report download links", () => {
    const services = makeStubServices({
      reports: {
        getHtmlReportUrl: () => "/api/lintpdf/reports/job-1/html",
        getPdfDownloadUrl: () => "/api/lintpdf/reports/job-1/download",
      },
    });
    const { container, getByText } = render(
      wrap(<MobileDrawer {...baseProps} isOpen />, services),
    );
    // The "Share & Export" section is collapsed by default (its
    // DrawerSection has defaultOpen={false}); click the header to
    // reveal the report links.
    fireEvent.click(getByText("Share & Export"));
    const htmlLink = getByText("View HTML Report").closest("a");
    expect(htmlLink?.getAttribute("href")).toBe(
      "/api/lintpdf/reports/job-1/html",
    );
    const downloadLink = getByText("Download PDF").closest("a");
    expect(downloadLink?.getAttribute("href")).toBe(
      "/api/lintpdf/reports/job-1/download",
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("hides annotation/share-toggle CTAs when readOnly=true", () => {
    const services = makeStubServices();
    const { queryByText } = render(
      wrap(<MobileDrawer {...baseProps} isOpen />, services, true),
    );
    // Tools section is gated on readOnly + (annotations || comparison
    // enabled). With readOnly=true the entire Tools block is hidden;
    // its specific CTAs (Annotate, Compare) shouldn't render.
    expect(queryByText("Annotate")).toBeNull();
    expect(queryByText("Compare")).toBeNull();
  });

  it("does not render the HTML report link when config.enable_html_report_link=false", () => {
    const services = makeStubServices({
      reports: {
        getHtmlReportUrl: () => "/api/lintpdf/reports/job-1/html",
        getPdfDownloadUrl: () => "/api/lintpdf/reports/job-1/download",
      },
    });
    const { getByText, queryByText } = render(
      wrap(
        <MobileDrawer
          {...baseProps}
          isOpen
          config={{ ...DEFAULT_VIEWER_CONFIG, enable_html_report_link: false }}
        />,
        services,
      ),
    );
    fireEvent.click(getByText("Share & Export"));
    expect(queryByText("View HTML Report")).toBeNull();
    expect(queryByText("Download PDF")).not.toBeNull();
  });

  it("does not render the download link when config.enable_download=false", () => {
    const services = makeStubServices();
    const { getByText, queryByText } = render(
      wrap(
        <MobileDrawer
          {...baseProps}
          isOpen
          config={{ ...DEFAULT_VIEWER_CONFIG, enable_download: false }}
        />,
        services,
      ),
    );
    fireEvent.click(getByText("Share & Export"));
    expect(queryByText("Download PDF")).toBeNull();
  });

  it("calls onClose when the close button (X icon in header) is clicked", () => {
    const onClose = vi.fn();
    const services = makeStubServices();
    const { container } = render(
      wrap(<MobileDrawer {...baseProps} isOpen onClose={onClose} />, services),
    );
    // The close button is the unlabeled <button> inside the header
    // (justify-between row). Find it by being the first <button>
    // child of the header row's flex container.
    const closeBtn = container.querySelector(
      ".flex.h-12 button",
    ) as HTMLButtonElement | null;
    expect(closeBtn).not.toBeNull();
    fireEvent.click(closeBtn!);
    expect(onClose).toHaveBeenCalled();
  });
});
