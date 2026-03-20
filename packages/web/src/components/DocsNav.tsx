"use client";

import { useState, useEffect } from "react";

const sections = [
  { id: "getting-started", label: "Getting Started" },
  { id: "authentication", label: "Authentication" },
  { id: "api-reference", label: "API Reference" },
  { id: "rulesets", label: "Rulesets" },
  { id: "inspections", label: "Checks" },
  { id: "report-formats", label: "Report Formats" },
  { id: "webhooks", label: "Webhooks" },
  { id: "sdks", label: "SDKs" },
  { id: "glossary", label: "Glossary" },
  { id: "ai-getting-started", label: "AI Getting Started" },
  { id: "ai-configuration", label: "AI Configuration" },
  { id: "ai-credits", label: "AI Credits" },
  { id: "ai-inspections", label: "AI Inspections" },
  { id: "ai-presets", label: "AI Presets" },
  { id: "ai-regulatory", label: "Regulatory Compliance" },
  { id: "ai-api", label: "AI API Reference" },
  { id: "ai-errors", label: "AI Errors" },
  { id: "ai-examples", label: "AI Code Examples" },
];

export function DocsNav() {
  const [active, setActive] = useState("getting-started");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActive(entry.target.id);
          }
        }
      },
      { rootMargin: "-80px 0px -60% 0px", threshold: 0 },
    );

    for (const section of sections) {
      const el = document.getElementById(section.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <>
      {/* Mobile docs nav toggle */}
      <div className="sticky top-16 z-30 bg-white border-b border-slate-200 px-6 py-3 lg:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="flex items-center gap-2 text-sm font-medium text-slate-700"
        >
          <svg
            className="h-4 w-4"
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
          <nav className="mt-3 space-y-1">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                onClick={() => setMobileOpen(false)}
                className={`block rounded-md px-3 py-1.5 text-sm transition-colors ${
                  active === s.id
                    ? "bg-brand-50 text-brand-700 font-medium"
                    : "text-slate-500 hover:text-brand-700"
                }`}
              >
                {s.label}
              </a>
            ))}
          </nav>
        )}
      </div>

      {/* Desktop sidebar */}
      <nav className="hidden lg:block sticky top-24 w-56 flex-shrink-0 self-start">
        <ul className="space-y-1">
          {sections.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className={`block rounded-md px-3 py-1.5 text-sm transition-colors ${
                  active === s.id
                    ? "bg-brand-50 text-brand-700 font-medium"
                    : "text-slate-500 hover:text-brand-700 hover:bg-slate-50"
                }`}
              >
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
