import type { Metadata } from "next";
import { hiddenInOssMetadata } from "@/lib/site-mode";

// Layout exists primarily to attach mode-aware noindex metadata to every
// blog page (index + every individual post). In OSS mode the blog is
// hidden from search engines via robots.ts + noindex meta. The full
// HTML still renders so direct links from the SaaS-mode build don't 404.
export const metadata: Metadata = {
  ...hiddenInOssMetadata,
};

export default function BlogLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
