import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { AI_CATEGORIES, AI_PRESETS } from "@/lib/brand";

export const metadata: Metadata = {
  title: "Features — LintPDF",
  description:
    "506 rule-based checks (259 LPDF + 247 PDF/X-4) plus 99 AI-powered inspections for PDF preflight. Resolution, fonts, colors, transparency, bleeds, packaging geometry, barcode grading, regulatory compliance, and more.",
};

const coreFeatures = [
  {
    title: "Font Integrity",
    description:
      "Embedding, subsetting, Type 3 detection, encoding mismatches, simulated bold/italic — every font issue that causes RIP failures.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M3 7V5a2 2 0 012-2h2m10 0h2a2 2 0 012 2v2m0 10v2a2 2 0 01-2 2h-2M5 21H3a2 2 0 01-2-2v-2m7-8h4m-2-2v4"
        />
      </svg>
    ),
  },
  {
    title: "Color Spaces",
    description:
      "RGB in CMYK workflows, spot color detection, ICC profile validation, overprint conflicts, and total ink coverage thresholds.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4.098 19.902a3.75 3.75 0 005.304 0l6.401-6.402M6.75 21A3.75 3.75 0 013 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 003.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072M10.5 8.197l2.88-2.88c.438-.439 1.15-.439 1.59 0l3.712 3.713c.44.44.44 1.152 0 1.59l-2.879 2.88M6.75 17.25h.008v.008H6.75v-.008z"
        />
      </svg>
    ),
  },
  {
    title: "Image Resolution",
    description:
      "DPI validation per image, JPEG artifact detection, missing or corrupt streams, alpha transparency in print workflows.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5a2.25 2.25 0 002.25-2.25V5.25a2.25 2.25 0 00-2.25-2.25H3.75a2.25 2.25 0 00-2.25 2.25v13.5a2.25 2.25 0 002.25 2.25z"
        />
      </svg>
    ),
  },
  {
    title: "Transparency & Blend Modes",
    description:
      "Transparency effects, non-standard blend modes, soft masks, and gradient transparency detection across all pages.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
        />
      </svg>
    ),
  },
  {
    title: "Page Geometry & Bleeds",
    description:
      "TrimBox validation, bleed sufficiency, page size matching, content outside trim detection. Every box the printer needs.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
        />
      </svg>
    ),
  },
  {
    title: "PDF/X & PDF/A Compliance",
    description:
      "PDF/X-1a, PDF/X-3, PDF/X-4 (ISO 15930) and PDF/A archival conformance. JavaScript, encryption, and prohibited feature detection.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
        />
      </svg>
    ),
  },
  {
    title: "Barcode Grading",
    description:
      "ISO 15416/15415 barcode grading for 1D and 2D codes, quiet zone validation, DPI checks, decode verification, and non-compliant color detection.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zm0 9.75c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zm9.75-9.75c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z"
        />
      </svg>
    ),
  },
  {
    title: "Overprint & Ink",
    description:
      "Overprint settings validation, ink coverage calculations per page, spot color usage tracking, and total area coverage limits.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 5.607A2.25 2.25 0 0119.027 23h-14.054a2.25 2.25 0 01-2.175-2.093L5 14.5"
        />
      </svg>
    ),
  },
];

const aiCategoryIcons: Record<string, React.ReactNode> = {
  barcode: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zm0 9.75c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zm9.75-9.75c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z"
      />
    </svg>
  ),
  content_quality: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
      />
    </svg>
  ),
  file_comparison: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
      />
    </svg>
  ),
  color_compliance: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M4.098 19.902a3.75 3.75 0 005.304 0l6.401-6.402M6.75 21A3.75 3.75 0 013 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 003.75-3.75V8.197"
      />
    </svg>
  ),
  trend_analysis: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
      />
    </svg>
  ),
  dieline: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
      />
    </svg>
  ),
  regulatory: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
      />
    </svg>
  ),
  image_analysis: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  ),
  document_classification: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
      />
    </svg>
  ),
  logo_verification: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42"
      />
    </svg>
  ),
  spatial_analysis: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9 6.75V15m0-6H4.5m4.5 0h4.5m0 0V15m0-8.25H18m-4.5 0V3M9 15v3.75m4.5-3.75v3.75M3 21h18"
      />
    </svg>
  ),
  nlp: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
      />
    </svg>
  ),
  text_analysis: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M10.5 21l5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 016-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 01-3.827-5.802"
      />
    </svg>
  ),
  symbol_detection: (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"
      />
    </svg>
  ),
};

const defaultIcon = (
  <svg
    className="h-6 w-6"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
    />
  </svg>
);

