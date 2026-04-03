import path from "node:path";
import { defineConfig } from "prisma/config";

export default defineConfig({
  schema: path.join(__dirname, "prisma", "schema"),
  datasource: {
    url: process.env.DATABASE_URL ?? process.env.DIRECT_URL ?? "",
  },
});
