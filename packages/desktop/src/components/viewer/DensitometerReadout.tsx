import { Loader } from "lucide-react";
import type { DensitometerResponse } from "../../lib/types";

interface DensitometerReadoutProps {
  sample: DensitometerResponse | null;
  loading: boolean;
  error: string | null;
}

/** Approximate display colour for the headline process channels so
 * the percentage bar reads at a glance. Spot channels fall back to
 * neutral grey. */
const SWATCH: Record<string, string> = {
  Cyan: "bg-cyan-400",
  Magenta: "bg-fuchsia-500",
  Yellow: "bg-yellow-300",
  Black: "bg-neutral-800",
};

export function DensitometerReadout({
  sample,
  loading,
  error,
}: DensitometerReadoutProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 p-4 text-xs text-gray-500">
        <Loader className="h-4 w-4 animate-spin" /> Sampling…
      </div>
    );
  }
  if (error) {
    return (
      <div className="p-4 text-xs text-red-600 whitespace-pre-wrap">{error}</div>
    );
  }
  if (!sample) {
    return (
      <div className="p-4 text-xs text-gray-500">
        Click anywhere on the page to sample ink coverage at that point.
        Sampling is done server-side at 300 DPI and returns per-channel
        coverage plus the summed TAC.
      </div>
    );
  }

  return (
    <div className="space-y-3 p-3 text-xs">
      <p className="text-gray-500">
        Sampled at ({sample.x.toFixed(1)}, {sample.y.toFixed(1)}) pts · DPI{" "}
        {sample.dpi}
      </p>

      <ul className="space-y-1.5">
        {sample.channels.map((c) => {
          const swatch = SWATCH[c.name] ?? "bg-gray-300";
          return (
            <li key={c.name} className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded ${swatch}`} />
              <span className="w-24 truncate" title={c.name}>
                {c.name}
              </span>
              <div className="relative flex-1 overflow-hidden rounded bg-gray-100">
                <div
                  className={`h-2 rounded ${swatch}`}
                  style={{
                    width: `${Math.min(100, Math.max(0, c.percent))}%`,
                  }}
                />
              </div>
              <span className="w-12 text-right font-mono text-gray-700">
                {c.percent.toFixed(1)}%
              </span>
            </li>
          );
        })}
      </ul>

      <div
        className={`rounded p-2 ${
          sample.limit_exceeded
            ? "bg-red-50 text-red-800"
            : "bg-gray-50 text-gray-700"
        }`}
      >
        <p className="flex items-center justify-between">
          <span className="font-medium">Total ink (TAC)</span>
          <span className="font-mono">{sample.tac.toFixed(1)}%</span>
        </p>
        <p className="mt-0.5 text-[11px]">
          Limit: {sample.tac_limit.toFixed(0)}%{" "}
          {sample.limit_exceeded ? "· exceeds" : "· within limit"}
        </p>
      </div>
    </div>
  );
}
