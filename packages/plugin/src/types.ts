/**
 * TypeScript types matching the LintPDF API schemas.
 *
 * These mirror the Python Pydantic models in:
 * packages/engine/src/grounded/api/schemas.py
 */

export type Severity = "error" | "warning" | "advisory";
export type JobStatus = "pending" | "processing" | "complete" | "failed";

export interface PreflightFinding {
  inspection_id: string;
  severity: Severity;
  message: string;
  page_num: number | null;
  details: Record<string, unknown>;
}

export interface PreflightSummary {
  total_findings: number;
  error_count: number;
  warning_count: number;
  advisory_count: number;
  passed: boolean;
  page_count: number;
  file_size_bytes: number;
}

export interface PreflightJob {
  job_id: string;
  status: JobStatus;
  profile_id: string;
  file_name: string;
  file_size: number;
  page_count: number | null;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  summary: PreflightSummary | null;
  findings: PreflightFinding[];
  error_message: string | null;
}

export interface PreflightProfile {
  profile_id: string;
  name: string;
  description: string;
  conformance: string | null;
  workflow: string;
  is_builtin: boolean;
}

/** Pixie Dust webhook payload from LintPDF */
export interface PixieDustPayload {
  event: "preflight.complete" | "preflight.failed";
  job_id: string;
  profile_id?: string;
  passed: boolean;
  badge: "pass" | "fail" | "error";
  summary?: {
    total: number;
    error_count: number;
    warning_count: number;
    advisory: number;
    pages: number;
    file_size_bytes: number;
  };
  document?: {
    pdf_version: string;
    encrypted: boolean;
    conformance: string | null;
  };
  findings?: {
    error: PixieDustFinding[];
    warning: PixieDustFinding[];
    advisory: PixieDustFinding[];
  };
  duration_ms?: number;
  error?: string;
  usage?: PixieDustUsage;
  report?: ReportUrls;
}

export interface ReportUrls {
  html_url: string | null;
  pdf_url: string | null;
  expires_at: string | null;
}

export interface ReportConfig {
  default_expiry_days: number;
  default_formats: string[];
  email_enabled: boolean;
  storage_used_bytes: number;
  storage_limit_bytes: number;
}

export interface PixieDustFinding {
  check_id: string;
  message: string;
  page: number | null;
  object: string;
}

export interface PreflightJobList {
  jobs: PreflightJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface PreflightProfileList {
  profiles: PreflightProfile[];
}

export interface UsageInfo {
  plan: string;
  used: number;
  limit: number;
  remaining_included: number;
  percentage: number;
  in_overage: boolean;
  overage_count: number;
  overage_rate_cents: number;
  overage_cost_cents: number;
  overage_enabled: boolean;
  overage_cap_cents: number | null;
  cap_remaining_cents: number | null;
  blocked: boolean;
  warning: boolean;
}

export interface PixieDustUsage {
  used: number;
  limit: number;
  remaining_included: number;
  percentage: number;
  in_overage: boolean;
  overage_count: number;
  overage_rate_cents: number;
  overage_cost_cents: number;
  overage_enabled: boolean;
  overage_cap_cents: number | null;
  cap_remaining_cents: number | null;
  blocked: boolean;
  warning: boolean;
}

export interface PluginConfig {
  apiUrl: string;
  webhookSecret: string;
  apiKey?: string;
}
