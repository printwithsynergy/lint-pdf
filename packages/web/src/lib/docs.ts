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

function parseDocAt(fullPath: string, slug: string): DocPage {
  const fileContents = fs.readFileSync(fullPath, "utf8");
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

/**
 * Walk ``content/docs`` recursively and collect every ``.md`` file.
 * Slugs include the directory prefix: ``panels/api-keys``, etc.
 */
function walkDocs(): DocPage[] {
  if (!fs.existsSync(DOCS_DIR)) return [];
  const out: DocPage[] = [];
  function walk(dir: string, prefix: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full, prefix ? `${prefix}/${entry.name}` : entry.name);
      } else if (entry.isFile() && entry.name.endsWith(".md")) {
        const base = entry.name.replace(/\.md$/, "");
        const slug = prefix ? `${prefix}/${base}` : base;
        out.push(parseDocAt(full, slug));
      }
    }
  }
  walk(DOCS_DIR, "");
  return out;
}

export function getAllDocs(): DocPage[] {
  return walkDocs().sort((a, b) => a.order - b.order);
}

export function getDocsBySection(section: string): DocPage[] {
  return getAllDocs().filter((d) => d.section === section);
}

export async function getDocBySlug(slug: string): Promise<DocPage | null> {
  // Path traversal guard: reject any slug that would escape DOCS_DIR.
  const safeSlug = slug.replace(/^\/+|\/+$/g, "");
  if (safeSlug.includes("..")) return null;

  const fullPath = path.join(DOCS_DIR, `${safeSlug}.md`);
  const resolved = path.resolve(fullPath);
  if (!resolved.startsWith(path.resolve(DOCS_DIR))) return null;
  if (!fs.existsSync(resolved)) return null;

  const doc = parseDocAt(resolved, safeSlug);
  // The renderer shows a hero block (title + description from frontmatter)
  // before the body, so drop the markdown's leading `# …` heading when
  // present to avoid a duplicate title. A regex-based strip is fine — the
  // pattern anchors at the start of the file and matches one heading line.
  const body = doc.content.replace(/^\s*#\s+[^\n]+\n+/, "");
  const result = await remark()
    .use(remarkGfm)
    .use(remarkRehype)
    .use(rehypeSanitize, gfmSchema)
    .use(rehypeStringify)
    .process(body);
  doc.htmlContent = result.toString();
  return doc;
}

export function getAllDocSlugs(): string[] {
  return walkDocs().map((d) => d.slug);
}
