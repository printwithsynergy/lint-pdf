import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // In a pnpm monorepo, dependencies are hoisted to the workspace root.
  // This tells Next.js file tracing to start from the monorepo root so
  // hoisted deps (like 'next' itself) are included in standalone output.
  outputFileTracingRoot: path.join(__dirname, "../../"),
};

export default nextConfig;
