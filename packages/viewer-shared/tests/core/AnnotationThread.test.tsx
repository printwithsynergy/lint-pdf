/**
 * AnnotationThread — Q7-A snapshot backfill.
 *
 * Sidebar list of annotations with delete-only-mine actions. Reads
 * from services.annotations.list() (PR #342). Tests cover loading
 * state, empty state, populated state, ownership-gated delete, and
 * delete wiring through services.annotations.remove().
 */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, waitFor } from "@testing-library/react";

import { AnnotationThread } from "../../src/core/components/AnnotationThread";
import { ViewerApiContext } from "../../src/types";
import type { AnnotationEntry } from "../../src/core/plugin/services";
import { makeStubServices, withServices } from "../_helpers/services";
import type { ViewerServices } from "../../src/core/plugin/services";

const wrap = (ui: React.ReactNode, services: ViewerServices, readOnly = false) => (
  <ViewerApiContext.Provider
    value={{ apiBase: "/api/test", jobApiBase: "/api/test/job", readOnly }}
  >
    {withServices(ui, services)}
  </ViewerApiContext.Provider>
);

const mkEntry = (overrides: Partial<AnnotationEntry> = {}): AnnotationEntry => ({
  id: "a1",
  jobId: "job-1",
  pageNum: 1,
  authorEmail: "alice@example.com",
  authorName: "Alice",
  createdAt: "2026-04-30T12:00:00Z",
  updatedAt: "2026-04-30T12:00:00Z",
  ...overrides,
});

describe("AnnotationThread", () => {
  it("renders the loading state on first render", () => {
    const services = makeStubServices({
      annotations: {
        list: () => new Promise(() => {}), // never resolves
      },
    });
    const { container } = render(
      wrap(<AnnotationThread jobId="job-1" />, services),
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders the empty-state message when list returns []", async () => {
    const services = makeStubServices({
      annotations: { list: async () => [] },
    });
    const { findByText, container } = render(
      wrap(<AnnotationThread jobId="job-1" />, services),
    );
    await findByText(/no annotations yet/i);
    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders one row per annotation with author + page + jump-to-page link", async () => {
    const services = makeStubServices({
      annotations: {
        list: async () => [
          mkEntry({ id: "a1", pageNum: 3, authorName: "Alice" }),
          mkEntry({
            id: "a2",
            pageNum: 5,
            authorName: null,
            authorEmail: "bob@example.com",
          }),
        ],
      },
    });
    const { findByText, container } = render(
      wrap(<AnnotationThread jobId="job-1" />, services),
    );
    await findByText("Alice");
    expect(container.textContent).toContain("Page 3");
    expect(container.textContent).toContain("bob@example.com");
    expect(container.textContent).toContain("Page 5");
  });

  it("renders Delete button only for the current user's annotations", async () => {
    const services = makeStubServices({
      annotations: {
        list: async () => [
          mkEntry({ id: "a1", authorEmail: "alice@example.com" }),
          mkEntry({ id: "a2", authorEmail: "bob@example.com" }),
        ],
      },
    });
    const { findAllByText } = render(
      wrap(
        <AnnotationThread
          jobId="job-1"
          currentUserEmail="alice@example.com"
        />,
        services,
      ),
    );
    await findAllByText(/Alice/);
    // Only one Delete button (for alice's annotation).
    const deleteButtons = document.querySelectorAll('[title="Delete annotation"]');
    expect(deleteButtons).toHaveLength(1);
  });

  it("hides all Delete buttons when readOnly=true", async () => {
    const services = makeStubServices({
      annotations: {
        list: async () => [
          mkEntry({ authorEmail: "alice@example.com" }),
        ],
      },
    });
    render(
      wrap(
        <AnnotationThread
          jobId="job-1"
          currentUserEmail="alice@example.com"
        />,
        services,
        true,
      ),
    );
    await waitFor(() => {
      const deleteButtons = document.querySelectorAll(
        '[title="Delete annotation"]',
      );
      expect(deleteButtons).toHaveLength(0);
    });
  });

  it("calls services.annotations.remove + updates the list when Delete clicked", async () => {
    const remove = vi.fn(async () => {});
    const services = makeStubServices({
      annotations: {
        list: async () => [
          mkEntry({ id: "a1", authorEmail: "alice@example.com" }),
        ],
        remove,
      },
    });
    const { findAllByTitle, queryByText } = render(
      wrap(
        <AnnotationThread
          jobId="job-1"
          currentUserEmail="alice@example.com"
        />,
        services,
      ),
    );
    const buttons = await findAllByTitle("Delete annotation");
    fireEvent.click(buttons[0]!);
    await waitFor(() => expect(remove).toHaveBeenCalledWith("a1"));
    // Row should be removed optimistically.
    await waitFor(() => expect(queryByText("Alice")).toBeNull());
  });

  it("calls onJumpToPage with the annotation's pageNum when Jump-to-page clicked", async () => {
    const onJumpToPage = vi.fn();
    const services = makeStubServices({
      annotations: {
        list: async () => [mkEntry({ pageNum: 7 })],
      },
    });
    const { findByText } = render(
      wrap(
        <AnnotationThread jobId="job-1" onJumpToPage={onJumpToPage} />,
        services,
      ),
    );
    fireEvent.click(await findByText("Jump to page"));
    expect(onJumpToPage).toHaveBeenCalledWith(7);
  });
});
