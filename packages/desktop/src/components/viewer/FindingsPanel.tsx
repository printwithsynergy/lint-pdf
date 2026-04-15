import { AlertOctagon, AlertTriangle, Info } from "lucide-react";
import type { ViewerFinding } from "../../lib/types";

interface FindingsPanelProps {
  findings: ViewerFinding[];
  selectedIdx: number | null;
  onSelect: (idx: number) => void;
  currentPage: number;
}

function severityIcon(severity: string) {
  if (severity === "error") {
    return <AlertOctagon className="h-3.5 w-3.5 shrink-0 text-red-600" />;
  }
  if (severity === "warning") {
    return <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600" />;
  }
  return <Info className="h-3.5 w-3.5 shrink-0 text-sky-600" />;
}

export function FindingsPanel({
  findings,
  selectedIdx,
  onSelect,
  currentPage,
}: FindingsPanelProps) {
  if (findings.length === 0) {
    return (
      <div className="p-4 text-xs text-gray-500">
        No findings on this job. The preflight profile didn't raise anything.
      </div>
    );
  }

  const grouped = {
    error: findings.filter((f) => f.severity === "error"),
    warning: findings.filter((f) => f.severity === "warning"),
    other: findings.filter(
      (f) => f.severity !== "error" && f.severity !== "warning",
    ),
  };

  return (
    <ul className="divide-y divide-gray-100 text-xs">
      {(["error", "warning", "other"] as const).map((bucket) =>
        grouped[bucket].map((f) => {
          const globalIdx = findings.indexOf(f);
          const active = globalIdx === selectedIdx;
          const onThisPage = f.page_num === currentPage;
          return (
            <li
              key={`${globalIdx}-${f.inspection_id}`}
              onClick={() => onSelect(globalIdx)}
              className={`flex cursor-pointer items-start gap-2 px-3 py-2 ${
                active ? "bg-brand-50" : "hover:bg-gray-50"
              }`}
            >
              {severityIcon(f.severity)}
              <div className="min-w-0 flex-1">
                <p className={`${onThisPage ? "font-medium" : ""} break-words`}>
                  {f.message}
                </p>
                <p className="mt-0.5 flex items-center gap-2 text-[11px] text-gray-400">
                  <span>{f.inspection_id}</span>
                  {f.page_num !== null && f.page_num !== undefined && (
                    <span>
                      · page {f.page_num}
                      {onThisPage ? "" : " (jump)"}
                    </span>
                  )}
                  {f.category && <span>· {f.category}</span>}
                </p>
              </div>
            </li>
          );
        }),
      )}
    </ul>
  );
}
