"use client";

/**
 * Structured preflight-profile editor (WS-12).
 *
 * Three tabs that all operate on the same immutable ``profile``
 * value:
 *
 * * **Rules** — catalog-backed grouped list with per-check
 *   severity select + enable toggle, plus per-category bulk
 *   actions (disable all, reset all) and top-level bulk actions
 *   (demote-every-error, reset-everything).
 * * **JSON** — raw JSON view. Valid edits surface in real time
 *   via ``JSON.parse`` + shape validation; invalid payloads
 *   leave the underlying profile untouched and render the
 *   parse error inline. Skipping Monaco keeps the pnpm-lock and
 *   bundle size stable; the validator catches everything a
 *   syntax highlighter would.
 * * **Diff** — every check whose effective state differs from
 *   the baseline profile (i.e. the built-in preset the custom
 *   was cloned from). Makes it trivial to review what a
 *   customer actually changed before saving.
 */

import { useMemo, useState } from "react";
import { ThresholdsPanel } from "./ThresholdsPanel";
import {
  catalog,
  cloneProfile,
  demoteAllErrors,
  diffProfiles,
  disableCategory,
  resetAll,
  resetCategory,
  resetCheck,
  resolveCheckState,
  setCheckEnabled,
  setCheckSeverity,
  validateProfileJson,
  type CheckCategory,
  type Profile,
  type Severity,
} from "@/lib/rules/profile-utils";

type Tab = "rules" | "json" | "diff";

const SEVERITY_OPTIONS: Severity[] = ["error", "warning", "advisory", "off"];

const SEVERITY_COLORS: Record<Severity, string> = {
  error: "text-red-700 bg-red-50 border-red-200",
  warning: "text-amber-700 bg-amber-50 border-amber-200",
  advisory: "text-blue-700 bg-blue-50 border-blue-200",
  off: "text-slate-500 bg-slate-100 border-slate-200",
};

export interface RulesEditorProps {
  profile: Profile;
  baseline?: Profile;
  onChange: (next: Profile) => void;
  readOnly?: boolean;
}

