import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Email Signature — LintPDF",
  description:
    "LintPDF staff email signature with one-click copy for Mac Mail, Outlook, and Gmail.",
  // Internal staff tool — don't surface in search results.
  robots: { index: false, follow: false },
};

export default function EmailSignatureLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
