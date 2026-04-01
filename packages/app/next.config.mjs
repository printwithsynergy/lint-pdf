/** @type {import("next").NextConfig} */
const config = {
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: true,
  transpilePackages: [
    "@thinkneverland/pixie-dust-api-keys",
    "@thinkneverland/pixie-dust-auth",
    "@thinkneverland/pixie-dust-boilerplate",
    "@thinkneverland/pixie-dust-config",
    "@thinkneverland/pixie-dust-cookie-consent",
    "@thinkneverland/pixie-dust-core",
    "@thinkneverland/pixie-dust-dashboard",
    "@thinkneverland/pixie-dust-devtools",
    "@thinkneverland/pixie-dust-email",
    "@thinkneverland/pixie-dust-fairy-ring",
    "@thinkneverland/pixie-dust-stripe-kit",
    "@thinkneverland/pixie-dust-theme-default",
    "@thinkneverland/pixie-dust-theme-kit",
    "@thinkneverland/pixie-dust-ui",
    "@thinkneverland/pixie-dust-usage",
    "@thinkneverland/pixie-dust-waitlist",
    "@thinkneverland/pixie-dust-webhooks",
    "@thinkneverland/grounded-plugin",
    "@lintpdf/stripe",
  ],
  serverExternalPackages: [
    "@prisma/client",
    "@prisma/adapter-pg",
    "@thinkneverland/pixie-dust-database",
  ],
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push("crypto");
    }
    // Provide empty fallbacks for Node.js built-ins encountered during
    // edge/instrumentation compilation (pixie-dust-database → pg chain).
    // serverExternalPackages only applies to the Node.js server bundle;
    // the instrumentation bundle uses the edge webpack config where the
    // package is still traversed statically.
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      path: false,
      stream: false,
      net: false,
      tls: false,
      dns: false,
    };
    // Handle node: protocol URIs used by @prisma/client@7.x ESM runtime.
    // resolve.fallback only covers bare imports (e.g. 'fs'); the node:
    // URI scheme needs resolve.alias to provide empty stubs.
    config.resolve.alias = {
      ...config.resolve.alias,
      "node:crypto": false,
      "node:fs": false,
      "node:module": false,
      "node:os": false,
      "node:path": false,
    };
    return config;
  },
};

export default config;
