"use client";

const DEFAULT_PRIMARY_HOSTS = [
  "lintpdf.com",
  "localhost",
  "127.0.0.1",
  "0.0.0.0",
];

function readPrimaryHostsEnv(): string {
  const proc = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process;
  return proc?.env?.NEXT_PUBLIC_LINTPDF_PRIMARY_HOSTS ?? "";
}

function getPrimaryHosts(): string[] {
  const parts = readPrimaryHostsEnv()
    .split(",")
    .map((s: string) => s.trim().toLowerCase())
    .filter(Boolean);
  return parts.length > 0 ? parts : DEFAULT_PRIMARY_HOSTS;
}

export function hostFallbackClient(): string {
  if (typeof window === "undefined") return "LintPDF";
  const h = window.location.hostname.toLowerCase();
  const primaries = getPrimaryHosts();
  const isPrimary = primaries.some((p) => h === p || h.endsWith(`.${p}`));
  return isPrimary ? "LintPDF" : h;
}
