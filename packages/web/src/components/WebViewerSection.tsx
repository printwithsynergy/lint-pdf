import Link from "next/link";

const capabilities = [
  {
    title: "Separations & ink channels",
    description:
      "Toggle process (CMYK) and spot channels per page. Isolate single inks, inspect overprint, and verify plate counts without a PitStop preflight run.",
  },
  {
    title: "TAC heatmap + densitometer",
    description:
      "Total Area Coverage overlay flags ink-limit violations at a glance. Click any pixel to read densitometer values across every separation.",
  },
  {
    title: "Layers & optional content",
    description:
      "PDF optional-content groups render as toggleable layers. Dieline, white ink, and varnish layers each get their own visibility switch.",
  },
  {
    title: "File comparison",
    description:
      "Diff two revisions side-by-side with SSIM heatmaps. Catch unintended changes — moved elements, colour shifts, font substitutions — before they ship.",
  },
  {
    title: "Branded share links",
    description:
      "Every job mints a tokenized URL with your logo, colours, and footer. Or flip anonymous mode and strip all branding including PDF metadata.",
  },
  {
    title: "Cloudflare R2 edge caching",
    description:
      "Page tiles are pre-warmed into Cloudflare R2 on ingest. Review-team pageflips load from the closest edge — no cold-render waits.",
  },
];

export function WebViewerSection() {
  return (
    <section id="web-viewer" className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center mb-14">
          <span className="inline-block rounded-full bg-brand-100 px-3 py-1 text-xs font-bold text-brand-700 mb-3">
            Hosted Web Viewer
          </span>
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl mb-4">
            A production-grade PDF viewer your stakeholders can actually use
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto">
            Open any submitted PDF in seconds with separations, TAC, layers,
            and comparison tooling. Share a link — no login required. Or embed
            in your own review workflow.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {capabilities.map((cap) => (
            <div
              key={cap.title}
              className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-1"
            >
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                {cap.title}
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed">
                {cap.description}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-10 rounded-2xl border border-brand-200 bg-brand-50/50 p-6 md:p-8 text-center">
          <h3 className="text-xl font-semibold text-slate-900 mb-2">
            Already running PitStop, callas, or Acrobat preflight?
          </h3>
          <p className="text-slate-600 max-w-2xl mx-auto mb-5">
            The new <span className="font-semibold">Viewer</span> tier lets you
            bring your own preflight report and host it in our interactive
            Web Viewer — branded share links, anonymous output, no engine run
            needed. Starts at $15 / month.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/pricing"
              className="rounded-xl bg-brand-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-800 shadow-md shadow-brand-200"
            >
              See Viewer tier pricing
            </Link>
            <Link
              href="/docs/viewer-only-mode"
              className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-200"
            >
              Read the docs
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
