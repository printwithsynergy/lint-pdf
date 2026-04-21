"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { docSections } from "@/lib/doc-sections";

export function DocsNav() {
  const pathname = usePathname();
  const currentSlug = pathname.replace("/docs/", "").replace("/docs", "");
  const pillBarRef = useRef<HTMLDivElement>(null);
  const activePillRef = useRef<HTMLButtonElement>(null);
  const activeLinkRef = useRef<HTMLAnchorElement>(null);

  function sectionForSlug(slug: string) {
    for (const section of docSections) {
      if (section.items.some((item) => item.slug === slug)) {
        return section.heading;
      }
    }
    return null;
  }

  // Single-open accordion: which section is currently expanded on both
  // mobile + desktop. Initialises to the section that contains the
  // current page so a user landing on any doc sees their context without
  // having to click anything.
  const [activeSection, setActiveSection] = useState<string | null>(
    sectionForSlug(currentSlug),
  );

  // Route change → auto-expand the group containing the new page.
  useEffect(() => {
    const section = sectionForSlug(currentSlug);
    setActiveSection(section);
  }, [currentSlug]);

  // Mobile: centre the active pill in the horizontal scroller.
  // Desktop: ensure the active link is visible inside the sidebar scroller.
  useEffect(() => {
    activePillRef.current?.scrollIntoView({
      inline: "center",
      block: "nearest",
      behavior: "smooth",
    });
    activeLinkRef.current?.scrollIntoView({
      block: "nearest",
      behavior: "smooth",
    });
  }, [activeSection, currentSlug]);

  function toggleSection(heading: string) {
    setActiveSection((prev) => (prev === heading ? null : heading));
  }

  const activeItems = activeSection
    ? (docSections.find((s) => s.heading === activeSection)?.items ?? [])
    : [];

  function navLink(slug: string, label: string, refActiveLink = false) {
    const isActive = currentSlug === slug;
    return (
      <Link
        key={slug}
        href={`/docs/${slug}`}
        ref={isActive && refActiveLink ? activeLinkRef : undefined}
        className={`block rounded-md px-3 py-1.5 text-sm transition-colors ${
          isActive
            ? "bg-brand-50 text-brand-700 font-medium"
            : "text-slate-500 hover:text-brand-700 hover:bg-slate-50"
        }`}
      >
        {label}
      </Link>
    );
  }

  return (
    <>
      {/* Mobile pill bar */}
      <div className="sticky top-16 z-30 bg-white border-b border-slate-200 lg:hidden">
        <div
          ref={pillBarRef}
          className="scrollbar-hide flex gap-2 overflow-x-auto px-4 py-2"
        >
          {docSections.map((section) => {
            const isActive = activeSection === section.heading;
            return (
              <button
                key={section.heading}
                ref={isActive ? activePillRef : undefined}
                type="button"
                onClick={() => toggleSection(section.heading)}
                className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-700 font-medium"
                    : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                }`}
              >
                {section.heading}
              </button>
            );
          })}
        </div>

        {/* Expandable items for the active section */}
        <nav
          className={`overflow-y-auto transition-all duration-200 ease-in-out ${
            activeSection
              ? "max-h-[50vh] opacity-100 px-4 pb-3"
              : "max-h-0 opacity-0 overflow-hidden"
          }`}
        >
          <div className="space-y-0.5">
            {activeItems.map((item) => navLink(item.slug, item.label))}
          </div>
        </nav>
      </div>

      {/* Desktop sidebar — accordion, single-open */}
      <nav className="hidden lg:block sticky top-24 w-56 flex-shrink-0 self-start max-h-[calc(100vh-8rem)] overflow-y-auto pb-8">
        {docSections.map((section) => {
          const isOpen = activeSection === section.heading;
          return (
            <div key={section.heading} className="mb-1">
              <button
                type="button"
                onClick={() => toggleSection(section.heading)}
                aria-expanded={isOpen}
                className="flex w-full items-center justify-between rounded-md px-3 py-1.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700"
              >
                <span>{section.heading}</span>
                <Chevron open={isOpen} />
              </button>
              {isOpen && (
                <div className="mt-0.5 mb-3 space-y-0.5">
                  {section.items.map((item) =>
                    navLink(item.slug, item.label, true),
                  )}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-3 w-3 shrink-0 text-slate-400 transition-transform ${
        open ? "rotate-90" : ""
      }`}
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 3l4 3-4 3" />
    </svg>
  );
}
