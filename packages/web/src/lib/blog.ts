import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { remark } from "remark";
import rehypeSanitize from "rehype-sanitize";
import remarkRehype from "remark-rehype";
import rehypeStringify from "rehype-stringify";

const BLOG_DIR = path.join(process.cwd(), "src/content/blog");

export interface BlogPost {
  slug: string;
  title: string;
  date: string;
  author: string;
  category: string;
  excerpt: string;
  tags: string[];
  content: string;
  htmlContent?: string;
}

export const BLOG_CATEGORIES = [
  "Product Updates",
  "Prepress Tips",
  "API Guides",
  "Industry News",
] as const;

export type BlogCategory = (typeof BLOG_CATEGORIES)[number];

function parsePost(fileName: string): BlogPost {
  const slug = fileName.replace(/\.md$/, "");
  const filePath = path.join(BLOG_DIR, fileName);
  const fileContents = fs.readFileSync(filePath, "utf8");
  const { data, content } = matter(fileContents);

  return {
    slug,
    title: data.title ?? "",
    date: data.date ?? "",
    author: data.author ?? "Think Neverland",
    category: data.category ?? "Product Updates",
    excerpt: data.excerpt ?? "",
    tags: data.tags ?? [],
    content,
  };
}

export function getAllPosts(): BlogPost[] {
  if (!fs.existsSync(BLOG_DIR)) return [];
  const files = fs.readdirSync(BLOG_DIR).filter((f) => f.endsWith(".md"));
  return files
    .map(parsePost)
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

export async function getPostBySlug(slug: string): Promise<BlogPost | null> {
  const filePath = path.join(BLOG_DIR, `${slug}.md`);
  if (!fs.existsSync(filePath)) return null;

  const post = parsePost(`${slug}.md`);
  const result = await remark()
    .use(remarkRehype)
    .use(rehypeSanitize)
    .use(rehypeStringify)
    .process(post.content);
  post.htmlContent = result.toString();
  return post;
}

export function getPostsByCategory(category: string): BlogPost[] {
  return getAllPosts().filter((p) => p.category === category);
}

export function getAllSlugs(): string[] {
  if (!fs.existsSync(BLOG_DIR)) return [];
  return fs
    .readdirSync(BLOG_DIR)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""));
}
