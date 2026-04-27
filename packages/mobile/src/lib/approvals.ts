import { apiFetch } from "./api";

export interface ApprovalCompletedStep {
  step_index: number;
  step_name: string;
  approver_email: string;
  decision: string;
  notes: string | null;
  decided_at: string | null;
}

export interface ApprovalHealthSummary {
  total_findings: number;
  error_count: number;
  warning_count: number;
  advisory_count: number;
  passed: boolean;
  page_count: number;
}

export interface ApprovalEpmVerdict {
  tier: string;
  rejection_drivers: string[];
  advisories: string[];
  recommends_indichrome: boolean;
  epm_findings_count: number;
}

export interface ApprovalChainInfo {
  id: string;
  job_id: string;
  status: string;
  current_step: number;
  total_steps: number;
  current_step_name: string | null;
  completed_steps: ApprovalCompletedStep[];
  file_name: string;
  health_summary: ApprovalHealthSummary;
  epm_verdict?: ApprovalEpmVerdict | null;
}

export type ApprovalDecision = "approved" | "rejected";

export class ApprovalError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApprovalError";
  }
}

export async function fetchApprovalInfo(
  token: string,
): Promise<ApprovalChainInfo> {
  const resp = await apiFetch(`/api/lintpdf/approvals/info/${encodeURIComponent(token)}`);
  if (!resp.ok) {
    const data = (await resp.json().catch(() => ({}))) as {
      detail?: string;
      error?: string;
    };
    const fallback =
      resp.status === 404
        ? "This approval link is invalid or has already been used."
        : resp.status === 410
          ? "This approval link has expired."
          : "Unable to load approval details.";
    throw new ApprovalError(data.detail ?? data.error ?? fallback, resp.status);
  }
  return (await resp.json()) as ApprovalChainInfo;
}

export async function submitApprovalDecision(
  token: string,
  decision: ApprovalDecision,
  notes: string | null,
): Promise<unknown> {
  const resp = await apiFetch(
    `/api/lintpdf/approvals/decide/${encodeURIComponent(token)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, notes: notes?.trim() || null }),
    },
  );
  const data = (await resp.json().catch(() => ({}))) as {
    detail?: string;
    error?: string;
  };
  if (!resp.ok) {
    throw new ApprovalError(
      data.detail ?? data.error ?? "Failed to submit decision",
      resp.status,
    );
  }
  return data;
}
