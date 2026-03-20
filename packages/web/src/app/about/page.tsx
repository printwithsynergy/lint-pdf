import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About — LintPDF",
  description:
    "LintPDF is a detection-only PDF preflight engine built by Think Neverland. Learn about our philosophy, standards commitment, and the team behind the product.",
};

export default function AboutPage() {
  return (
    <main>
      {/* Hero */}
      <section className="bg-brand-50/50 pt-20 pb-16">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h1 className="text-4xl font-bold text-slate-900 md:text-5xl mb-4">
            Built by prepress veterans
          </h1>
          <p className="text-lg text-slate-500">
            LintPDF exists because the print industry deserves better tooling.
            Comprehensive preflight, modern API, transparent pricing — no sales
            calls required.
          </p>
        </div>
      </section>

      {/* Think Neverland */}
      <section className="py-16">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Think Neverland
          </h2>
          <p className="text-slate-600 mb-4 leading-relaxed">
            LintPDF is built by{" "}
            <a
              href="https://thinkneverland.com"
              className="text-brand-600 hover:underline font-medium"
              target="_blank"
              rel="noopener noreferrer"
            >
              Think Neverland
            </a>
            , a product studio focused on developer tools for the print and
            publishing industry. We have spent years inside prepress operations,
            print automation systems, and web-to-print platforms. We know what
            breaks, what gets missed, and what costs money when it reaches the
            press.
          </p>
          <p className="text-slate-600 mb-4 leading-relaxed">
            We built LintPDF because the preflight tools available today fall
            into two camps: enterprise software that requires a sales call and a
            six-figure contract, or developer APIs that check a few boxes but
            miss the depth that real print production demands. Neither option
            works for the 45,000+ web-to-print platforms worldwide that need
            automated, comprehensive PDF validation at scale.
          </p>
          <p className="text-slate-600 leading-relaxed">
            LintPDF fills that gap. Comprehensive print preflight, delivered
            through a REST API, with self-service signup and transparent
            per-file pricing. The Stripe for PDF preflight.
          </p>
        </div>
      </section>

      {/* Detection-Only Philosophy */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Detection-only by design
          </h2>
          <p className="text-slate-600 mb-4 leading-relaxed">
            LintPDF is detection-only. We inspect your files and report what we
            find. We never modify, re-save, or alter your originals. This is not
            a limitation — it is a deliberate product decision and one of our
            strongest selling points.
          </p>
          <p className="text-slate-600 mb-4 leading-relaxed">
            Automated PDF correction sounds appealing until a tool re-renders
            your transparency wrong, drops an ICC profile, or re-encodes an
            image at lower quality. The cost of a single damaged file in a
            production print run far exceeds the cost of detecting the issue and
            letting a human decide how to resolve it.
          </p>
          <p className="text-slate-600 leading-relaxed">
            LintPDF gives you the information. You make the decisions. Your
            files stay exactly as they were — byte for byte, every time. Zero
            risk of file damage, zero surprises on press.
          </p>
        </div>
      </section>

      {/* Standards */}
      <section className="py-16">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Open standards commitment
          </h2>
          <p className="text-slate-600 mb-6 leading-relaxed">
            LintPDF validates against the standards that the print industry
            relies on. We do not invent our own criteria — we implement the
            specifications that ISO, the Ghent Workgroup, and the PDF
            Association have spent decades refining.
          </p>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="font-semibold text-slate-900 mb-2">ISO 32000-2</h3>
              <p className="text-sm text-slate-500">
                The PDF 2.0 specification. LintPDF supports all PDF versions
                through 2.0.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="font-semibold text-slate-900 mb-2">
                ISO 15930 (PDF/X)
              </h3>
              <p className="text-sm text-slate-500">
                PDF/X-4, PDF/X-1a, and PDF/X-3 conformance validation for print
                exchange.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="font-semibold text-slate-900 mb-2">GWG 2022</h3>
              <p className="text-sm text-slate-500">
                Ghent Workgroup specifications for sheetfed offset and digital
                printing workflows.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="font-semibold text-slate-900 mb-2">ISO 15416</h3>
              <p className="text-sm text-slate-500">
                Barcode print quality grading. LintPDF decodes and grades
                barcodes per this standard.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            See what LintPDF can detect
          </h2>
          <p className="text-slate-500 mb-8">
            250+ checks across fonts, color spaces, images, transparency, page
            geometry, compliance, and barcodes.
          </p>
          <Link
            href="/docs"
            className="inline-block rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
          >
            Read the Docs
          </Link>
        </div>
      </section>
    </main>
  );
}
