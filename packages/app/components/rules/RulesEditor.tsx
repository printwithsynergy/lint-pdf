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

import { useEffect, useMemo, useState } from "react";
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

// Two-level grouping: each entry rolls up several catalog categories
// into a single header strip so the editor opens with ~7 sections
// instead of 47. AI checks are computed at render time so any new
// "ai:*" catalog category lands in the AI bucket automatically.
interface SuperGroupDef {
  id: string;
  label: string;
  categoryIds: readonly string[];
}

const SUPER_GROUPS: readonly SuperGroupDef[] = [
  {
    id: "color",
    label: "Colour & inks",
    categoryIds: [
      "color",
      "color_management",
      "ink_coverage",
      "spot_colors",
      "overprint",
      "transparency",
    ],
  },
  { id: "fonts", label: "Fonts & text", categoryIds: ["fonts", "text"] },
  {
    id: "imagery",
    label: "Imagery & vectors",
    categoryIds: ["image", "hairlines", "strokes", "paths"],
  },
  {
    id: "layout",
    label: "Layout & structure",
    categoryIds: [
      "page_geometry",
      "document",
      "structure",
      "metadata",
      "annotations",
      "accessibility",
    ],
  },
  {
    id: "print",
    label: "Print production",
    categoryIds: ["barcodes", "packaging", "advanced", "standards"],
  },
  { id: "ai", label: "AI checks", categoryIds: [] },
  { id: "other", label: "Other", categoryIds: ["other"] },
];

const STORAGE_KEY_SUPER = "lintpdf.rulesEditor.collapsedSuperGroups";
const STORAGE_KEY_CATEGORY = "lintpdf.rulesEditor.collapsedCategories";

