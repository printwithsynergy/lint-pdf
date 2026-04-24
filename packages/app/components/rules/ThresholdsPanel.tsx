"use client";

/**
 * Per-profile threshold editor.
 *
 * Surfaces numeric / string thresholds that previously were only
 * editable via the JSON tab. First concrete use: PDF version
 * constraints (T1-CMP02 LPDF_DOC_009) — ``min_pdf_version`` and
 * ``max_pdf_version`` on ``profile.thresholds``.
 *
 * Designed as a generic section container with one "Thresholds"
 * block at the top of the Rules tab; additional threshold groups
 * (expected page size, TAC limit, etc.) can be added here without
 * restructuring the page.
 */

import { useState } from "react";
import type { Profile } from "@/lib/rules/profile-utils";

const PDF_VERSIONS = ["1.3", "1.4", "1.5", "1.6", "1.7", "2.0"];
const PDF_VERSION_RE = /^\d+\.\d+$/;

export interface ThresholdsPanelProps {
  profile: Profile;
  onChange: (next: Profile) => void;
  readOnly?: boolean;
}

export function ThresholdsPanel({
  profile,
  onChange,
  readOnly = false,
}: ThresholdsPanelProps) {
  const [collapsed, setCollapsed] = useState(true);

  const thresholds =
    (profile.thresholds as Record<string, unknown> | undefined) ?? {};
  const changedCount = countChangedVersionFields(thresholds);

  return (
    <div className="mb-3 rounded-md border">
      <button
        onClick={() => setCollapsed((v) => !v)}
        className="flex w-full items-center justify-between border-b bg-muted/20 px-3 py-2 text-left"
      >
        <span className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {collapsed ? "▸" : "▾"}
          </span>
          <span className="font-medium">Thresholds</span>
          <span className="text-xs text-muted-foreground">
            PDF version constraints
            {changedCount > 0 && ` · ${changedCount} set`}
          </span>
        </span>
      </button>
      {!collapsed && (
        <div className="p-3">
          <PdfVersionConstraints
            profile={profile}
            onChange={onChange}
            readOnly={readOnly}
          />
        </div>
      )}
    </div>
  );
}

// ── PDF version constraints (T1-CMP02) ─────────────────────────

function PdfVersionConstraints({
  profile,
  onChange,
  readOnly,
}: {
  profile: Profile;
  onChange: (next: Profile) => void;
  readOnly: boolean;
}) {
  const thresholds =
    (profile.thresholds as Record<string, unknown> | undefined) ?? {};
  const minRaw = thresholds.min_pdf_version;
  const maxRaw = thresholds.max_pdf_version;
  const minStr = typeof minRaw === "string" ? minRaw : "";
  const maxStr = typeof maxRaw === "string" ? maxRaw : "";

  const minError = minStr && !PDF_VERSION_RE.test(minStr) ? "Invalid version" : null;
  const maxError = maxStr && !PDF_VERSION_RE.test(maxStr) ? "Invalid version" : null;
  const rangeError =
    !minError &&
    !maxError &&
    minStr &&
    maxStr &&
    compareVersions(minStr, maxStr) > 0
      ? "min_pdf_version must be ≤ max_pdf_version"
      : null;

  function setField(key: "min_pdf_version" | "max_pdf_version", value: string) {
    const next: Profile = {
      ...profile,
      thresholds: { ...thresholds, [key]: value || undefined },
    };
    // Strip undefined keys so the JSON tab doesn't show them.
    const cleaned: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(next.thresholds ?? {})) {
      if (v !== undefined && v !== "") cleaned[k] = v;
    }
    next.thresholds = cleaned;
    onChange(next);
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="mb-1 text-xs text-muted-foreground">
          Fires <code className="font-mono">LPDF_DOC_009</code> when the PDF
          header version sits outside this range. Either bound may be omitted;
          omitting both disables the check.
        </p>
      </div>
      <div className="flex flex-wrap gap-4">
        <VersionField
          label="Minimum PDF version"
          value={minStr}
          error={minError}
          readOnly={readOnly}
          onChange={(v) => setField("min_pdf_version", v)}
          helper="e.g. 1.6 for PDF/X-4 workflows"
        />
        <VersionField
          label="Maximum PDF version"
          value={maxStr}
          error={maxError}
          readOnly={readOnly}
          onChange={(v) => setField("max_pdf_version", v)}
          helper="e.g. 1.4 for PDF/X-1a-2003 workflows"
        />
      </div>
      {rangeError && (
        <p className="text-xs text-destructive">{rangeError}</p>
      )}
    </div>
  );
}

function VersionField({
  label,
  value,
  error,
  readOnly,
  onChange,
  helper,
}: {
  label: string;
  value: string;
  error: string | null;
  readOnly: boolean;
  onChange: (v: string) => void;
  helper: string;
}) {
  const listId = `ver-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div className="flex min-w-[180px] flex-col">
      <label className="text-xs font-medium">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value.trim())}
        list={listId}
        placeholder="—"
        disabled={readOnly}
        className={`mt-1 w-28 rounded border px-2 py-1 text-sm ${error ? "border-destructive" : ""}`}
      />
      <datalist id={listId}>
        {PDF_VERSIONS.map((v) => (
          <option key={v} value={v} />
        ))}
      </datalist>
      {error ? (
        <span className="mt-1 text-xs text-destructive">{error}</span>
      ) : (
        <span className="mt-1 text-xs text-muted-foreground">{helper}</span>
      )}
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────

function compareVersions(a: string, b: string): number {
  const [aMajor = 0, aMinor = 0] = a.split(".").map(Number);
  const [bMajor = 0, bMinor = 0] = b.split(".").map(Number);
  if (aMajor !== bMajor) return aMajor - bMajor;
  return aMinor - bMinor;
}

function countChangedVersionFields(
  thresholds: Record<string, unknown>,
): number {
  let n = 0;
  if (typeof thresholds.min_pdf_version === "string" && thresholds.min_pdf_version)
    n += 1;
  if (typeof thresholds.max_pdf_version === "string" && thresholds.max_pdf_version)
    n += 1;
  return n;
}
