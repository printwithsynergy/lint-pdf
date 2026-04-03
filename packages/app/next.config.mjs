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
    "@prisma/client/runtime",
    "@prisma/client/runtime/library",
    "@prisma/client/runtime/query_compiler_fast_bg.postgresql.mjs",
    "@prisma/client/runtime/query_compiler_fast_bg.postgresql.wasm-base64.mjs",
  ],
  webpack: (config, { isServer, webpack }) => {
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push(
        "crypto",
        "@prisma/client/runtime",
        "@prisma/client/runtime/query_compiler_fast_bg.postgresql.mjs",
        "@prisma/client/runtime/query_compiler_fast_bg.postgresql.wasm-base64.mjs"
      );
    }
    // Provide empty fallbacks for Node.js built-ins encountered during
    // edge/instrumentation compilation (pixie-dust-database → pg chain).
    // serverExternalPackages only applies to the Node.js server bundle;
    // the instrumentation bundle uses the edge webpack config where the
    // package is still traversed statically.
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
    };
    // Handle node: protocol URIs used by @prisma/client@7.x ESM runtime.
    // resolve.alias/fallback cannot intercept scheme-based URIs (node:*).
    // NormalModuleReplacementPlugin strips the node: prefix so that the
    // bare module name hits resolve.fallback above (client/edge) or
    // resolves to the real built-in (server).
    config.plugins.push(
      new webpack.NormalModuleReplacementPlugin(/^node:/, (resource) => {
        resource.request = resource.request.replace(/^node:/, "");
      }),
    );
    return config;
  },
};

export default config;
