import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { remark } from "remark";
import rehypeSanitize from "rehype-sanitize";
import remarkRehype from "remark-rehype";
import rehypeStringify from "rehype-stringify";

const DOCS_DIR = path.join(process.cwd(), "src/content/docs");

export interface DocPage {
  slug: string;
  title: string;
  description: string;
  section: string;
  order: number;
  content: string;
  htmlContent?: string;
}

function parseDoc(fileName: string): DocPage {
  const slug = fileName.replace(/\.md$/, "");
  const filePath = path.join(DOCS_DIR, fileName);
  const fileContents = fs.readFileSync(filePath, "utf8");
  const { data, content } = matter(fileContents);

  return {
    slug,
    title: data.title ?? "",
    description: data.description ?? "",
    section: data.section ?? "core",
    order: data.order ?? 99,
    content,
  };
}

export function getAllDocs(): DocPage[] {
  if (!fs.existsSync(DOCS_DIR)) return [];
  const files = fs.readdirSync(DOCS_DIR).filter((f) => f.endsWith(".md"));
  return files.map(parseDoc).sort((a, b) => a.order - b.order);
}

export function getDocsBySection(section: string): DocPage[] {
  return getAllDocs().filter((d) => d.section === section);
}

export async function getDocBySlug(slug: string): Promise<DocPage | null> {
  const filePath = path.join(DOCS_DIR, `${slug}.md`);
  if (!fs.existsSync(filePath)) return null;

  const doc = parseDoc(`${slug}.md`);
  const result = await remark()
    .use(remarkRehype)
    .use(rehypeSanitize)
    .use(rehypeStringify)
    .process(doc.content);
  doc.htmlContent = result.toString();
  return doc;
}

export function getAllDocSlugs(): string[] {
  if (!fs.existsSync(DOCS_DIR)) return [];
  return fs
    .readdirSync(DOCS_DIR)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""));
}
