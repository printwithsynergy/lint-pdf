import type { MetadataRoute } from "next";
import { getAllPosts } from "@/lib/blog";
import { isOssMode } from "@/lib/site-mode";

const BASE_URL = "https://lintpdf.com";

interface SitemapEntry {
  path: string;
  changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
  priority: number;
  ossPublic: boolean;
}

const STATIC_ENTRIES: SitemapEntry[] = [
  { path: "", changeFrequency: "weekly", priority: 1.0, ossPublic: true },
  { path: "/features", changeFrequency: "monthly", priority: 0.9, ossPublic: true },
  { path: "/engine", changeFrequency: "monthly", priority: 0.9, ossPublic: true },
  { path: "/about", changeFrequency: "monthly", priority: 0.7, ossPublic: true },
  { path: "/contact", changeFrequency: "monthly", priority: 0.6, ossPublic: true },
  { path: "/status", changeFrequency: "daily", priority: 0.5, ossPublic: true },
  { path: "/compliance", changeFrequency: "monthly", priority: 0.5, ossPublic: true },
  { path: "/pricing", changeFrequency: "monthly", priority: 0.9, ossPublic: false },
  { path: "/docs", changeFrequency: "weekly", priority: 0.9, ossPublic: false },
  { path: "/blog", changeFrequency: "weekly", priority: 0.8, ossPublic: false },
  { path: "/changelog", changeFrequency: "weekly", priority: 0.6, ossPublic: false },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const ossMode = isOssMode();
  const lastModified = new Date();

  const staticPages: MetadataRoute.Sitemap = STATIC_ENTRIES
    .filter((entry) => !ossMode || entry.ossPublic)
    .map((entry) => ({
      url: `${BASE_URL}${entry.path}`,
      lastModified,
      changeFrequency: entry.changeFrequency,
      priority: entry.priority,
    }));

  // Blog posts and other product surfaces are SaaS-only. In OSS mode the
  // /blog index is hidden, so individual post URLs would be link-orphans
  // even if listed here.
  const blogPosts: MetadataRoute.Sitemap = ossMode
    ? []
    : getAllPosts().map((post) => ({
        url: `${BASE_URL}/blog/${post.slug}`,
        lastModified: new Date(post.date),
        changeFrequency: "monthly" as const,
        priority: 0.6,
      }));

  return [...staticPages, ...blogPosts];
}
