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
