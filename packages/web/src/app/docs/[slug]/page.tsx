import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getDocBySlug, getAllDocSlugs } from "@/lib/docs";
import { allDocSlugs } from "@/lib/doc-sections";

// JSX page components (too complex for markdown)
import ApiReferencePage from "@/components/docs/pages/ApiReferencePage";
import ChecksPage from "@/components/docs/pages/ChecksPage";
import ReportFormatsPage from "@/components/docs/pages/ReportFormatsPage";
import WebhooksPage from "@/components/docs/pages/WebhooksPage";
import GlossaryPage from "@/components/docs/pages/GlossaryPage";
import AiInspectionsPage from "@/components/docs/pages/AiInspectionsPage";
import AiApiPage from "@/components/docs/pages/AiApiPage";

interface Props {
  params: Promise<{ slug: string }>;
}

const jsxPages: Record<
  string,
  { component: React.ComponentType; title: string; description: string }
> = {
  "api-reference": {
    component: ApiReferencePage,
    title: "API Reference",
    description: "Complete API reference for the LintPDF preflight engine.",
  },
  checks: {
    component: ChecksPage,
    title: "Checks Reference",
    description:
      "500+ individual checks across fonts, colors, images, transparency, compliance, barcodes, and packaging geometry.",
  },
  "report-formats": {
    component: ReportFormatsPage,
    title: "Report Formats",
    description: "JSON, PDF, and XML report format documentation.",
  },
  webhooks: {
    component: WebhooksPage,
    title: "Webhooks",
    description: "Register webhook endpoints for real-time event notifications.",
  },
  glossary: {
    component: GlossaryPage,
    title: "Glossary",
    description: "LintPDF terminology reference.",
  },
  "ai-inspections": {
    component: AiInspectionsPage,
    title: "AI Inspections Reference",
    description:
      "Complete reference for all 32 AI inspections across 14 categories.",
  },
  "ai-api": {
    component: AiApiPage,
    title: "AI API Reference",
    description: "API endpoints for AI-powered preflight inspections.",
  },
};

// Canonical ordering for prev/next navigation
const canonicalOrder = allDocSlugs;

export function generateStaticParams() {
  const mdSlugs = getAllDocSlugs();
  const jsxSlugsArr = Object.keys(jsxPages);
  const all = [...new Set([...mdSlugs, ...jsxSlugsArr])];
  return all.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;

  const jsx = jsxPages[slug];
  if (jsx) {
    return {
      title: `${jsx.title} — LintPDF Docs`,
      description: jsx.description,
    };
  }

  const doc = await getDocBySlug(slug);
  if (!doc) return {};

  return {
    title: `${doc.title} — LintPDF Docs`,
    description: doc.description,
  };
}

export default async function DocSlugPage({ params }: Props) {
  const { slug } = await params;

  // Find prev/next in canonical order
  const idx = canonicalOrder.indexOf(slug);
  const prevSlug = idx > 0 ? canonicalOrder[idx - 1] : null;
  const nextSlug =
    idx >= 0 && idx < canonicalOrder.length - 1
      ? canonicalOrder[idx + 1]
      : null;

  // Check JSX registry first
  const jsx = jsxPages[slug];
  if (jsx) {
    const JsxComponent = jsx.component;
    return (
      <>
        <JsxComponent />
        <PrevNextNav prevSlug={prevSlug} nextSlug={nextSlug} />
      </>
    );
  }

  // Fall back to markdown
  const doc = await getDocBySlug(slug);
  if (!doc) notFound();

  return (
    <article>
      <h1 className="text-3xl font-bold text-slate-900 mb-2">{doc.title}</h1>
      {doc.description && (
        <p className="text-slate-500 mb-8">{doc.description}</p>
      )}
      <div
        className="prose prose-slate max-w-none prose-headings:font-bold prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:leading-relaxed prose-p:text-slate-600 prose-a:text-brand-600 prose-a:no-underline hover:prose-a:underline prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono prose-code:before:content-none prose-code:after:content-none prose-pre:bg-brand-950 prose-pre:border prose-pre:border-slate-200 prose-pre:rounded-lg prose-li:text-slate-600 prose-strong:text-slate-800 prose-table:text-sm prose-th:text-left prose-th:py-2 prose-th:px-3 prose-th:text-slate-500 prose-th:font-medium prose-td:py-2 prose-td:px-3"
        // nosemgrep: react-dangerouslysetinnerhtml -- content is sanitized via rehype-sanitize in lib/docs.ts
        dangerouslySetInnerHTML={{ __html: doc.htmlContent ?? "" }}
      />
      <PrevNextNav prevSlug={prevSlug} nextSlug={nextSlug} />
    </article>
  );
}

function PrevNextNav({
  prevSlug,
  nextSlug,
}: {
  prevSlug: string | null;
  nextSlug: string | null;
}) {
  if (!prevSlug && !nextSlug) return null;

  return (
    <nav className="mt-12 pt-6 border-t border-slate-200 grid gap-4 md:grid-cols-2">
      {prevSlug ? (
        <Link
          href={`/docs/${prevSlug}`}
          className="rounded-xl border border-slate-200 p-4 hover:border-brand-200 hover:bg-brand-50/50 transition-all"
        >
          <span className="text-xs text-slate-400 mb-1 block">Previous</span>
          <span className="text-sm font-medium text-slate-700">{prevSlug}</span>
        </Link>
      ) : (
        <div />
      )}
      {nextSlug ? (
        <Link
          href={`/docs/${nextSlug}`}
          className="rounded-xl border border-slate-200 p-4 hover:border-brand-200 hover:bg-brand-50/50 transition-all text-right"
        >
          <span className="text-xs text-slate-400 mb-1 block">Next</span>
          <span className="text-sm font-medium text-slate-700">{nextSlug}</span>
        </Link>
      ) : (
        <div />
      )}
    </nav>
  );
}
