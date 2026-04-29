import type { Metadata } from "next";
import { hiddenInOssMetadata } from "@/lib/site-mode";

// /try-it is a public-prospect lead-gen surface: in OSS mode the public
// posture has no funnel, so the page is unlinked and noindex'd. Direct
// URL access still renders.
export const metadata: Metadata = {
  ...hiddenInOssMetadata,
};

export default function TryItLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
