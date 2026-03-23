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

  // Find which section contains the current page
  function sectionForSlug(slug: string) {
    for (const section of docSections) {
      if (section.items.some((item) => item.slug === slug)) {
        return section.heading;
      }
    }
    return null;
  }

  const [activeSection, setActiveSection] = useState<string | null>(
    sectionForSlug(currentSlug),
  );

  // Update active section and scroll pill into view on route change
  useEffect(() => {
    const section = sectionForSlug(currentSlug);
    setActiveSection(section);
  }, [currentSlug]);

  useEffect(() => {
    activePillRef.current?.scrollIntoView({
      inline: "center",
      block: "nearest",
      behavior: "smooth",
    });
  }, [activeSection]);

  function toggleSection(heading: string) {
    setActiveSection((prev) => (prev === heading ? null : heading));
  }

  const activeItems = activeSection
    ? docSections.find((s) => s.heading === activeSection)?.items ?? []
    : [];

  function navLink(slug: string, label: string) {
    const isActive = currentSlug === slug;
    return (
      <Link
        key={slug}
        href={`/docs/${slug}`}
        onClick={() => setActiveSection(null)}
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

  const nav = (
    <>
      {docSections.map((section) => (
        <div key={section.heading} className="mb-4">
          <h4 className="px-3 mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {section.heading}
          </h4>
          <div className="space-y-0.5">
            {section.items.map((item) => navLink(item.slug, item.label))}
          </div>
        </div>
      ))}
    </>
  );

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

      {/* Desktop sidebar */}
      <nav className="hidden lg:block sticky top-24 w-56 flex-shrink-0 self-start max-h-[calc(100vh-8rem)] overflow-y-auto">
        {nav}
      </nav>
    </>
  );
}
