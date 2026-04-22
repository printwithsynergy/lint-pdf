import { getBranding } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import type { Metadata } from "next";

import { getHostBranding } from "@/lib/host-branding";

import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const { fallbackName, isPrimary } = await getHostBranding();
  // Prefer tenant-set AppSettings values (title + custom favicon) and
  // only fall back to the baked-in LintPDF assets on the primary host.
  // The branding query is already cached by getBranding(), so this does
  // not add a round-trip on every request.
  const branding = await getBranding(prisma).catch(() => null);
  const title = branding?.brandName ?? fallbackName;
  const icons = branding?.faviconUrl
    ? { icon: [{ url: branding.faviconUrl }] }
    : isPrimary
      ? {
          icon: [
            { url: "/favicon.svg", type: "image/svg+xml" },
            { url: "/favicon.png", type: "image/png" },
          ],
        }
      : undefined;
  return {
    title,
    description: isPrimary
      ? "PDF preflight SaaS — inspect, report, never modify."
      : undefined,
    icons,
  };
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
