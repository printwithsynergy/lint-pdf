import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { BetaProvider } from "@/components/BetaContext";

export const metadata: Metadata = {
  title: "LintPDF — PDF Preflight API | Every check. Every page. Every time.",
  description:
    "Detection-only PDF preflight engine. API-first. 250+ checks for fonts, color, images, transparency, PDF/X-4, and PDF/A compliance. White-labeled reports. Self-service pricing.",
  keywords: "PDF preflight API, PDF/X-4 validation, print-ready PDF check, prepress quality control, PDF preflight SaaS, preflight-as-a-service, web-to-print preflight, PDF linter",
  openGraph: {
    title: "LintPDF — PDF Preflight API | Every check. Every page. Every time.",
    description: "Detection-only PDF preflight engine. 250+ checks. PDF/X-4, PDF/A, GWG 2022 compliance. White-labeled reports. Zero file modifications.",
    type: "website",
    url: "https://lintpdf.com",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white text-slate-900 antialiased">
        <BetaProvider>
          <Header />
          <div className="pt-16">{children}</div>
          <Footer />
        </BetaProvider>
      </body>
    </html>
  );
}
