"use client";

/**
 * UpgradePrompt — inline card shown when a tenant tries to use a feature
 * their plan doesn't include. Matches the ``plan_upgrade_required`` 403
 * envelope from the engine (see ``packages/engine/src/lintpdf/api/gates.py``).
 *
 * Single reusable surface for all four tier gates (preflight_source,
 * capability_fillin, annotations, report_format). The CTA links to
 * ``/pricing`` and deep-links to the relevant tier when possible.
 */

export type UpgradePromptGate =
  | "preflight_source"
  | "capability_fillin"
  | "annotations"
  | "report_format";

export interface UpgradePromptProps {
  gate: UpgradePromptGate;
  currentPlan?: string;
  requiredPlan?: string;
  className?: string;
}

const GATE_COPY: Record<
  UpgradePromptGate,
  { title: string; body: string }
> = {
  preflight_source: {
    title: "Engine preflight not included on your plan",
    body: "The Viewer tier uses your imported preflight data — it doesn't run our engine. Upgrade to Starter to submit files for the full 500+ check pipeline.",
  },
  capability_fillin: {
    title: "On-demand analysis requires Starter",
    body: "Findings, separations, TAC, fonts, and images are on-demand fills on Starter and above. Your Viewer-tier plan shows what's in the PDF + your imported report — nothing more.",
  },
  annotations: {
    title: "Viewer annotations require Starter",
    body: "Drawing, highlighting, and comment threads are available on Starter and above. The Viewer tier ships a read-only viewer — bring your own annotation tool, or upgrade.",
  },
  report_format: {
    title: "Report downloads require Starter",
    body: "Viewer-tier output is the interactive share link only. Upgrade to Starter to download PDF, JSON, and XML reports.",
  },
};

export function UpgradePrompt({
  gate,
  currentPlan,
  requiredPlan,
  className,
}: UpgradePromptProps) {
  const copy = GATE_COPY[gate];
  const targetPlan = requiredPlan || "starter";

  return (
    <div
      role="alert"
      className={
        "rounded-2xl border border-brand-200 bg-brand-50/70 p-5 " +
        (className ?? "")
      }
    >
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M5 10l7-7 7 7M5 20h14"
            />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">
            {copy.title}
          </h3>
          <p className="text-sm text-slate-600 leading-relaxed mb-3">
            {copy.body}
          </p>
          {currentPlan && (
            <p className="text-xs text-slate-400 mb-3">
              Current plan:{" "}
              <span className="font-medium capitalize">{currentPlan}</span>
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <a
              href={`/dashboard/billing?suggest=${targetPlan}`}
              className="rounded-lg bg-brand-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-800"
            >
              Upgrade to {targetPlan.charAt(0).toUpperCase() + targetPlan.slice(1)}
            </a>
            <a
              href="/pricing"
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-200"
            >
              Compare plans
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Narrow the engine's 403 body to ``plan_upgrade_required`` so viewer code
 * can short-circuit to an ``UpgradePrompt`` without leaking raw 403s.
 */
export interface PlanUpgradeRequiredDetail {
  error: "plan_upgrade_required";
  message: string;
  gate: UpgradePromptGate;
  current_plan: string;
  required_plan: string;
  upgrade_url: string;
}

export function isPlanUpgradeRequired(
  detail: unknown,
): detail is PlanUpgradeRequiredDetail {
  return (
    typeof detail === "object" &&
    detail !== null &&
    (detail as { error?: unknown }).error === "plan_upgrade_required"
  );
}