export function RulesEditor({
  profile,
  baseline,
  onChange,
  readOnly = false,
}: RulesEditorProps) {
  const [tab, setTab] = useState<Tab>("rules");
  const [searchQuery, setSearchQuery] = useState("");
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(
    new Set(),
  );

  const effectiveBaseline = baseline ?? DEFAULT_BASELINE;

  const diffRows = useMemo(
    () => diffProfiles(effectiveBaseline, profile),
    [effectiveBaseline, profile],
  );
  const diffByCheckId = useMemo(() => {
    const set = new Set<string>();
    for (const row of diffRows) set.add(row.checkId);
    return set;
  }, [diffRows]);

  function toggleCategory(id: string) {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="mt-4 rounded-lg border">
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2">
        <div className="flex gap-1">
          {(["rules", "json", "diff"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded px-3 py-1 text-sm ${
                tab === t ? "bg-background font-semibold shadow-sm" : "text-muted-foreground hover:bg-background/50"
              }`}
            >
              {t === "rules" && "Rules"}
              {t === "json" && "JSON"}
              {t === "diff" && (
                <span>
                  Diff
                  {diffRows.length > 0 && (
                    <span className="ml-1.5 rounded-full bg-primary/15 px-1.5 py-0.5 text-xs text-primary">
                      {diffRows.length}
                    </span>
                  )}
                </span>
              )}
            </button>
          ))}
        </div>
        {tab === "rules" && !readOnly && (
          <div className="flex gap-2">
            <button
              onClick={() => onChange(demoteAllErrors(profile))}
              className="rounded border px-2 py-1 text-xs hover:bg-muted"
              title="Demote every currently-active error override to advisory."
            >
              Demote all errors
            </button>
            <button
              onClick={() => onChange(resetAll(profile))}
              className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
              title="Drop every check override so the profile matches the catalog defaults."
            >
              Reset all
            </button>
          </div>
        )}
      </div>

      {tab === "rules" && (
        <div className="p-4">
          <ThresholdsPanel
            profile={profile}
            onChange={onChange}
            readOnly={readOnly}
          />
          <input
            type="search"
            placeholder="Filter checks by id, name, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="mb-3 w-full rounded-md border px-3 py-1.5 text-sm"
          />
          <div className="space-y-3">
            {catalog.categories.map((cat) => (
              <CategoryBlock
                key={cat.id}
                category={cat}
                profile={profile}
                readOnly={readOnly}
                searchQuery={searchQuery}
                collapsed={collapsedCategories.has(cat.id)}
                changedCheckIds={diffByCheckId}
                onToggleCollapse={() => toggleCategory(cat.id)}
                onCheckSeverity={(checkId, severity) =>
                  onChange(setCheckSeverity(profile, checkId, severity))
                }
                onCheckEnabled={(checkId, enabled) =>
                  onChange(setCheckEnabled(profile, checkId, enabled))
                }
                onCheckReset={(checkId) => onChange(resetCheck(profile, checkId))}
                onDisableCategory={() => onChange(disableCategory(profile, cat.id))}
                onResetCategory={() => onChange(resetCategory(profile, cat.id))}
              />
            ))}
          </div>
        </div>
      )}

      {tab === "json" && (
        <JsonTab profile={profile} onChange={onChange} readOnly={readOnly} />
      )}

      {tab === "diff" && <DiffTab rows={diffRows} />}
    </div>
  );
}

// ── Category block ─────────────────────────────────────────

function CategoryBlock({
  category,
  profile,
  readOnly,
  searchQuery,
  collapsed,
  changedCheckIds,
  onToggleCollapse,
  onCheckSeverity,
  onCheckEnabled,
  onCheckReset,
  onDisableCategory,
  onResetCategory,
}: {
  category: CheckCategory;
  profile: Profile;
  readOnly: boolean;
  searchQuery: string;
  collapsed: boolean;
  changedCheckIds: Set<string>;
  onToggleCollapse: () => void;
  onCheckSeverity: (id: string, severity: Severity) => void;
  onCheckEnabled: (id: string, enabled: boolean) => void;
  onCheckReset: (id: string) => void;
  onDisableCategory: () => void;
  onResetCategory: () => void;
}) {
  const q = searchQuery.trim().toLowerCase();
  const filtered = q
    ? category.checks.filter(
        (c) =>
          c.id.toLowerCase().includes(q) ||
          c.name.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q),
      )
    : category.checks;

  if (filtered.length === 0 && q) {
    return null;
  }

  const changedCount = category.checks.filter((c) =>
    changedCheckIds.has(c.id),
  ).length;

  return (
    <div className="rounded-md border">
      <div className="flex items-center justify-between border-b bg-muted/20 px-3 py-2">
        <button
          onClick={onToggleCollapse}
          className="flex items-center gap-2 text-left"
        >
          <span className="text-xs text-muted-foreground">
            {collapsed ? "▸" : "▾"}
          </span>
          <span className="font-medium">{category.label}</span>
          <span className="text-xs text-muted-foreground">
            {filtered.length} check{filtered.length === 1 ? "" : "s"}
            {changedCount > 0 && ` · ${changedCount} changed`}
          </span>
        </button>
        {!readOnly && (
          <div className="flex gap-1">
            <button
              onClick={onDisableCategory}
              className="rounded border px-2 py-0.5 text-xs hover:bg-muted"
            >
              Disable all
            </button>
            <button
              onClick={onResetCategory}
              className="rounded border px-2 py-0.5 text-xs hover:bg-muted"
            >
              Reset
            </button>
          </div>
        )}
      </div>
      {!collapsed && (
        <div className="divide-y">
          {filtered.map((check) => {
            const state = resolveCheckState(profile, check.id);
            const changed = changedCheckIds.has(check.id);
            return (
              <div
                key={check.id}
                className={`flex items-start gap-3 px-3 py-2 ${changed ? "bg-amber-50/40" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={state.enabled}
                  onChange={(e) => onCheckEnabled(check.id, e.target.checked)}
                  disabled={readOnly}
                  className="mt-1"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-muted-foreground">
                      {check.id}
                    </code>
                    <span className="font-medium text-sm">{check.name}</span>
                    {changed && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">
                        Changed
                      </span>
                    )}
                  </div>
                  {check.description && (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {check.description}
                    </p>
                  )}
                </div>
                <select
                  value={state.enabled ? state.severity : "off"}
                  onChange={(e) =>
                    onCheckSeverity(check.id, e.target.value as Severity)
                  }
                  disabled={readOnly}
                  className={`rounded border px-2 py-1 text-xs ${SEVERITY_COLORS[state.enabled ? state.severity : "off"]}`}
                >
                  {SEVERITY_OPTIONS.map((sev) => (
                    <option key={sev} value={sev}>
                      {sev}
                    </option>
                  ))}
                </select>
                {changed && !readOnly && (
                  <button
                    onClick={() => onCheckReset(check.id)}
                    className="rounded border px-2 py-1 text-xs hover:bg-muted"
                    title="Reset this check to its catalog default."
                  >
                    Reset
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── JSON tab ───────────────────────────────────────────────

function JsonTab({
  profile,
  onChange,
  readOnly,
}: {
  profile: Profile;
  onChange: (next: Profile) => void;
  readOnly: boolean;
}) {
  const [draft, setDraft] = useState(() => JSON.stringify(profile, null, 2));
  const [lastProfile, setLastProfile] = useState(profile);

  // Keep the draft in sync when the parent profile changes (e.g.
  // the user edited something in the Rules tab and switched back
  // to the JSON view).
  if (profile !== lastProfile) {
    setLastProfile(profile);
    setDraft(JSON.stringify(profile, null, 2));
  }

  const validation = useMemo(() => validateProfileJson(draft), [draft]);

  function handleApply() {
    if (validation.valid && validation.parsed) {
      onChange(cloneProfile(validation.parsed));
    }
  }

  return (
    <div className="p-4">
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">
          Edit the raw PreflightProfile JSON. Invalid JSON stays local until you
          fix it.
        </span>
        {!readOnly && (
          <button
            onClick={handleApply}
            disabled={!validation.valid}
            className="rounded border px-2 py-1 text-xs disabled:opacity-40"
          >
            Apply JSON
          </button>
        )}
      </div>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        readOnly={readOnly}
        spellCheck={false}
        rows={24}
        className={`w-full rounded-md border p-3 font-mono text-xs ${
          validation.valid ? "" : "border-destructive"
        }`}
      />
      {!validation.valid && (
        <p className="mt-2 text-xs text-destructive">{validation.error}</p>
      )}
    </div>
  );
}

// ── Diff tab ───────────────────────────────────────────────

function DiffTab({ rows }: { rows: ReturnType<typeof diffProfiles> }) {
  if (rows.length === 0) {
    return (
      <div className="p-6 text-center text-sm text-muted-foreground">
        No changes vs. the baseline profile.
      </div>
    );
  }
  return (
    <div className="divide-y">
      {rows.map((row) => (
        <div key={row.checkId} className="flex items-center gap-3 px-4 py-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <code className="text-xs text-muted-foreground">
                {row.checkId}
              </code>
              <span className="text-sm font-medium">{row.name}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Category: {row.categoryId}
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <DiffChip label="was" state={row.from} />
            <span>→</span>
            <DiffChip label="now" state={row.to} />
          </div>
        </div>
      ))}
    </div>
  );
}

function DiffChip({
  label,
  state,
}: {
  label: string;
  state: { enabled: boolean; severity: Severity };
}) {
  const sev: Severity = state.enabled ? state.severity : "off";
  return (
    <span
      className={`rounded border px-2 py-0.5 ${SEVERITY_COLORS[sev]}`}
      title={label}
    >
      {sev}
    </span>
  );
}

// The "baseline" is whatever profile the user started from; when
// the caller doesn't pass one we fall back to an empty profile so
// diffs render the full set of explicit overrides rather than
// nothing.
const DEFAULT_BASELINE: Profile = {
  checks: { enabled: [], disabled: [], severity_overrides: {} },
};
