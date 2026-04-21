import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAdminDocBySlug, getAllAdminDocs } from "@/lib/admin-docs";
import {
  adminDocSectionsByKey,
  allAdminDocSlugs,
  type AdminDocSection,
} from "@/lib/admin-doc-sections";

interface Props {
  params: Promise<{ slug: string[] }>;
}

export function generateStaticParams() {
  const mdSlugs = getAllAdminDocs().map((d) => d.slug);
  const groupKeys = Object.keys(adminDocSectionsByKey);
  const all = [...new Set([...mdSlugs, ...groupKeys])];
  return all.map((slug) => ({ slug: slug.split("/") }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const joined = slug.join("/");

  const group = adminDocSectionsByKey[joined];
  if (group) {
    return { title: `${group.heading} — Admin docs`, description: group.blurb };
  }

  const doc = await getAdminDocBySlug(joined);
  if (!doc) return {};
  return {
    title: `${doc.title} — Admin docs`,
    description: doc.description,
  };
}

export default async function AdminDocPage({ params }: Props) {
  const { slug } = await params;
  const joined = slug.join("/");

  // Group-index page: e.g. /dashboard/admin/docs/panels
  const group = adminDocSectionsByKey[joined];
  if (group) {
    return <GroupIndex section={group} />;
  }

  const doc = await getAdminDocBySlug(joined);
  if (!doc) notFound();

  const canonicalIdx = allAdminDocSlugs.indexOf(joined);
  const prevSlug = canonicalIdx > 0 ? allAdminDocSlugs[canonicalIdx - 1] : null;
  const nextSlug =
    canonicalIdx >= 0 && canonicalIdx < allAdminDocSlugs.length - 1
      ? allAdminDocSlugs[canonicalIdx + 1]
      : null;

  return (
    <article className="max-w-3xl">
      <div className="mb-6">
        <Link
          href="/dashboard/admin/docs"
          className="text-xs text-muted-foreground hover:text-brand-700"
        >
          ← Admin docs
        </Link>
      </div>
      <h1 className="text-2xl sm:text-3xl font-bold mb-2">{doc.title}</h1>
      {doc.description ? (
        <p className="text-muted-foreground mb-8">{doc.description}</p>
      ) : null}
      <div
        className="prose prose-slate max-w-none prose-headings:font-bold prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:leading-relaxed prose-p:text-slate-600 prose-a:text-brand-600 prose-a:no-underline hover:prose-a:underline prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono prose-code:before:content-none prose-code:after:content-none prose-pre:bg-brand-950 prose-pre:text-slate-300 prose-pre:border prose-pre:border-slate-200 prose-pre:rounded-lg prose-li:text-slate-600 prose-strong:text-slate-800 prose-table:text-sm prose-th:text-left prose-th:py-2 prose-th:px-3 prose-th:text-slate-500 prose-th:font-medium prose-td:py-2 prose-td:px-3"
        // nosemgrep: react-dangerouslysetinnerhtml -- sanitized via rehype-sanitize in lib/admin-docs.ts
        dangerouslySetInnerHTML={{ __html: doc.htmlContent ?? "" }}
      />
      <PrevNext prevSlug={prevSlug ?? null} nextSlug={nextSlug ?? null} />
    </article>
  );
}

function GroupIndex({ section }: { section: AdminDocSection }) {
  return (
    <article className="max-w-5xl">
      <div className="mb-6">
        <Link
          href="/dashboard/admin/docs"
          className="text-xs text-muted-foreground hover:text-brand-700"
        >
          ← Admin docs
        </Link>
      </div>
      <h1 className="text-2xl sm:text-3xl font-bold mb-2">{section.heading}</h1>
      <p className="text-muted-foreground mb-8">{section.blurb}</p>
      <ul className="grid gap-4 sm:grid-cols-2">
        {section.items.map((item) => (
          <li key={item.slug}>
            <Link
              href={`/dashboard/admin/docs/${item.slug}`}
              className="block rounded-xl border border-border p-4 hover:border-brand-200 hover:bg-brand-50/40 transition-all h-full"
            >
              <span className="block text-sm font-semibold">{item.label}</span>
              {item.description ? (
                <span className="mt-1 block text-sm text-muted-foreground">
                  {item.description}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </article>
  );
}

function PrevNext({
  prevSlug,
  nextSlug,
}: {
  prevSlug: string | null;
  nextSlug: string | null;
}) {
  if (!prevSlug && !nextSlug) return null;
  return (
    <nav className="mt-12 pt-6 border-t border-border grid gap-4 md:grid-cols-2">
      {prevSlug ? (
        <Link
          href={`/dashboard/admin/docs/${prevSlug}`}
          className="rounded-xl border border-border p-4 hover:border-brand-200 hover:bg-brand-50/40 transition-all"
        >
          <span className="text-xs text-muted-foreground mb-1 block">
            Previous
          </span>
          <span className="text-sm font-medium">{prevSlug}</span>
        </Link>
      ) : (
        <div />
      )}
      {nextSlug ? (
        <Link
          href={`/dashboard/admin/docs/${nextSlug}`}
          className="rounded-xl border border-border p-4 hover:border-brand-200 hover:bg-brand-50/40 transition-all text-right"
        >
          <span className="text-xs text-muted-foreground mb-1 block">
            Next
          </span>
          <span className="text-sm font-medium">{nextSlug}</span>
        </Link>
      ) : (
        <div />
      )}
    </nav>
  );
}
