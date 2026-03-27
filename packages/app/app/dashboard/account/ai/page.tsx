"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface AiConfig {
  ai_enabled: boolean;
  categories: string[];
  credits_used: number;
  credits_limit: number;
  trial_enabled: boolean;
  trial_expires_at: string | null;
  custom_dictionary_words: string[];
  reference_logos: { id: string; name: string }[];
}

const AI_CATEGORIES = [
  { id: "barcode_detection", label: "Barcode Detection & Grading" },
  { id: "regulatory_compliance", label: "Regulatory Label Compliance" },
  { id: "brand_compliance", label: "Brand Compliance" },
  { id: "spell_check", label: "Spell Check" },
  { id: "content_quality", label: "Content Quality Analysis" },
  { id: "color_analysis", label: "Color Analysis" },
];

export default function AiConfigPage() {
  const [config, setConfig] = useState<AiConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [enabledCategories, setEnabledCategories] = useState<string[]>([]);
  const [dictionaryText, setDictionaryText] = useState("");

  const fetchConfig = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/ai-config");
      if (!resp.ok) throw new Error("Failed to load AI config");
      const data = await resp.json();
      setConfig(data);
      setEnabledCategories(data.categories ?? []);
      setDictionaryText((data.custom_dictionary_words ?? []).join("\n"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load AI config");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const resp = await fetch("/api/lintpdf/ai-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          categories: enabledCategories,
          custom_dictionary_words: dictionaryText
            .split("\n")
            .map((w) => w.trim())
            .filter(Boolean),
        }),
      });
      if (!resp.ok) throw new Error("Failed to save AI config");
      setSuccess("AI configuration saved");
      await fetchConfig();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  function toggleCategory(catId: string) {
    setEnabledCategories((prev) =>
      prev.includes(catId) ? prev.filter((c) => c !== catId) : [...prev, catId],
    );
  }

  if (loading) {
    return <SkeletonDashboard type="form" />;
  }

  return (
    <>
      <h1 className="font-display text-2xl font-bold">AI Configuration</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Configure AI-powered preflight checks for your organization.
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

      {/* Credits */}
      {config && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">AI Credits</h2>
          <div className="mt-2 flex gap-4 text-sm">
            <span>
              Used: <strong>{config.credits_used}</strong>
            </span>
            <span>
              Limit: <strong>{config.credits_limit}</strong>
            </span>
            {config.trial_enabled && (
              <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs text-yellow-700">
                Trial
                {config.trial_expires_at &&
                  ` (expires ${new Date(config.trial_expires_at).toLocaleDateString()})`}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Categories */}
      <div className="mt-6 rounded-lg border p-4">
        <h2 className="text-lg font-semibold">AI Categories</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Enable or disable AI-powered check categories.
        </p>
        <div className="mt-3 space-y-2">
          {AI_CATEGORIES.map((cat) => (
            <label key={cat.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={enabledCategories.includes(cat.id)}
                onChange={() => toggleCategory(cat.id)}
              />
              {cat.label}
            </label>
          ))}
        </div>
      </div>

      {/* Custom dictionary */}
      <div className="mt-6 rounded-lg border p-4">
        <h2 className="text-lg font-semibold">Custom Dictionary</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Add custom words for spell check (one per line). These words will not
          be flagged as misspellings.
        </p>
        <textarea
          value={dictionaryText}
          onChange={(e) => setDictionaryText(e.target.value)}
          rows={6}
          className="mt-2 w-full rounded-md border px-3 py-2 text-sm font-mono"
          placeholder="brandname&#10;productterm&#10;customword"
        />
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save AI Configuration"}
      </button>
    </>
  );
}
