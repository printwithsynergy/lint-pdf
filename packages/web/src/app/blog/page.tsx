import type { Metadata } from "next";
import { getAllPosts, BLOG_CATEGORIES } from "@/lib/blog";
import { BlogFilters } from "./BlogFilters";

export const metadata: Metadata = {
  title: "Blog — LintPDF",
  description:
    "Product updates, prepress tips, API guides, and industry news from the LintPDF team.",
};

export default function BlogPage() {
  const posts = getAllPosts();

  return (
    <main className="py-16">
      <div className="mx-auto max-w-4xl px-6">
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Blog</h1>
          <p className="text-slate-500">
            Product updates, prepress tips, API guides, and industry news from
            the LintPDF team.
          </p>
        </div>

        <BlogFilters posts={posts} categories={[...BLOG_CATEGORIES]} />
      </div>
    </main>
  );
}