function loadStoredSet(key: string): Set<string> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    return new Set(parsed.filter((v): v is string => typeof v === "string"));
  } catch {
    return null;
  }
}

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
    () => loadStoredSet(STORAGE_KEY_CATEGORY) ?? new Set(),
  );
  // Resolved super-group list with the AI bucket populated from the
  // catalog. Memoised so the same Set is reused across renders.
  const superGroups = useMemo(() => {
    const knownIds = new Set<string>();
    const groups: Array<{ id: string; label: string; categories: CheckCategory[] }> = [];
    const catById = new Map(catalog.categories.map((c) => [c.id, c]));
    for (const def of SUPER_GROUPS) {
      const ids =
        def.id === "ai"
          ? catalog.categories.filter((c) => c.id.startsWith("ai:")).map((c) => c.id)
          : def.categoryIds;
      const categories: CheckCategory[] = [];
      for (const id of ids) {
        const cat = catById.get(id);
        if (cat) {
          categories.push(cat);
          knownIds.add(id);
        }
      }
      groups.push({ id: def.id, label: def.label, categories });
    }
    // Anything not assigned by SUPER_GROUPS lands in "Other" so a new
    // catalog category added upstream still shows up in the editor.
    const other = groups.find((g) => g.id === "other");
    if (other) {
      for (const cat of catalog.categories) {
        if (!knownIds.has(cat.id) && !other.categories.find((c) => c.id === cat.id)) {
          other.categories.push(cat);
        }
      }
    }
    return groups;
  }, []);
  const [collapsedSuperGroups, setCollapsedSuperGroups] = useState<Set<string>>(
    () => {
      const stored = loadStoredSet(STORAGE_KEY_SUPER);
      if (stored) return stored;
      // First-ever load: collapse every super-group except the first
      // so the editor opens compact instead of as a 421-row wall.
      const initial = new Set<string>();
      SUPER_GROUPS.slice(1).forEach((g) => initial.add(g.id));
      return initial;
    },
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        STORAGE_KEY_CATEGORY,
        JSON.stringify(Array.from(collapsedCategories)),
      );
    } catch {
      // localStorage unavailable (private mode quota etc.) — ignore.
    }
  }, [collapsedCategories]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        STORAGE_KEY_SUPER,
        JSON.stringify(Array.from(collapsedSuperGroups)),
      );
    } catch {
      // ignore
    }
  }, [collapsedSuperGroups]);

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

  function toggleSuperGroup(id: string) {
    setCollapsedSuperGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function expandAll() {
    setCollapsedSuperGroups(new Set());
    setCollapsedCategories(new Set());
  }

  function collapseAll() {
    setCollapsedSuperGroups(new Set(superGroups.map((g) => g.id)));
  }

  const searchActive = searchQuery.trim().length > 0;

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
        {tab === "rules" && (
          <div className="flex gap-2">
            <button
              onClick={expandAll}
              className="rounded border px-2 py-1 text-xs hover:bg-muted"
              title="Open every super-group and category."
            >
              Expand all
            </button>
            <button
              onClick={collapseAll}
              className="rounded border px-2 py-1 text-xs hover:bg-muted"
              title="Collapse every super-group."
            >
              Collapse all
            </button>
            {!readOnly && (
              <>
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
              </>
            )}
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
            {superGroups.map((group) => {
              if (group.categories.length === 0) return null;
              if (searchActive) {
                const q = searchQuery.trim().toLowerCase();
                const anyMatch = group.categories.some((c) =>
                  c.checks.some(
                    (ck) =>
                      ck.id.toLowerCase().includes(q) ||
                      ck.name.toLowerCase().includes(q) ||
                      ck.description.toLowerCase().includes(q),
                  ),
                );
                if (!anyMatch) return null;
              }
              const collapsed =
                !searchActive && collapsedSuperGroups.has(group.id);
              const totalChecks = group.categories.reduce(
                (n, c) => n + c.checks.length,
                0,
              );
              const changedCount = group.categories.reduce(
                (n, c) =>
                  n + c.checks.filter((ck) => diffByCheckId.has(ck.id)).length,
                0,
              );
              return (
                <SuperGroupBlock
                  key={group.id}
                  label={group.label}
                  collapsed={collapsed}
                  totalChecks={totalChecks}
                  changedCount={changedCount}
                  onToggleCollapse={() => toggleSuperGroup(group.id)}
                >
                  {group.categories.map((cat) => (
                    <CategoryBlock
                      key={cat.id}
                      category={cat}
                      profile={profile}
                      readOnly={readOnly}
                      searchQuery={searchQuery}
                      collapsed={
                        !searchActive && collapsedCategories.has(cat.id)
                      }
                      changedCheckIds={diffByCheckId}
                      onToggleCollapse={() => toggleCategory(cat.id)}
                      onCheckSeverity={(checkId, severity) =>
                        onChange(setCheckSeverity(profile, checkId, severity))
                      }
                      onCheckEnabled={(checkId, enabled) =>
                        onChange(setCheckEnabled(profile, checkId, enabled))
                      }
                      onCheckReset={(checkId) =>
                        onChange(resetCheck(profile, checkId))
                      }
                      onDisableCategory={() =>
                        onChange(disableCategory(profile, cat.id))
                      }
                      onResetCategory={() =>
                        onChange(resetCategory(profile, cat.id))
                      }
                    />
                  ))}
                </SuperGroupBlock>
              );
            })}
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

// ── Super-group block ──────────────────────────────────────

function SuperGroupBlock({
  label,
  collapsed,
  totalChecks,
  changedCount,
  onToggleCollapse,
  children,
}: {
  label: string;
  collapsed: boolean;
  totalChecks: number;
  changedCount: number;
  onToggleCollapse: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-slate-300 bg-slate-50/40">
      <button
        onClick={onToggleCollapse}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-slate-100"
      >
        <span className="text-xs text-muted-foreground">
          {collapsed ? "▸" : "▾"}
        </span>
        <span className="text-sm font-semibold uppercase tracking-wide text-slate-700">
          {label}
        </span>
        <span className="text-xs text-muted-foreground">
          {totalChecks} check{totalChecks === 1 ? "" : "s"}
          {changedCount > 0 && ` · ${changedCount} changed`}
        </span>
      </button>
      {!collapsed && <div className="space-y-3 border-t bg-background p-3">{children}</div>}
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
