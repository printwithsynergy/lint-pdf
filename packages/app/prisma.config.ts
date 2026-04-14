import path from "node:path";
import { defineConfig, env } from "prisma/config";

// Fall back to a dummy URL so ``prisma generate`` (which only needs the
// schema, not the live database) works during ``pnpm install`` and CI
// typechecks where DATABASE_URL isn't provided. Runtime clients still
// read the real value from ``process.env.DATABASE_URL``.
const databaseUrl = process.env.DATABASE_URL
  ? env("DATABASE_URL")
  : "postgresql://user:pass@localhost:5432/placeholder";

export default defineConfig({
  schema: path.join(__dirname, "prisma", "schema"),
  datasource: {
    url: databaseUrl,
  },
});
