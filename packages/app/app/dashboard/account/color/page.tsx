"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface ColorConfig {
  default_output_condition: string | null;
  default_tac_threshold: number;
  default_safe_zone_margin_mm: number;
  epm_mode_default: boolean;
  target_market: string | null;
  brand_palette: { name: string; value: string }[];
  custom_icc_profiles: { id: string; name: string; color_space: string }[];
  custom_pantone_overrides: Record<
    string,
    { lab: number[]; cmyk_bridge?: number[] }
  > | null;
}

interface GamutCondition {
  slug: string;
  name: string;
  region: string;
  use_case: string;
  tac_limit: number | null;
}

interface PantoneOverridesData {
  count: number;
  overrides: Record<string, { lab: number[]; cmyk_bridge?: number[] }>;
}

export default function ColorConfigPage() {
  const [config, setConfig] = useState<ColorConfig | null>(null);
  const [conditions, setConditions] = useState<GamutCondition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");

  // Editable fields
  const [outputCondition, setOutputCondition] = useState("");
  const [tacThreshold, setTacThreshold] = useState(320);
  const [safeZone, setSafeZone] = useState(3.0);
  const [epmMode, setEpmMode] = useState(false);
  const [targetMarket, setTargetMarket] = useState("");

  // Pantone overrides
  const [overrides, setOverrides] = useState<PantoneOverridesData | null>(null);
  const [overridesLoading, setOverridesLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newLab, setNewLab] = useState(["", "", ""]);
  const [newCmyk, setNewCmyk] = useState(["", "", "", ""]);
  const [savingOverrides, setSavingOverrides] = useState(false);
  const [overrideSearch, setOverrideSearch] = useState("");
  const csvInputRef = useRef<HTMLInputElement>(null);

  const fetchData = useCallback(async () => {
    try {
      const [configResp, conditionsResp] = await Promise.all([
        fetch("/api/grounded/color-config"),
        fetch("/api/grounded/color-config/gamut-conditions"),
      ]);
      if (configResp.ok) {
        const data = await configResp.json();
        setConfig(data);
        setOutputCondition(data.default_output_condition ?? "");
        setTacThreshold(data.default_tac_threshold ?? 320);
        setSafeZone(data.default_safe_zone_margin_mm ?? 3.0);
        setEpmMode(data.epm_mode_default ?? false);
        setTargetMarket(data.target_market ?? "");
      }
      if (conditionsResp.ok) {
        const data = await conditionsResp.json();
        setConditions(data.conditions ?? []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load color config");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchOverrides = useCallback(async () => {
    setOverridesLoading(true);
    try {
      const resp = await fetch("/api/grounded/color-config/pantone-overrides");
      if (resp.ok) {
        const data = await resp.json();
        setOverrides(data);
      }
    } catch {
      // Non-critical — overrides section just shows empty
    } finally {
      setOverridesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    fetchOverrides();
  }, [fetchData, fetchOverrides]);

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const resp = await fetch("/api/grounded/color-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          default_output_condition: outputCondition || null,
          default_tac_threshold: tacThreshold,
          default_safe_zone_margin_mm: safeZone,
          epm_mode_default: epmMode,
          target_market: targetMarket || null,
        }),
      });
      if (!resp.ok) throw new Error("Failed to save color config");
      setSuccess("Color configuration saved");
      await fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleAddOverride() {
    if (!newName.trim()) return;
    const lab = newLab.map(Number);
    if (lab.some(isNaN)) {
      setError("Lab values must be numbers");
      return;
    }

    const cmykValues = newCmyk.map(Number);
    const hasCmyk = newCmyk.some((v) => v !== "");
    if (hasCmyk && cmykValues.some(isNaN)) {
      setError("CMYK values must be numbers");
      return;
    }

    // Merge with existing overrides
    const existing = overrides?.overrides ?? {};
    const entry: { lab: number[]; cmyk_bridge?: number[] } = { lab };
    if (hasCmyk) entry.cmyk_bridge = cmykValues;

    const merged = {
      ...existing,
      [newName.trim().toUpperCase()]: entry,
    };

    await saveOverrides(merged);
    setShowAddForm(false);
    setNewName("");
    setNewLab(["", "", ""]);
    setNewCmyk(["", "", "", ""]);
  }

  async function handleRemoveOverride(name: string) {
    const existing = { ...(overrides?.overrides ?? {}) };
    delete existing[name];
    await saveOverrides(existing);
  }

  async function handleClearAll() {
    setSavingOverrides(true);
    setError("");
    try {
      const resp = await fetch("/api/grounded/color-config/pantone-overrides", {
        method: "DELETE",
      });
      if (!resp.ok && resp.status !== 204)
        throw new Error("Failed to clear overrides");
      setSuccess("All Pantone overrides cleared");
      await fetchOverrides();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to clear overrides");
    } finally {
      setSavingOverrides(false);
    }
  }

  async function saveOverrides(
    data: Record<string, { lab: number[]; cmyk_bridge?: number[] }>,
  ) {
    setSavingOverrides(true);
    setError("");
    try {
      const entries = Object.entries(data).map(([name, values]) => ({
        name,
        lab: values.lab,
        cmyk_bridge: values.cmyk_bridge ?? null,
      }));
      const resp = await fetch("/api/grounded/color-config/pantone-overrides", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overrides: entries }),
      });
      if (!resp.ok) throw new Error("Failed to save Pantone overrides");
      setSuccess("Pantone overrides saved");
      await fetchOverrides();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save overrides");
    } finally {
      setSavingOverrides(false);
    }
  }

  function handleCsvImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (ev) => {
      const text = ev.target?.result as string;
      if (!text) return;

      const lines = text.trim().split("\n");
      const merged = { ...(overrides?.overrides ?? {}) };
      let imported = 0;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line || (i === 0 && line.toLowerCase().includes("name"))) continue;

        // Support comma or pipe delimiter
        const sep = line.includes("|") ? "|" : ",";
        const parts = line.split(sep).map((p) => p.trim());

        if (parts.length < 4) continue;
        const [name, l, a, b, ...rest] = parts;
        const lab = [Number(l), Number(a), Number(b)];
        if (lab.some(isNaN)) continue;

        const entry: { lab: number[]; cmyk_bridge?: number[] } = { lab };
        if (rest.length >= 4) {
          const cmyk = rest.slice(0, 4).map(Number);
          if (!cmyk.some(isNaN)) entry.cmyk_bridge = cmyk;
        }

        merged[name.toUpperCase()] = entry;
        imported++;
      }

      if (imported > 0) {
        await saveOverrides(merged);
        setSuccess(`Imported ${imported} Pantone overrides from CSV`);
      } else {
        setError(
          "No valid rows found in CSV. Expected: Name, L*, a*, b* [, C, M, Y, K]",
        );
      }

      // Reset file input
      if (csvInputRef.current) csvInputRef.current.value = "";
    };
    reader.readAsText(file);
  }

  function handleExportCsv() {
    const entries = Object.entries(overrides?.overrides ?? {});
    if (entries.length === 0) return;

    const header = "Name,L*,a*,b*,C,M,Y,K";
    const rows = entries.map(([name, v]) => {
      const cmyk = v.cmyk_bridge ? v.cmyk_bridge.join(",") : ",,,";
      return `${name},${v.lab.join(",")},${cmyk}`;
    });
    const csv = [header, ...rows].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pantone_overrides.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  // Filter overrides for search
  const filteredOverrides = Object.entries(overrides?.overrides ?? {}).filter(
    ([name]) => name.toLowerCase().includes(overrideSearch.toLowerCase()),
  );

  if (loading) {
    return <SkeletonDashboard type="form" />;
  }

  return (
    <main className="p-8 max-w-4xl">
      <h1 className="font-display text-2xl font-bold">Color Management</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Configure default color management settings for preflight checks.
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}
      {success && (
        <div className="mt-4 rounded-md bg-green-50 p-3 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Output condition */}
      <div className="mt-6 rounded-lg border p-4">
        <h2 className="text-lg font-semibold">Output Condition</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Default target output condition for gamut checking.
        </p>
        <select
          value={outputCondition}
          onChange={(e) => setOutputCondition(e.target.value)}
          className="mt-2 w-full rounded-md border px-3 py-2 text-sm"
        >
          <option value="">None (no gamut checking)</option>
          {conditions.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name} — {c.region} / {c.use_case}
              {c.tac_limit ? ` (TAC ${c.tac_limit}%)` : ""}
            </option>
          ))}
        </select>
      </div>

      {/* Thresholds */}
      <div className="mt-6 rounded-lg border p-4">
        <h2 className="text-lg font-semibold">Default Thresholds</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium">TAC Limit (%)</label>
            <input
              type="number"
              value={tacThreshold}
              onChange={(e) => setTacThreshold(Number(e.target.value))}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">
              Safety Zone Margin (mm)
            </label>
            <input
              type="number"
              step="0.5"
              value={safeZone}
              onChange={(e) => setSafeZone(Number(e.target.value))}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Target Market</label>
            <input
              type="text"
              value={targetMarket}
              onChange={(e) => setTargetMarket(e.target.value)}
              placeholder="e.g. North America, Europe"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input
              type="checkbox"
              id="epm-mode"
              checked={epmMode}
              onChange={(e) => setEpmMode(e.target.checked)}
            />
            <label htmlFor="epm-mode" className="text-sm font-medium">
              HP Indigo EPM Mode
            </label>
          </div>
        </div>
      </div>

      {/* ICC Profiles */}
      {config?.custom_icc_profiles && config.custom_icc_profiles.length > 0 && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">ICC Profiles</h2>
          <div className="mt-2 space-y-1">
            {config.custom_icc_profiles.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded border p-2 text-sm"
              >
                <span>
                  {p.name}{" "}
                  <span className="text-muted-foreground">
                    ({p.color_space})
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Brand palette */}
      {config?.brand_palette && config.brand_palette.length > 0 && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">Brand Palette</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {config.brand_palette.map((color, i) => (
              <div key={i} className="flex items-center gap-1.5 text-sm">
                <div
                  className="h-6 w-6 rounded border"
                  style={{ backgroundColor: color.value }}
                />
                <span>{color.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save Color Configuration"}
      </button>

      {/* Pantone Color Overrides */}
      <div className="mt-10 rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Pantone Color Overrides</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Upload your official Pantone Color Bridge data to override the
              built-in reference values. Overrides take precedence during
              preflight spot color validation.
            </p>
          </div>
          {overrides && overrides.count > 0 && (
            <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
              {overrides.count} override{overrides.count !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-muted"
          >
            {showAddForm ? "Cancel" : "Add Override"}
          </button>
          <label className="cursor-pointer rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-muted">
            Import CSV
            <input
              ref={csvInputRef}
              type="file"
              accept=".csv,.txt"
              onChange={handleCsvImport}
              className="hidden"
            />
          </label>
          {overrides && overrides.count > 0 && (
            <>
              <button
                onClick={handleExportCsv}
                className="rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-muted"
              >
                Export CSV
              </button>
              <button
                onClick={handleClearAll}
                disabled={savingOverrides}
                className="rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10"
              >
                Clear All
              </button>
            </>
          )}
        </div>

        {/* CSV format help */}
        <p className="mt-2 text-xs text-muted-foreground">
          CSV format: <code>Name, L*, a*, b* [, C, M, Y, K]</code> — pipe or
          comma delimited. First row header is auto-skipped.
        </p>

        {/* Add form */}
        {showAddForm && (
          <div className="mt-4 rounded-md border bg-muted/30 p-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium">
                  Pantone Name
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. PANTONE 485 C"
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium">
                  Lab Values (L*, a*, b*)
                </label>
                <div className="mt-1 flex gap-1">
                  {["L*", "a*", "b*"].map((label, i) => (
                    <input
                      key={label}
                      type="number"
                      step="0.01"
                      placeholder={label}
                      value={newLab[i]}
                      onChange={(e) => {
                        const updated = [...newLab];
                        updated[i] = e.target.value;
                        setNewLab(updated);
                      }}
                      className="w-full rounded-md border px-2 py-2 text-sm"
                    />
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium">
                  CMYK Bridge (optional)
                </label>
                <div className="mt-1 flex gap-1">
                  {["C", "M", "Y", "K"].map((label, i) => (
                    <input
                      key={label}
                      type="number"
                      step="0.1"
                      placeholder={label}
                      value={newCmyk[i]}
                      onChange={(e) => {
                        const updated = [...newCmyk];
                        updated[i] = e.target.value;
                        setNewCmyk(updated);
                      }}
                      className="w-full rounded-md border px-2 py-2 text-sm"
                    />
                  ))}
                </div>
              </div>
            </div>
            <button
              onClick={handleAddOverride}
              disabled={savingOverrides || !newName.trim()}
              className="mt-3 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {savingOverrides ? "Saving..." : "Add Override"}
            </button>
          </div>
        )}

        {/* Search & list */}
        {overrides && overrides.count > 0 && (
          <div className="mt-4">
            {overrides.count > 5 && (
              <input
                type="text"
                value={overrideSearch}
                onChange={(e) => setOverrideSearch(e.target.value)}
                placeholder="Search overrides..."
                className="mb-2 w-full rounded-md border px-3 py-2 text-sm"
              />
            )}
            <div className="max-h-80 overflow-y-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted text-left">
                  <tr>
                    <th className="px-3 py-2 font-medium">Name</th>
                    <th className="px-3 py-2 font-medium">Lab</th>
                    <th className="px-3 py-2 font-medium">CMYK Bridge</th>
                    <th className="px-3 py-2 font-medium w-16"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filteredOverrides.map(([name, v]) => (
                    <tr key={name} className="hover:bg-muted/50">
                      <td className="px-3 py-2 font-mono text-xs">{name}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {v.lab.map((n) => n.toFixed(1)).join(", ")}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {v.cmyk_bridge
                          ? v.cmyk_bridge.map((n) => n.toFixed(0)).join(", ")
                          : "—"}
                      </td>
                      <td className="px-3 py-2">
                        <button
                          onClick={() => handleRemoveOverride(name)}
                          className="text-xs text-destructive hover:underline"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                  {filteredOverrides.length === 0 && (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-3 py-4 text-center text-muted-foreground"
                      >
                        No overrides match your search.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {overridesLoading && (
          <p className="mt-3 text-sm text-muted-foreground">
            Loading overrides...
          </p>
        )}
        {!overridesLoading && (!overrides || overrides.count === 0) && (
          <p className="mt-3 text-sm text-muted-foreground">
            No Pantone overrides configured. Add individual colors or import a
            CSV from your Color Bridge data.
          </p>
        )}
      </div>
    </main>
  );
}