export default function FeaturesPage() {
  const totalAiInspections = AI_CATEGORIES.reduce(
    (acc, cat) => acc + cat.inspections.length,
    0,
  );

  return (
    <main>
      {/* Hero */}
      <section className="bg-brand-50/50 pt-20 pb-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h1 className="text-4xl font-bold text-slate-900 md:text-5xl mb-4">
            Everything Your PDFs Need, Checked Automatically
          </h1>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto">
            506 rule-based checks (259 LPDF + 247 PDF/X-4) powered by a deterministic engine, plus{" "}
            {totalAiInspections} AI-powered inspections for content quality,
            regulatory compliance, and brand verification.
          </p>
        </div>
      </section>

      {/* Three ways to run */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">
              Three ways to run
            </h2>
            <p className="text-slate-500 max-w-3xl">
              LintPDF processes jobs in one of three modes. Pick per-request —
              mix and match across your workflow.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            <div className="rounded-2xl border border-brand-200 bg-white p-6 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wider text-brand-700 mb-2">
                Engine
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Run our 600+ checks
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed mb-4">
                Full analyzer pipeline — fonts, color, images, transparency,
                packaging geometry, barcode grading, PDF/X + PDF/A compliance.
                Separations, TAC, font and image catalogues all shipped in the
                viewer.
              </p>
              <Link
                href="/docs/preflight-modes"
                className="text-xs font-semibold text-brand-700 hover:underline"
              >
                Read the mode guide →
              </Link>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                External Import
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Bring your own preflight
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed mb-4">
                Already running PitStop, callas pdfToolbox, or Adobe Acrobat
                Preflight? Submit the PDF plus the XML/JSON report. LintPDF
                parses the findings and renders them in the viewer with full
                geometry — no re-checking cost.
              </p>
              <Link
                href="/docs/external-imports"
                className="text-xs font-semibold text-brand-700 hover:underline"
              >
                See supported formats →
              </Link>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                Viewer Only
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Just render &amp; share
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed mb-4">
                Submit in minimal mode for pure viewer + share-link use cases —
                no analyzers run. On Starter+, separations, TAC, fonts, and
                images can be filled on demand when you need them. The new{" "}
                <Link
                  href="/pricing"
                  className="font-semibold text-brand-700 hover:underline"
                >
                  Viewer tier
                </Link>{" "}
                packages this workflow at $15/mo.
              </p>
              <Link
                href="/docs/viewer-only-mode"
                className="text-xs font-semibold text-brand-700 hover:underline"
              >
                Minimal mode docs →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Hosted Web Viewer capabilities */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">
              Hosted Web Viewer
            </h2>
            <p className="text-slate-500 max-w-3xl">
              Every job — engine, external import, or minimal — opens in the
              same production-grade viewer. Share links are tokenized,
              branded, and stream from Cloudflare R2 edge caches.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[
              {
                title: "Separations & ink channels",
                body: "Toggle process (CMYK) and spot channels per page. Isolate single inks, inspect overprint behaviour, verify plate counts.",
              },
              {
                title: "TAC heatmap + densitometer",
                body: "Total Area Coverage overlay flags ink-limit violations. Click any pixel to read the densitometer across every separation.",
              },
              {
                title: "Layers & optional content",
                body: "PDF optional-content groups render as toggleable layers. Dieline, white ink, and varnish each get their own visibility switch.",
              },
              {
                title: "File comparison",
                body: "Diff two revisions side-by-side with SSIM heatmaps. Catch moved elements, colour shifts, font substitutions before they ship.",
              },
              {
                title: "Branded & anonymous share links",
                body: "Every job mints a tokenized URL with your logo and colours — or strip all branding including PDF metadata with one flag.",
              },
              {
                title: "Cloudflare R2 edge caching",
                body: "Page tiles are pre-warmed into Cloudflare R2 on ingest. Reviewers load from the closest edge, no cold-render waits.",
              },
            ].map((cap) => (
              <div
                key={cap.title}
                className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-1"
              >
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  {cap.title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed">
                  {cap.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Anonymous output */}
      <section className="py-8">
        <div className="mx-auto max-w-6xl px-6">
          <div className="rounded-2xl border border-slate-100 bg-gradient-to-br from-brand-50/80 to-white p-8">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div className="max-w-3xl">
                <h2 className="text-2xl font-bold text-slate-900 mb-2">
                  Anonymous output for brokers &amp; distributors
                </h2>
                <p className="text-slate-600 leading-relaxed">
                  Flip a tenant default or pass{" "}
                  <code className="bg-white px-1 rounded text-sm font-mono">
                    brand=anonymous
                  </code>{" "}
                  per submission to strip every trace of LintPDF{" "}
                  <em>and</em> tenant branding from reports, viewers, and
                  share links. PDF metadata is sanitized, the filename becomes{" "}
                  <code className="bg-white px-1 rounded text-sm font-mono">
                    preflight-&lt;id&gt;.pdf
                  </code>
                  , and share links freeze that anonymity at mint time — flipping
                  the setting later won&apos;t retroactively rebrand already-sent
                  links. Ideal for agencies and brokers who hand reports to
                  end-distributors without exposing their supply chain.
                </p>
              </div>
              <Link
                href="/docs/branding-and-anonymous"
                className="shrink-0 rounded-xl bg-brand-700 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-800"
              >
                How anonymous mode works →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Core Engine */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">
              Core Engine
            </h2>
            <p className="text-slate-500 max-w-3xl">
              506 rule-based checks (259 LPDF + 247 PDF/X-4 conformance) that run on every file. Deterministic,
              fast, and thorough. Resolution, fonts, colors, transparency,
              bleeds, barcodes, packaging geometry, artwork comparison,
              compliance, and more. Included on all plans with no per-check
              fees.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {coreFeatures.map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-1"
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Inspections Header */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12 text-center">
            <div className="flex items-center justify-center gap-3 mb-4">
              <h2 className="text-3xl font-bold text-slate-900">
                AI Inspections
              </h2>
              <span className="rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white">
                Invite-Only Alpha
              </span>
            </div>
            <p className="text-slate-500 max-w-3xl mx-auto">
              {totalAiInspections} AI-powered inspections across{" "}
              {AI_CATEGORIES.length} categories. Computer vision, NLP, and
              machine learning models that catch what deterministic rules
              cannot. Metered with credits, available on all paid plans.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {AI_CATEGORIES.map((category) => (
              <div
                key={category.id}
                className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-1"
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  {aiCategoryIcons[category.id] ?? defaultIcon}
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-lg font-semibold text-slate-900">
                    {category.name}
                  </h3>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {category.inspections.length}
                  </span>
                </div>
                <p className="text-sm text-slate-500 leading-relaxed mb-4">
                  {category.description}
                </p>
                <ul className="space-y-1.5">
                  {category.inspections.map((inspection) => (
                    <li
                      key={inspection.id}
                      className="flex items-start gap-2 text-xs text-slate-500"
                    >
                      <span
                        className={`mt-0.5 inline-block h-1.5 w-1.5 rounded-full flex-shrink-0 ${inspection.tier === "text" ? "bg-emerald-400" : "bg-violet-400"}`}
                      />
                      <span>
                        <span className="font-medium text-slate-700">
                          {inspection.name}
                        </span>{" "}
                        &mdash; {inspection.credits} credit
                        {inspection.credits > 1 ? "s" : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Presets */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">
              AI Presets
            </h2>
            <p className="text-slate-500 max-w-3xl">
              Pre-configured inspection bundles for common use cases. Select a
              preset in your submit request or build custom combinations in your
              Ruleset.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {AI_PRESETS.map((preset) => (
              <div
                key={preset.id}
                className="rounded-xl border border-slate-200 bg-white p-5 hover:border-brand-200 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                    {preset.id}
                  </code>
                </div>
                <h3 className="font-semibold text-slate-900 mb-1">
                  {preset.name}
                </h3>
                <p className="text-sm text-slate-500 mb-3">
                  {preset.description}
                </p>
                <p className="text-xs text-slate-400">
                  Est. {preset.estimatedCredits} credits per file
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tier Legend */}
      <section className="bg-brand-50/50 py-12">
        <div className="mx-auto max-w-4xl px-6">
          <div className="flex flex-col sm:flex-row gap-8 justify-center">
            <div className="flex items-center gap-3">
              <span className="inline-block h-3 w-3 rounded-full bg-emerald-400" />
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Text Tier
                </p>
                <p className="text-xs text-slate-500">
                  1 credit &middot; Sub-second latency &middot; Text & structure
                  analysis
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-block h-3 w-3 rounded-full bg-violet-400" />
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Vision Tier
                </p>
                <p className="text-xs text-slate-500">
                  2 credits &middot; 1-5s latency &middot; Vision & ML models
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Ready to preflight smarter?
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto mb-8">
            Core engine checks are available on all plans. AI features are in
            invite-only alpha — request access to get started.
          </p>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <a
              href="/ai"
              className="rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
            >
              Explore AI Features
            </a>
            <Link
              href="/docs"
              className="rounded-xl border-2 border-slate-200 px-8 py-3.5 text-base font-medium text-slate-600 transition-all hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50"
            >
              View Documentation
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
