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

/** Generate a distinct hue for spot colors based on name hash. */
function spotColorHue(name: string): string {
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
  jobId,
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
      <div className="p-3 text-xs text-muted-foreground">
        Loading separations...
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
    <div className="space-y-3 p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Separations</h3>
        <div className="flex gap-1">
          <button
            onClick={() => onSetAllChannels(true)}
            className="rounded border px-2 py-0.5 text-xs hover:bg-muted"
          >
            All On
          </button>
          <button
            onClick={() => onSetAllChannels(false)}
            className="rounded border px-2 py-0.5 text-xs hover:bg-muted"
          >
            All Off
          </button>
        </div>
      </div>

      {/* Process channels (CMYK) */}
      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">Process</p>
        {processChannels.map((ch) => (
          <ChannelToggle
            key={ch.name}
            name={ch.name}
            color={CHANNEL_COLORS[ch.name] ?? spotColorHue(ch.name)}
            enabled={enabledChannels.has(ch.name)}
            onToggle={() => onToggleChannel(ch.name)}
          />
        ))}
      </div>

      {/* Spot colors */}
      {spotChannels.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">
            Spot Colors ({spotChannels.length})
          </p>
          {spotChannels.map((ch) => (
            <ChannelToggle
              key={ch.name}
              name={ch.name}
              color={spotColorHue(ch.name)}
              enabled={enabledChannels.has(ch.name)}
              onToggle={() => onToggleChannel(ch.name)}
            />
          ))}
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
    <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-muted">
      <input
        type="checkbox"
        checked={enabled}
        onChange={onToggle}
        className="rounded border-border"
      />
      <span
        className="inline-block h-3 w-3 rounded-full border"
        style={{ backgroundColor: color }}
      />
      <span className="truncate text-xs">{name}</span>
    </label>
  );
}
