import type { TacRun } from "../../lib/types";

interface TACPanelProps {
  enabled: boolean;
  tacLimit: number;
  onToggle: (enabled: boolean) => void;
  onLimitChange: (limit: number) => void;
  runs: TacRun[];
}

export function TACPanel({
  enabled,
  tacLimit,
  onToggle,
  onLimitChange,
  runs,
}: TACPanelProps) {
  const exceedingCount = runs.filter((r) => r.exceeds).length;
  return (
    <div className="p-3 text-xs">
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
          className="rounded border-gray-300"
        />
        <span className="font-medium">Show TAC heatmap</span>
      </label>
      <p className="mt-1 text-gray-500">
        Highlights regions of the page where the summed CMYK+spot ink
        coverage meets or exceeds the limit.
      </p>

      <div className="mt-3">
        <label className="label">
          Ink limit: {tacLimit}%
        </label>
        <input
          type="range"
          min={100}
          max={500}
          step={10}
          value={tacLimit}
          onChange={(e) => onLimitChange(parseInt(e.target.value, 10))}
          className="w-full"
        />
        <div className="flex justify-between text-[10px] text-gray-400">
          <span>100%</span>
          <span>300%</span>
          <span>500%</span>
        </div>
      </div>

      {enabled && (
        <div className="mt-3 space-y-1">
          <p className="font-medium text-gray-700">
            Runs on this page: {runs.length}
            {exceedingCount > 0 && (
              <span className="ml-1 text-red-600">
                · {exceedingCount} exceed
              </span>
            )}
          </p>
          <p className="text-[11px] text-gray-400">
            Solid red outlines mark runs that meet or exceed the limit;
            dashed amber outlines are below-limit runs.
          </p>
        </div>
      )}
    </div>
  );
}
