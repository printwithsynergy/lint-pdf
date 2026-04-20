"use client";

const DEFAULT_PRIMARY_HOSTS = [
  "lintpdf.com",
  "localhost",
  "127.0.0.1",
  "0.0.0.0",
];

function getPrimaryHosts(): string[] {
  const env =
    (typeof process !== "undefined" &&
      process.env?.NEXT_PUBLIC_LINTPDF_PRIMARY_HOSTS) ||
    "";
  const parts = env
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return parts.length > 0 ? parts : DEFAULT_PRIMARY_HOSTS;
}

/** Hostname-based brand fallback for client components. Returns "LintPDF"
 * on primary LintPDF hosts (and during SSR), and the current hostname on
 * custom domains so the UI never leaks "LintPDF" to tenant visitors. */
export function hostFallbackClient(): string {
  if (typeof window === "undefined") return "LintPDF";
  const h = window.location.hostname.toLowerCase();
  const primaries = getPrimaryHosts();
  const isPrimary = primaries.some((p) => h === p || h.endsWith(`.${p}`));
  return isPrimary ? "LintPDF" : h;
}
