import type { MetadataRoute } from "next";
import { isOssMode } from "@/lib/site-mode";

// Routes that build but are explicitly hidden from indexers in OSS mode.
// Three-layer defense: nav links suppressed (Header/Footer), page-level
// metadata.robots set to noindex, sitemap-excluded, robots.txt-disallowed.
const OSS_DISALLOW = [
  "/pricing",
  "/try-it",
  "/blog",
  "/changelog",
  "/integrations",
  "/swagger",
  "/ai",
  "/email-signature",
  "/beta",
  "/docs",
];

export default function robots(): MetadataRoute.Robots {
  if (isOssMode()) {
    return {
      rules: {
        userAgent: "*",
        allow: "/",
        disallow: OSS_DISALLOW,
      },
      sitemap: "https://lintpdf.com/sitemap.xml",
    };
  }

  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: "https://lintpdf.com/sitemap.xml",
  };
}
