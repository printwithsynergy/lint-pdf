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
    "prisma",
    "@prisma/adapter-pg",
    "@thinkneverland/pixie-dust-database",
    "pg",
    "pg-connection-string",
    "pgpass",
  ],
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push(
        "crypto",
        { "@thinkneverland/pixie-dust-database": "commonjs @thinkneverland/pixie-dust-database" },
        { "@prisma/adapter-pg": "commonjs @prisma/adapter-pg" },
        { "pg": "commonjs pg" },
        { "pg-connection-string": "commonjs pg-connection-string" },
        { "pgpass": "commonjs pgpass" },
      );
    }
    return config;
  },
};

export default config;
