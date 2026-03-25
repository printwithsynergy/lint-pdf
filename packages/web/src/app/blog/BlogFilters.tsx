"use client";

import { useState } from "react";
import Link from "next/link";
import type { BlogPost } from "@/lib/blog";

interface Props {
  posts: BlogPost[];
  categories: string[];
}

export function BlogFilters({ posts, categories }: Props) {
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const filtered =
    activeCategory === "All"
      ? posts
      : posts.filter((p) => p.category === activeCategory);

  return (
    <>
      {/* Category filters */}
      <div className="flex flex-wrap gap-2 mb-8">
        <button
          type="button"
          onClick={() => setActiveCategory("All")}
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
            activeCategory === "All"
              ? "bg-brand-900 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-brand-50 hover:text-brand-700"
          }`}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(cat)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              activeCategory === cat
                ? "bg-brand-900 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-brand-50 hover:text-brand-700"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Post cards */}
      {filtered.length === 0 ? (
        <p className="text-slate-500 text-center py-12">
          No posts in this category yet.
        </p>
      ) : (
        <div className="space-y-6">
          {filtered.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="block rounded-xl border border-slate-200 bg-white p-6 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-brand-200"
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="rounded-full bg-brand-50 px-3 py-0.5 text-xs font-medium text-brand-700">
                  {post.category}
                </span>
                <time className="text-xs text-slate-400" dateTime={post.date}>
                  {new Date(post.date).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </time>
              </div>
              <h2 className="text-xl font-semibold text-slate-900 mb-2">
                {post.title}
              </h2>
              <p className="text-sm text-slate-500 leading-relaxed">
                {post.excerpt}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {post.tags.map((tag) => (
                  <span key={tag} className="text-xs text-slate-400">
                    #{tag}
                  </span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
