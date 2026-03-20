import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPostBySlug, getAllSlugs, getAllPosts } from "@/lib/blog";

interface Props {
  params: Promise<{ slug: string }>;
}

export function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPostBySlug(slug);
  if (!post) return {};

  return {
    title: `${post.title} — Never Grounded Blog`,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: "article",
      publishedTime: post.date,
      authors: [post.author],
    },
  };
}

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params;
  const post = await getPostBySlug(slug);
  if (!post) notFound();

  const allPosts = getAllPosts();
  const currentIndex = allPosts.findIndex((p) => p.slug === slug);
  const prevPost =
    currentIndex < allPosts.length - 1 ? allPosts[currentIndex + 1] : null;
  const nextPost = currentIndex > 0 ? allPosts[currentIndex - 1] : null;

  return (
    <main className="py-16">
      <article className="mx-auto max-w-3xl px-6">
        <Link
          href="/blog"
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-700 transition-colors mb-8"
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to Blog
        </Link>

        <header className="mb-10">
          <div className="flex items-center gap-3 mb-4">
            <span className="rounded-full bg-brand-50 px-3 py-0.5 text-xs font-medium text-brand-700">
              {post.category}
            </span>
            <time className="text-sm text-slate-400" dateTime={post.date}>
              {new Date(post.date).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </time>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 md:text-4xl mb-3">
            {post.title}
          </h1>
          <p className="text-slate-500">By {post.author}</p>
        </header>

        <div
          className="prose prose-slate max-w-none prose-headings:font-bold prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:leading-relaxed prose-p:text-slate-600 prose-a:text-brand-600 prose-a:no-underline hover:prose-a:underline prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono prose-code:before:content-none prose-code:after:content-none prose-pre:bg-brand-950 prose-pre:border prose-pre:border-slate-200 prose-pre:rounded-lg prose-li:text-slate-600 prose-strong:text-slate-800"
          // nosemgrep: react-dangerouslysetinnerhtml -- content is sanitized via rehype-sanitize in lib/blog.ts
          dangerouslySetInnerHTML={{ __html: post.htmlContent ?? "" }} // skipcq: JS-0440
        />

        {post.tags.length > 0 && (
          <div className="mt-10 pt-6 border-t border-slate-200 flex flex-wrap gap-2">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-500"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Post navigation */}
        <nav className="mt-10 pt-6 border-t border-slate-200 grid gap-4 md:grid-cols-2">
          {prevPost ? (
            <Link
              href={`/blog/${prevPost.slug}`}
              className="rounded-xl border border-slate-200 p-4 hover:border-brand-200 hover:bg-brand-50/50 transition-all"
            >
              <span className="text-xs text-slate-400 mb-1 block">
                Previous
              </span>
              <span className="text-sm font-medium text-slate-700">
                {prevPost.title}
              </span>
            </Link>
          ) : (
            <div />
          )}
          {nextPost ? (
            <Link
              href={`/blog/${nextPost.slug}`}
              className="rounded-xl border border-slate-200 p-4 hover:border-brand-200 hover:bg-brand-50/50 transition-all text-right"
            >
              <span className="text-xs text-slate-400 mb-1 block">Next</span>
              <span className="text-sm font-medium text-slate-700">
                {nextPost.title}
              </span>
            </Link>
          ) : (
            <div />
          )}
        </nav>
      </article>
    </main>
  );
}
