import type { Metadata } from "next";
import { getEntriesWithHtml } from "@/lib/changelog";

export const metadata: Metadata = {
  title: "Changelog — Never Grounded",
  description:
    "The Logbook — version history and release notes for the Never Grounded PDF preflight engine.",
};

export default async function ChangelogPage() {
  const entries = await getEntriesWithHtml();

  return (
    // skipcq: JS-0415
    <main className="py-16">
      <div className="mx-auto max-w-3xl px-6">
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Changelog</h1>
          <p className="text-sm text-brand-500 italic mb-4">The Logbook</p>
          <p className="text-slate-500">
            Version history and release notes for the Never Grounded preflight
            engine and API.
          </p>
        </div>

        <div className="space-y-12">
          {entries.map((entry) => (
            <article
              key={entry.version}
              className="relative pl-8 border-l-2 border-brand-200"
            >
              <div className="absolute -left-2.5 top-0 h-5 w-5 rounded-full border-2 border-brand-400 bg-white" />
              <div className="mb-4">
                <div className="flex items-center gap-3 mb-1">
                  <span className="rounded-full bg-brand-900 px-3 py-0.5 text-xs font-bold text-white">
                    v{entry.version}
                  </span>
                  <time
                    className="text-sm text-slate-400"
                    dateTime={entry.date}
                  >
                    {new Date(entry.date).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </time>
                </div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {entry.title}
                </h2>
              </div>
              <div
                className="prose prose-sm prose-slate max-w-none prose-headings:font-semibold prose-h3:text-base prose-h3:mt-6 prose-h3:mb-2 prose-p:text-slate-600 prose-li:text-slate-600 prose-strong:text-slate-800 prose-code:bg-slate-100 prose-code:px-1 prose-code:rounded prose-code:text-xs prose-code:font-mono prose-code:before:content-none prose-code:after:content-none"
                // nosemgrep: react-dangerouslysetinnerhtml -- content is sanitized via rehype-sanitize in lib/changelog.ts
                dangerouslySetInnerHTML={{ __html: entry.htmlContent ?? "" }} // skipcq: JS-0440
              />
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
