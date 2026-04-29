import type { Metadata } from "next";
import Link from "next/link";
import { OSS_REPO_URL, ossRepoIsLive } from "@/lib/site-mode";

export const metadata: Metadata = {
  title: "Engine — lintPDF",
  description:
    "The detection-only PDF preflight engine that powers lintPDF. " +
    "Inspect color spaces, fonts, images, transparency, and packaging " +
    "geometry without modifying a single byte.",
};

export default function EnginePage() {
  const repoLive = ossRepoIsLive();

  return (
    <main className="mx-auto max-w-3xl px-6 py-20 md:py-28">
      <header className="mb-10">
        <p className="text-sm font-medium uppercase tracking-wide text-brand-700">
          Engine
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
          The detection-only PDF preflight engine
        </h1>
        <p className="mt-4 text-lg text-slate-600 leading-relaxed">
          The same engine that powers lintPDF. It reads PDFs and reports
          what&rsquo;s wrong with them — color spaces, fonts, images,
          transparency, page geometry, packaging geometry, barcodes — without
          touching a single byte of the input file.
        </p>
      </header>

      <section className="mb-10 rounded-2xl border border-slate-200 bg-white p-6 md:p-8 shadow-sm">
        {repoLive && OSS_REPO_URL ? (
          <>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Available now
            </div>
            <h2 className="text-2xl font-semibold text-slate-900 mb-2">
              Open source
            </h2>
            <p className="text-slate-600 mb-6">
              The engine is published on GitHub. Clone it, run it locally, or
              build on top of it. Documentation lives alongside the source.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href={OSS_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl bg-brand-900 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-800"
              >
                View on GitHub
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 0a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.2c-3.34.73-4.04-1.43-4.04-1.43-.55-1.39-1.34-1.76-1.34-1.76-1.09-.74.08-.73.08-.73 1.21.09 1.84 1.24 1.84 1.24 1.07 1.83 2.81 1.3 3.5.99.11-.78.42-1.3.76-1.6-2.66-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.11-3.18 0 0 1.01-.32 3.31 1.23a11.5 11.5 0 0 1 6.02 0c2.3-1.55 3.31-1.23 3.31-1.23.65 1.66.24 2.88.12 3.18.77.84 1.23 1.91 1.23 3.22 0 4.61-2.81 5.62-5.49 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58A12 12 0 0 0 12 0Z" />
                </svg>
              </a>
            </div>
          </>
        ) : (
          <>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-400" />
              Coming soon
            </div>
            <h2 className="text-2xl font-semibold text-slate-900 mb-2">
              Open source — in progress
            </h2>
            <p className="text-slate-600 mb-6">
              The OSS release is in preparation. When it ships you&rsquo;ll
              be able to run the engine locally, inspect the source, and
              contribute back. The OSS engine will have its own documentation
              site published alongside the repository.
            </p>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 rounded-xl border-2 border-slate-200 px-6 py-3 text-sm font-medium text-slate-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
            >
              Get in touch
            </Link>
          </>
        )}
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="text-base font-semibold text-slate-900 mb-2">
            Detection-only
          </h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Reads the PDF, never writes. Your input file is byte-identical
            when we&rsquo;re done. No silent fixes, no re-distillation, no
            &ldquo;preserved&rdquo; metadata that quietly changed.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="text-base font-semibold text-slate-900 mb-2">
            Standards-aware
          </h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            PDF/X-1a, PDF/X-3, PDF/X-4, PDF/A, ISO 15930, GWG 2022. The check
            catalog covers fonts, color spaces, images, transparency, page
            geometry, packaging dielines, and barcodes.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="text-base font-semibold text-slate-900 mb-2">
            Built for prepress
          </h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Written by people who shipped print jobs for a living. The check
            catalog reflects what actually breaks at press, not what looks
            tidy in a spec PDF.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="text-base font-semibold text-slate-900 mb-2">
            Programmable
          </h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            The engine ships with a CLI and a Python API. Wire it into a hot
            folder, a CI pipeline, or your existing prepress automation
            without rewriting anything.
          </p>
        </div>
      </section>
    </main>
  );
}
