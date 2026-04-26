/**
 * Resolves the LintPDF Next.js base URL for fetch calls. Uses the
 * `VITE_LINTPDF_API_BASE_URL` env var when present (for staging /
 * preview builds), otherwise defaults to production.
 *
 * Tauri WebViews load the bundle from a `tauri://` or
 * `https://tauri.localhost/` origin, so all API calls are
 * cross-origin — the public endpoints we hit (`/api/public/*`,
 * `/api/lintpdf/viewer/public/*`, `/api/lintpdf/approvals/*`) all
 * set permissive CORS headers, so this works without proxy config.
 */
export function getApiBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_LINTPDF_API_BASE_URL;
  if (typeof fromEnv === "string" && fromEnv.length > 0) {
    return fromEnv;
  }
  return "https://app.lintpdf.com";
}

/**
 * Thin fetch wrapper that scopes every request to the configured
 * base URL. Future iterations will attach `X-Tenant-Id` and
 * `Authorization` headers from the captured tenant + API key.
 */
export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const url = path.startsWith("http")
    ? path
    : new URL(path, getApiBaseUrl()).toString();
  return fetch(url, init);
}
