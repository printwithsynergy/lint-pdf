import Link from "next/link";

export function TryItCTA() {
  return (
    <section className="relative py-20 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-50 via-white to-brand-100/50" />
      <div className="relative mx-auto max-w-3xl px-6 text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-100">
          <svg
            className="h-8 w-8 text-brand-700"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        <h2 className="text-3xl font-bold text-slate-900 md:text-4xl mb-4">
          Got Messy PDFs?{" "}
          <span className="bg-gradient-to-r from-brand-800 via-brand-600 to-brand-400 bg-clip-text text-transparent">
            We&rsquo;ll Sort Them Out.
          </span>
        </h2>
        <p className="text-slate-500 mb-8 text-lg max-w-xl mx-auto">
          Upload your files and get a free preflight report — no account needed.
          See exactly what our engine catches.
        </p>
        <Link
          href="/try-it"
          className="inline-flex items-center gap-2 rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
        >
          Upload Your Files
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
              d="M14 5l7 7m0 0l-7 7m7-7H3"
            />
          </svg>
        </Link>
      </div>
    </section>
  );
}
