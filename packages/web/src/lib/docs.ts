import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { remark } from "remark";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkRehype from "remark-rehype";
import rehypeStringify from "rehype-stringify";

// rehype-sanitize's default schema strips GFM table tags in some combinations.
// Extend it to explicitly allow the table surface so remark-gfm's output
// survives sanitisation.
const gfmSchema = {
  ...defaultSchema,
  tagNames: [
    ...(defaultSchema.tagNames ?? []),
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    "colgroup",
    "col",
  ],
  attributes: {
    ...(defaultSchema.attributes ?? {}),
    th: [...((defaultSchema.attributes ?? {}).th ?? []), "align", "scope"],
    td: [...((defaultSchema.attributes ?? {}).td ?? []), "align"],
  },
};

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
    .use(remarkGfm)
    .use(remarkRehype)
    .use(rehypeSanitize, gfmSchema)
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
