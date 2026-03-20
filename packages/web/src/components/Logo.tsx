/**
 * LintPDF logo — uses the compact SVG logo file.
 * For hero/marketing contexts, use the marketing logo via <img>.
 *
 * Plain <img> tags are used instead of next/image to avoid
 * wrapper-element rendering artifacts with SVGs on mobile.
 */

/* eslint-disable @next/next/no-img-element */

export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  return <img src="/logo.svg" alt="LintPDF" className={className} />;
}

export function MarketingLogo({
  className = "h-40 w-auto",
}: {
  className?: string;
}) {
  return <img src="/logo-marketing.svg" alt="LintPDF" className={className} />;
}
