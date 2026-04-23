/**
 * Pure helpers for the Rules editor (WS-12).
 *
 * The editor operates on a mutable clone of the PreflightProfile
 * JSON and applies structured edits via these helpers so the
 * same logic runs whether the user is clicking a toggle or
 * triggering a bulk action. Keeping the functions pure (no state,
 * no I/O) means the structured editor and the JSON tab can pipe
 * through the same code paths — the JSON tab just validates +
 * hands the parsed object straight into the diff engine.
 */

import catalogData from "./check-catalog.json";

export type Severity = "error" | "warning" | "advisory" | "off";

export interface CheckCatalogEntry {
  id: string;
  name: string;
  description: string;
  default_severity: Severity;
}

export interface CheckCategory {
  id: string;
  label: string;
  checks: CheckCatalogEntry[];
}

export interface CheckCatalog {
  version: number;
  generated_by: string;
  total_checks: number;
  categories: CheckCategory[];
}

export const catalog = catalogData as CheckCatalog;

// Lookup helpers keyed by check id. Built once at module load so
// the editor doesn't re-scan the catalog on every row render.
const catalogByCheckId: Record<string, CheckCatalogEntry> = {};
const categoryByCheckId: Record<string, string> = {};
for (const cat of catalog.categories) {
  for (const check of cat.checks) {
    catalogByCheckId[check.id] = check;
    categoryByCheckId[check.id] = cat.id;
  }
}

export function getCheckInfo(id: string): CheckCatalogEntry | null {
  return catalogByCheckId[id] ?? null;
}

export function getCategoryOf(id: string): string | null {
  return categoryByCheckId[id] ?? null;
}

// ── Profile shape ─────────────────────────────────────────────

export interface ProfileChecks {
  enabled?: string[];
  disabled?: string[];
  severity_overrides?: Record<string, Severity>;
}

export interface Profile {
  name?: string;
  description?: string;
  version?: string;
  conformance?: string | null;
  workflow?: string;
  checks?: ProfileChecks;
  thresholds?: Record<string, unknown>;
  [k: string]: unknown;
}

// ── Severity + enable/disable computation ────────────────────

/**
 * Work out the effective severity + enabled status for a check
 * given the profile's ``checks`` block. Mirrors the engine-side
 * resolution order:
 *
 * 1. If the check is on ``checks.disabled`` → off.
 * 2. Otherwise if ``severity_overrides[id]`` is set → that value
 *    (``off`` disables the check; error/warning/advisory pin it).
 * 3. Otherwise inherit the catalog's ``default_severity``.
 *
 * Wildcard entries on ``enabled`` / ``disabled`` (e.g. ``LPDF_*``)
 * are respected by splitting them into prefix matchers.
 */
export function resolveCheckState(
  profile: Profile,
  checkId: string,
): { enabled: boolean; severity: Severity } {
  const info = getCheckInfo(checkId);
  const defaultSeverity = info?.default_severity ?? "advisory";
  const checks = profile.checks ?? {};
  const enabledList = checks.enabled ?? [];
  const disabledList = checks.disabled ?? [];
  const overrides = checks.severity_overrides ?? {};

  const matches = (list: string[]): boolean =>
    list.some((pattern) => {
      if (pattern === checkId) return true;
      if (pattern.endsWith("*")) {
        return checkId.startsWith(pattern.slice(0, -1));
      }
      return false;
    });

  if (matches(disabledList)) {
    return { enabled: false, severity: defaultSeverity };
  }
  const override = overrides[checkId];
  if (override === "off") {
    return { enabled: false, severity: defaultSeverity };
  }
  if (override === "error" || override === "warning" || override === "advisory") {
    return { enabled: true, severity: override };
  }
  // ``enabled`` is a positive allowlist — the check is on when it
  // matches a pattern there OR when neither list excludes it.
  const onAllowlist = enabledList.length === 0 || matches(enabledList);
  return {
    enabled: onAllowlist,
    severity: defaultSeverity,
  };
}

// ── Edits ────────────────────────────────────────────────────

export function cloneProfile(profile: Profile): Profile {
  // Structured clone is safe — profile JSON has no functions or
  // Dates. Avoids the ``JSON.parse(JSON.stringify(...))`` round-trip.
  return structuredClone(profile);
}

function ensureChecks(profile: Profile): ProfileChecks {
  if (!profile.checks) profile.checks = {};
  if (!profile.checks.enabled) profile.checks.enabled = [];
  if (!profile.checks.disabled) profile.checks.disabled = [];
  if (!profile.checks.severity_overrides) profile.checks.severity_overrides = {};
  return profile.checks;
}

