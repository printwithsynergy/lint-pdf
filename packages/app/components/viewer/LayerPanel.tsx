"use client";

import { useCallback, useEffect, useState } from "react";
import type { LayerInfo } from "./types";
import { useViewerApi } from "./types";

interface LayerPanelProps {
  jobId: string;
  enabledLayers: Set<number>;
  onToggleLayer: (ocgIndex: number) => void;
  onSetAllLayers: (enabled: boolean) => void;
}

export function LayerPanel({
  jobId,
  enabledLayers,
  onToggleLayer,
  onSetAllLayers,
}: LayerPanelProps) {
  const { apiBase } = useViewerApi();
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchLayers = useCallback(async () => {
    try {
      const resp = await fetch(`${apiBase}/layers`);
      if (!resp.ok) throw new Error("Failed to load layers");
      const data = await resp.json();
      setLayers(data.layers ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load layers");
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchLayers();
  }, [fetchLayers]);

  if (loading) {
    return (
      <div className="p-3 text-xs text-muted-foreground">Loading layers...</div>
    );
  }

  if (error) {
    return <div className="p-3 text-xs text-destructive">{error}</div>;
  }

  if (layers.length === 0) {
    return (
      <div className="p-3 text-xs text-muted-foreground">
        This PDF has no optional content layers (OCGs).
      </div>
    );
  }

  return (
    <div className="space-y-3 p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Layers</h3>
        <div className="flex gap-1">
          <button
            onClick={() => onSetAllLayers(true)}
            className="rounded border px-2 py-0.5 text-xs hover:bg-muted"
          >
            All On
          </button>
          <button
            onClick={() => onSetAllLayers(false)}
            className="rounded border px-2 py-0.5 text-xs hover:bg-muted"
          >
            All Off
          </button>
        </div>
      </div>

      <div className="space-y-1">
        {layers.map((layer) => (
          <label
            key={layer.ocg_index}
            className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-muted"
          >
            <input
              type="checkbox"
              checked={enabledLayers.has(layer.ocg_index)}
              onChange={() => onToggleLayer(layer.ocg_index)}
              className="rounded border-border"
            />
            <span className="inline-block h-3 w-3 rounded border bg-violet-400/40" />
            <span className="truncate text-xs">{layer.name}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
