"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { docSections } from "@/lib/doc-sections";

export function DocsNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const currentSlug = pathname.replace("/docs/", "").replace("/docs", "");

  function navLink(slug: string, label: string) {
    const isActive = currentSlug === slug;
    return (
      <Link
        key={slug}
        href={`/docs/${slug}`}
        onClick={() => setMobileOpen(false)}
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
      {/* Mobile docs nav toggle */}
      <div className="sticky top-16 z-30 bg-white border-b border-slate-200 px-6 py-2 lg:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="flex items-center gap-2 text-sm font-medium text-slate-700 min-h-[44px] w-full"
        >
          <svg
            className={`h-4 w-4 transition-transform ${mobileOpen ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
          Documentation
        </button>
        {mobileOpen && (
          <nav className="mt-2 pb-3 max-h-[60vh] overflow-y-auto">{nav}</nav>
        )}
      </div>

      {/* Desktop sidebar */}
      <nav className="hidden lg:block sticky top-24 w-56 flex-shrink-0 self-start max-h-[calc(100vh-8rem)] overflow-y-auto">
        {nav}
      </nav>
    </>
  );
}