/** Set a single check's severity. ``off`` disables it. */
export function setCheckSeverity(
  profile: Profile,
  checkId: string,
  severity: Severity,
): Profile {
  const next = cloneProfile(profile);
  const checks = ensureChecks(next);
  const info = getCheckInfo(checkId);
  const defaultSeverity = info?.default_severity ?? "advisory";

  // Always purge any stale explicit enable/disable entries so the
  // editor doesn't leave wildcard residue after a UI toggle.
  checks.disabled = (checks.disabled ?? []).filter((p) => p !== checkId);
  checks.enabled = (checks.enabled ?? []).filter((p) => p !== checkId);

  if (severity === "off") {
    checks.severity_overrides![checkId] = "off";
    return next;
  }
  if (severity === defaultSeverity) {
    // Round-trip back to the default — drop the override so the
    // JSON stays as close to the baseline profile as possible.
    delete checks.severity_overrides![checkId];
    return next;
  }
  checks.severity_overrides![checkId] = severity;
  return next;
}

/** Toggle a single check on or off. */
export function setCheckEnabled(
  profile: Profile,
  checkId: string,
  enabled: boolean,
): Profile {
  if (enabled) {
    // Re-enabling: drop any "off" override / disabled entry and
    // restore the prior severity (or the default if none).
    const next = cloneProfile(profile);
    const checks = ensureChecks(next);
    checks.disabled = (checks.disabled ?? []).filter((p) => p !== checkId);
    if (checks.severity_overrides![checkId] === "off") {
      delete checks.severity_overrides![checkId];
    }
    return next;
  }
  return setCheckSeverity(profile, checkId, "off");
}

/** Reset a check to its catalog default (remove every override). */
export function resetCheck(profile: Profile, checkId: string): Profile {
  const next = cloneProfile(profile);
  const checks = ensureChecks(next);
  checks.disabled = (checks.disabled ?? []).filter((p) => p !== checkId);
  checks.enabled = (checks.enabled ?? []).filter((p) => p !== checkId);
  delete checks.severity_overrides![checkId];
  return next;
}

// ── Bulk actions ─────────────────────────────────────────────

/** Drop every override so the profile matches catalog defaults. */
export function resetAll(profile: Profile): Profile {
  const next = cloneProfile(profile);
  next.checks = { enabled: [], disabled: [], severity_overrides: {} };
  return next;
}

/** Disable every check in a category. */
export function disableCategory(profile: Profile, categoryId: string): Profile {
  let next = profile;
  const cat = catalog.categories.find((c) => c.id === categoryId);
  if (!cat) return profile;
  for (const check of cat.checks) {
    next = setCheckSeverity(next, check.id, "off");
  }
  return next;
}

/** Re-enable every check in a category to its catalog default. */
export function resetCategory(profile: Profile, categoryId: string): Profile {
  let next = profile;
  const cat = catalog.categories.find((c) => c.id === categoryId);
  if (!cat) return profile;
  for (const check of cat.checks) {
    next = resetCheck(next, check.id);
  }
  return next;
}

/** Demote every ``error`` override to ``advisory``. Handy for "soft mode". */
export function demoteAllErrors(profile: Profile): Profile {
  const next = cloneProfile(profile);
  const checks = ensureChecks(next);
  for (const check of Object.values(catalogByCheckId)) {
    const state = resolveCheckState(next, check.id);
    if (state.enabled && state.severity === "error") {
      checks.severity_overrides![check.id] = "advisory";
    }
  }
  return next;
}

// ── Diff ────────────────────────────────────────────────────

export interface DiffEntry {
  checkId: string;
  name: string;
  categoryId: string;
  from: { enabled: boolean; severity: Severity };
  to: { enabled: boolean; severity: Severity };
}

/** Find every check whose effective state differs between the two profiles.
 *
 * Walks the catalog (so we don't miss checks that have been added
 * to ``disabled`` / ``severity_overrides`` but don't appear in the
 * baseline). The editor uses this both for the inline "changed"
 * indicator and for the Diff view alongside the Rules tab.
 */
export function diffProfiles(baseline: Profile, current: Profile): DiffEntry[] {
  const rows: DiffEntry[] = [];
  for (const [checkId, info] of Object.entries(catalogByCheckId)) {
    const from = resolveCheckState(baseline, checkId);
    const to = resolveCheckState(current, checkId);
    if (from.enabled !== to.enabled || from.severity !== to.severity) {
      rows.push({
        checkId,
        name: info.name,
        categoryId: categoryByCheckId[checkId] ?? "other",
        from,
        to,
      });
    }
  }
  return rows;
}

// ── JSON tab validation ─────────────────────────────────────

export interface JsonValidation {
  valid: boolean;
  error?: string;
  parsed?: Profile;
}

export function validateProfileJson(raw: string): JsonValidation {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    return { valid: false, error: e instanceof Error ? e.message : String(e) };
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return { valid: false, error: "Top-level value must be an object." };
  }
  const p = parsed as Profile;
  if (p.checks !== undefined && typeof p.checks !== "object") {
    return { valid: false, error: "`checks` must be an object." };
  }
  if (p.checks) {
    const { severity_overrides } = p.checks;
    if (severity_overrides) {
      for (const [k, v] of Object.entries(severity_overrides)) {
        if (!["error", "warning", "advisory", "off"].includes(v as string)) {
          return {
            valid: false,
            error: `severity_overrides.${k} must be one of error|warning|advisory|off (got ${JSON.stringify(v)}).`,
          };
        }
      }
    }
  }
  return { valid: true, parsed: p };
}
