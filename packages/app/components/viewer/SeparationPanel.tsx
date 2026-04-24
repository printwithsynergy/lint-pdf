"use client";

import { useCallback, useEffect, useState } from "react";
import { useViewerApi } from "./types";

interface SeparationChannel {
  name: string;
  type: "process" | "spot";
}

/** Representative CSS colors for each channel. */
const CHANNEL_COLORS: Record<string, string> = {
  Cyan: "#00bcd4",
  Magenta: "#e91e63",
  Yellow: "#fdd835",
  Black: "#212121",
};

/**
 * Map a spot-color name to a swatch colour.
 *
 * Pre-WS-17 the swatch was always derived from a hash of the
 * spot's name (`spotColorHue`), which produced absurd results for
 * spots whose name *is* the colour: "Black" landed as a
 * mid-saturation green, "Foil 425" as bright green, etc.
 *
 * The new precedence order:
 *  1. Exact / case-insensitive match against known process
 *     channels ("Black", "Cyan", "Magenta", "Yellow", "K", "C",
 *     "M", "Y", "White") — render the actual ink colour.
 *  2. Substring match against common colour words ("black",
 *     "white", "silver", "gold", "foil", "beige", "buff", "cream",
 *     "tan") and well-known print-process tokens ("cut", "die",
 *     "crease", "perf", "varnish", "uv") — pick a sensible
 *     representative.
 *  3. Hash-based hue fallback for everything else, kept stable so
 *     the same spot name always renders the same swatch.
 */
function spotSwatchColor(name: string): string {
  const lowered = name.trim().toLowerCase();
  const exact: Record<string, string> = {
    black: "#212121",
    k: "#212121",
    cyan: "#00bcd4",
    c: "#00bcd4",
    magenta: "#e91e63",
    m: "#e91e63",
    yellow: "#fdd835",
    y: "#fdd835",
    white: "#f8fafc",
  };
  if (lowered in exact) return exact[lowered]!;

  // Substring matchers (ordered most → least specific).
  const substringMatchers: [RegExp, string][] = [
    [/cut\s*contour|dieline|die\s*line|kiss\s*cut|\bdie\b|\bcut\b|crease|perf|fold|score/, "#dc2626"], // print-process / dieline → red
    [/varnish|spot\s*uv|gloss|matte/, "#a3a3a3"],
    [/foil|silver|metal|chrome/, "#9ca3af"],
    [/gold/, "#d4af37"],
    [/copper|bronze/, "#b87333"],
    [/black|noir|onyx/, "#212121"],
    [/white|ivory|cream/, "#f8fafc"],
    [/beige|tan|sand/, "#d4a373"],
    [/buff/, "#ddc593"],
    [/red|crimson|maroon/, "#dc2626"],
    [/orange/, "#ea580c"],
    [/blue|navy|cobalt/, "#2563eb"],
    [/green|teal|mint|sage/, "#16a34a"],
    [/purple|violet|lavender/, "#7c3aed"],
    [/pink|rose|fuchsia/, "#ec4899"],
    [/brown/, "#8b5a2b"],
    [/grey|gray|slate/, "#64748b"],
  ];
  for (const [re, color] of substringMatchers) {
    if (re.test(lowered)) return color;
  }

  // Stable hash → HSL for unknown spots.
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 60%, 50%)`;
}

interface SeparationPanelProps {
  jobId: string;
  enabledChannels: Set<string>;
  onToggleChannel: (channel: string) => void;
  onSetAllChannels: (enabled: boolean) => void;
}

export function SeparationPanel({
  jobId: _jobId,
  enabledChannels,
  onToggleChannel,
  onSetAllChannels,
}: SeparationPanelProps) {
  const { apiBase } = useViewerApi();
  const [channels, setChannels] = useState<SeparationChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchChannels = useCallback(async () => {
    try {
      const resp = await fetch(`${apiBase}/separations`);
      if (!resp.ok) throw new Error("Failed to load separations");
      const data = await resp.json();
      setChannels(data.channels ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load channels");
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchChannels();
  }, [fetchChannels]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-6">
        <svg className="h-6 w-6 animate-spin text-slate-400" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
        <span className="text-xs text-slate-500">Loading separations</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 text-xs text-destructive">{error}</div>
    );
  }

  const processChannels = channels.filter((c) => c.type === "process");
  const spotChannels = channels.filter((c) => c.type === "spot");

  return (
    <div className="space-y-3 p-3 text-slate-200">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Separations</h3>
        <div className="flex gap-1">
          <button
            onClick={() => onSetAllChannels(true)}
            className="rounded border border-white/10 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            All On
          </button>
          <button
            onClick={() => onSetAllChannels(false)}
            className="rounded border border-white/10 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            All Off
          </button>
        </div>
      </div>

      {/* Process channels (CMYK) */}
      <div>
        <p className="mb-1 text-xs font-medium text-slate-400">Process</p>
        <div className="grid grid-cols-2 gap-0.5">
        {processChannels.map((ch) => (
          <ChannelToggle
            key={ch.name}
            name={ch.name}
            color={CHANNEL_COLORS[ch.name] ?? spotSwatchColor(ch.name)}
            enabled={enabledChannels.has(ch.name)}
            onToggle={() => onToggleChannel(ch.name)}
          />
        ))}
        </div>
      </div>

      {/* Spot colors */}
      {spotChannels.length > 0 && (
        <div className="space-y-1">
          <p className="mb-1 text-xs font-medium text-slate-400">
            Spot Colors ({spotChannels.length})
          </p>
          <div className="grid grid-cols-2 gap-0.5">
          {spotChannels.map((ch) => (
            <ChannelToggle
              key={ch.name}
              name={ch.name}
              color={spotSwatchColor(ch.name)}
              enabled={enabledChannels.has(ch.name)}
              onToggle={() => onToggleChannel(ch.name)}
            />
          ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ChannelToggle({
  name,
  color,
  enabled,
  onToggle,
}: {
  name: string;
  color: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-slate-200 hover:bg-slate-800">
      <input
        type="checkbox"
        checked={enabled}
        onChange={onToggle}
        className="rounded border-white/10"
      />
      <span
        className="inline-block h-3 w-3 shrink-0 rounded-full border border-white/10"
        style={{ backgroundColor: color }}
      />
      <span className="truncate text-xs">{name}</span>
    </label>
  );
}
