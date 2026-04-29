import type { Metadata } from "next";
import { hiddenInOssMetadata } from "@/lib/site-mode";

// /beta and /beta/join are launch-flavored lead-gen surfaces; hidden in
// OSS mode (unlinked + noindex). The layout covers every nested /beta/*
// route in one place.
export const metadata: Metadata = {
  ...hiddenInOssMetadata,
};

export default function BetaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
