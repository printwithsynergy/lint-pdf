import path from "node:path";
import { defineConfig, env } from "prisma/config";

export default defineConfig({
  schema: path.join(__dirname, "prisma", "schema"),
  datasource: {
    url: env("DATABASE_URL"),
    directUrl: process.env.DIRECT_URL,
  },
});
