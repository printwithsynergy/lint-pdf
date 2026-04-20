import type { Metadata } from "next";

import { getHostBranding } from "@/lib/host-branding";

import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const { fallbackName, isPrimary } = await getHostBranding();
  return {
    title: fallbackName,
    description: isPrimary
      ? "PDF preflight SaaS — inspect, report, never modify."
      : undefined,
    icons: isPrimary
      ? {
          icon: [
            { url: "/favicon.svg", type: "image/svg+xml" },
            { url: "/favicon.png", type: "image/png" },
          ],
        }
      : undefined,
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
