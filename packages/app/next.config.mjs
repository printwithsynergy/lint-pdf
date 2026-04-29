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
  // Legacy /dashboard/endpoints surface was hard-removed in PR 26.
  // Old bookmarks land on the Workflows page so customers don't see
  // a 404; 308 keeps the method semantics for any rare POST/PATCH
  // that survives in scripts (Workflows ignores them, but at least
  // the redirect doesn't break payload visibility).
  async redirects() {
    return [
      {
        source: "/dashboard/endpoints",
        destination: "/dashboard/workflows",
        permanent: true,
      },
      {
        source: "/dashboard/endpoints/:path*",
        destination: "/dashboard/workflows",
        permanent: true,
      },
    ];
  },
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
    "@thinkneverland/lintpdf-plugin",
    "@lintpdf/stripe",
    "@lintpdf/viewer-shared",
  ],
  serverExternalPackages: [
    "@prisma/client",
    "@prisma/adapter-pg",
  ],
  webpack: (config, { isServer, webpack }) => {
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push("crypto");
    }

    // Redirect Prisma ESM runtime (.mjs) to CJS (.js) for non-server
    // compilations (instrumentation, edge) where serverExternalPackages
    // doesn't apply and webpack can't handle raw ESM imports.
    config.resolve.alias = {
      ...config.resolve.alias,
      "@prisma/client/runtime/query_compiler_fast_bg.postgresql.mjs":
        "@prisma/client/runtime/query_compiler_fast_bg.postgresql.js",
      "@prisma/client/runtime/query_compiler_fast_bg.postgresql.wasm-base64.mjs":
        "@prisma/client/runtime/query_compiler_fast_bg.postgresql.wasm-base64.js",
    };

    config.resolve.fallback = {
      ...config.resolve.fallback,
      crypto: false,
      fs: false,
      module: false,
      os: false,
      path: false,
      stream: false,
      net: false,
      tls: false,
      dns: false,
      "pg-native": false,
    };
    // Handle node: protocol URIs used by @prisma/client@7.x ESM runtime.
    config.plugins.push(
      new webpack.NormalModuleReplacementPlugin(/^node:/, (resource) => {
        resource.request = resource.request.replace(/^node:/, "");
      }),
    );
    return config;
  },
};

export default config;
