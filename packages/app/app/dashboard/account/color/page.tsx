"use client";

import { useCallback, useEffect, useState } from "react";

interface ColorConfig {
  default_output_condition: string | null;
  default_tac_threshold: number;
  default_safe_zone_margin_mm: number;
  epm_mode_default: boolean;
  target_market: string | null;
  brand_palette: { name: string; value: string }[];
  custom_icc_profiles: { id: string; name: string; color_space: string }[];
}

interface GamutCondition {
  slug: string;
  name: string;
  region: string;
  use_case: string;
  tac_limit: number | null;
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

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  if (loading) {
    return (
      <main className="p-8">
        <h1 className="font-display text-2xl font-bold">Color Management</h1>
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </main>
    );
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
    </main>
  );
}
