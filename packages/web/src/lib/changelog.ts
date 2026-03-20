import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { remark } from "remark";
import rehypeSanitize from "rehype-sanitize";
import remarkRehype from "remark-rehype";
import rehypeStringify from "rehype-stringify";

const CHANGELOG_DIR = path.join(process.cwd(), "src/content/changelog");

export interface ChangelogEntry {
  slug: string;
  version: string;
  date: string;
  title: string;
  content: string;
  htmlContent?: string;
}

function parseEntry(fileName: string): ChangelogEntry {
  const slug = fileName.replace(/\.md$/, "");
  const filePath = path.join(CHANGELOG_DIR, fileName);
  const fileContents = fs.readFileSync(filePath, "utf8");
  const { data, content } = matter(fileContents);

  return {
    slug,
    version: data.version ?? slug,
    date: data.date ?? "",
    title: data.title ?? "",
    content,
  };
}

export function getAllEntries(): ChangelogEntry[] {
  if (!fs.existsSync(CHANGELOG_DIR)) return [];
  const files = fs.readdirSync(CHANGELOG_DIR).filter((f) => f.endsWith(".md"));
  return files
    .map(parseEntry)
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

export function getEntriesWithHtml(): Promise<ChangelogEntry[]> {
  const entries = getAllEntries();
  return Promise.all(
    entries.map(async (entry) => {
      const result = await remark()
        .use(remarkRehype)
        .use(rehypeSanitize)
        .use(rehypeStringify)
        .process(entry.content);
      return { ...entry, htmlContent: result.toString() };
    }),
  );
}
