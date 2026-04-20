import { headers } from "next/headers";

const DEFAULT_PRIMARY_HOSTS = [
  "lintpdf.com",
  "localhost",
  "127.0.0.1",
  "0.0.0.0",
];

function parsePrimaryHosts(raw: string | undefined): string[] {
  if (!raw) return DEFAULT_PRIMARY_HOSTS;
  const parts = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return parts.length > 0 ? parts : DEFAULT_PRIMARY_HOSTS;
}

function normalize(host: string | null | undefined): string | null {
  if (!host) return null;
  return host.toLowerCase().split(":")[0] ?? null;
}

export function isPrimaryHost(host: string | null | undefined): boolean {
  const h = normalize(host);
  if (!h) return true;
  const primaries = parsePrimaryHosts(process.env.LINTPDF_PRIMARY_HOSTS);
  return primaries.some((p) => h === p || h.endsWith(`.${p}`));
}

export interface HostBranding {
  host: string | null;
  isPrimary: boolean;
  /** Name to use when a tenant hasn't set an explicit brand name.
   * On primary LintPDF hosts: "LintPDF".
   * On custom domains: the hostname itself (e.g. "files.acme.com"). */
  fallbackName: string;
}

export async function getHostBranding(): Promise<HostBranding> {
  const hdrs = await headers();
  // On custom domains, requests hit edge-caddy first, which rewrites Host
  // to app.lintpdf.com for Railway's SNI. Railway's own proxy further
  // rewrites X-Forwarded-Host to the Railway hostname it answered on.
  //   edge-caddy/Caddyfile sets a custom X-LintPDF-Public-Host that
  // Railway passes through untouched — that's the only reliable place to
  // read the actual public hostname the viewer typed.
  const raw =
    hdrs.get("x-lintpdf-public-host") ??
    hdrs.get("x-forwarded-host") ??
    hdrs.get("x-original-host") ??
    hdrs.get("host");
  const h = normalize(raw);
  const primary = isPrimaryHost(h);
  return {
    host: h,
    isPrimary: primary,
    fallbackName: primary ? "LintPDF" : (h ?? "Viewer"),
  };
}
