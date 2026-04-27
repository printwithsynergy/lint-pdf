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

// ── v2 playbook contract surface ─────────────────────────────────────
//
// Token-only mobile flows (share-link approve, viewer) can't hit the
// tenant-scoped explain / epm / decisions endpoints — those require a
// Bearer API key. These wrappers exist so authenticated mobile flows
// (when we add operator login) can hit the same engine surface the
// dashboard, desktop, SDK, and plugin consume.

export interface MobileFetchOptions {
  /** Bearer token for tenant-scoped endpoints. */
  apiKey: string;
}

export interface ExplanationResponse {
  finding_id: string;
  text: string;
  model: string | null;
  cached: boolean;
  cost_cents: number | null;
}

async function authFetch(
  path: string,
  apiKey: string,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${apiKey}`);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return apiFetch(path, { ...init, headers });
}

export async function explainFinding(
  jobId: string,
  findingId: string,
  opts: MobileFetchOptions,
): Promise<ExplanationResponse> {
  const resp = await authFetch(
    `/api/v1/jobs/${jobId}/findings/${findingId}/explain`,
    opts.apiKey,
    { method: "POST", body: "{}" },
  );
  if (resp.status === 402) throw new Error("Cost cap exceeded");
  if (!resp.ok) throw new Error(await resp.text());
  const data = await resp.json();
  return {
    finding_id: data.finding_id ?? findingId,
    text: data.explanation ?? data.text ?? "",
    model: data.model ?? null,
    cached: Boolean(data.cached ?? false),
    cost_cents: data.cost_cents ?? null,
  };
}

export interface EpmVerdictResponse {
  job_id: string;
  tier: string;
  rejection_drivers: string[];
  advisories: string[];
  recommends_indichrome: boolean;
  legacy_codes_fired: string[];
  epm_findings_count: number;
}

export async function getEpmVerdict(
  jobId: string,
  opts: MobileFetchOptions,
): Promise<EpmVerdictResponse> {
  const resp = await authFetch(`/api/v1/jobs/${jobId}/epm`, opts.apiKey);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export interface DecisionResponse {
  id: string;
  job_id: string;
  finding_id: string | null;
  decision_type: string;
  decision_value: string | null;
  notes: string | null;
  decided_by_user_id: string;
  decided_at: string | null;
  source: string;
  is_active: boolean;
  revoked_at: string | null;
  revoked_reason: string | null;
}

export async function listDecisions(
  jobId: string,
  opts: MobileFetchOptions,
  query?: { include_revoked?: boolean; limit?: number },
): Promise<DecisionResponse[]> {
  const qs = new URLSearchParams();
  qs.set("include_revoked", String(Boolean(query?.include_revoked)));
  qs.set("limit", String(query?.limit ?? 200));
  const resp = await authFetch(
    `/api/v1/jobs/${jobId}/decisions?${qs.toString()}`,
    opts.apiKey,
  );
  if (!resp.ok) throw new Error(await resp.text());
  const data = await resp.json();
  return data.decisions ?? [];
}

export interface RecordDecisionInput {
  decision_type: string;
  decided_by_user_id: string;
  source?: string;
  finding_id?: string | null;
  notes?: string | null;
}

export async function recordDecision(
  jobId: string,
  input: RecordDecisionInput,
  opts: MobileFetchOptions,
): Promise<DecisionResponse> {
  const path = input.finding_id
    ? `/api/v1/jobs/${jobId}/findings/${input.finding_id}/decisions`
    : `/api/v1/jobs/${jobId}/decisions`;
  const resp = await authFetch(path, opts.apiKey, {
    method: "POST",
    body: JSON.stringify({
      decision_type: input.decision_type,
      decided_by_user_id: input.decided_by_user_id,
      source: input.source ?? "mobile",
      notes: input.notes ?? null,
    }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}
