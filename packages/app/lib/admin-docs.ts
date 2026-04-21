import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { remark } from "remark";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkRehype from "remark-rehype";
import rehypeStringify from "rehype-stringify";

const DOCS_DIR = path.join(process.cwd(), "content/docs-admin");

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

export interface AdminDocPage {
  /** Slug relative to content/docs-admin/, e.g. "panels/webhooks" or "runbooks/dlq-replay". */
  slug: string;
  /** Frontmatter title. */
  title: string;
  /** Frontmatter description. */
  description: string;
  /** Raw markdown body. */
  content: string;
  /** Rendered HTML (set on getAdminDocBySlug). */
  htmlContent?: string;
}

function parseFile(fullPath: string, slug: string): AdminDocPage {
  const fileContents = fs.readFileSync(fullPath, "utf8");
  const { data, content } = matter(fileContents);
  return {
    slug,
    title: data.title ?? slug,
    description: data.description ?? "",
    content,
  };
}

/**
 * Walk ``content/docs-admin/`` recursively and return every ``.md`` page.
 * Slugs include the directory prefix: ``panels/webhooks``, ``runbooks/dlq-replay``.
 */
export function getAllAdminDocs(): AdminDocPage[] {
  if (!fs.existsSync(DOCS_DIR)) return [];
  const pages: AdminDocPage[] = [];
  function walk(dir: string, prefix: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full, prefix ? `${prefix}/${entry.name}` : entry.name);
      } else if (entry.isFile() && entry.name.endsWith(".md")) {
        const base = entry.name.replace(/\.md$/, "");
        const slug = prefix ? `${prefix}/${base}` : base;
        pages.push(parseFile(full, slug));
      }
    }
  }
  walk(DOCS_DIR, "");
  return pages.sort((a, b) => a.slug.localeCompare(b.slug));
}

export async function getAdminDocBySlug(
  slug: string,
): Promise<AdminDocPage | null> {
  // Path traversal guard: reject any slug that would escape DOCS_DIR.
  const safeSlug = slug.replace(/^\/+|\/+$/g, "");
  if (safeSlug.includes("..")) return null;

  const fullPath = path.join(DOCS_DIR, `${safeSlug}.md`);
  // Resolve + prefix check so a crafted slug like "../../secret" can't
  // read anything outside the content tree even if the naive ".." check
  // above is sidestepped.
  const resolved = path.resolve(fullPath);
  if (!resolved.startsWith(path.resolve(DOCS_DIR))) return null;
  if (!fs.existsSync(resolved)) return null;

  const doc = parseFile(resolved, safeSlug);
  const result = await remark()
    .use(remarkGfm)
    .use(remarkRehype)
    .use(rehypeSanitize, gfmSchema)
    .use(rehypeStringify)
    .process(doc.content);
  doc.htmlContent = result.toString();
  return doc;
}
