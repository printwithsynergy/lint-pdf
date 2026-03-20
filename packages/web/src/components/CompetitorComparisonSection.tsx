import {
  competitors,
  comparisonDimensions,
  type CompetitorCellValue,
} from "@/lib/brand";

function CheckIcon() {
  return (
    <svg
      className="h-5 w-5 text-green-500 mx-auto"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function XIcon() {
  return (
    <svg
      className="h-5 w-5 text-red-400 mx-auto"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

function Cell({
  cell,
  isLintPDF,
}: {
  cell: CompetitorCellValue;
  isLintPDF: boolean;
}) {
  if (cell.type === "boolean") {
    return cell.value ? <CheckIcon /> : <XIcon />;
  }
  if (cell.type === "highlight") {
    return (
      <span className="text-sm font-semibold text-brand-700">{cell.value}</span>
    );
  }
  return (
    <span
      className={`text-sm ${isLintPDF ? "text-brand-700 font-semibold" : "text-slate-600"}`}
    >
      {cell.value}
    </span>
  );
}

export function CompetitorComparisonSection() {
  return (
    <section id="compare" className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl mb-4">
            The only detection-only preflight API
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto">
            More checks, lower cost, zero file modifications. See how LintPDF stacks up.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left min-w-[640px]">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-4 px-5 text-xs font-semibold uppercase tracking-wider text-slate-400 bg-slate-50 w-[180px]">
                    Feature
                  </th>
                  {competitors.map((c) => (
                    <th
                      key={c.shortName}
                      className={`py-4 px-4 text-center text-sm font-semibold ${
                        c.shortName === "lintpdf"
                          ? "bg-brand-900 text-white"
                          : "bg-slate-50 text-slate-700"
                      }`}
                    >
                      {c.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonDimensions.map((dim, i) => (
                  <tr
                    key={dim.label}
                    className={`border-b border-slate-100 last:border-b-0 ${
                      i % 2 === 0 ? "bg-white" : "bg-slate-50/50"
                    }`}
                  >
                    <td className="py-3.5 px-5 text-sm font-medium text-slate-700">
                      {dim.label}
                      {dim.tooltip && (
                        <span
                          className="ml-1 inline-block text-slate-300 cursor-help"
                          title={dim.tooltip}
                        >
                          <svg
                            className="h-3.5 w-3.5 inline"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                          </svg>
                        </span>
                      )}
                    </td>
                    {competitors.map((c) => (
                      <td
                        key={c.shortName}
                        className={`py-3.5 px-4 text-center ${
                          c.shortName === "lintpdf" ? "bg-brand-50/60" : ""
                        }`}
                      >
                        <Cell
                          cell={dim.values[c.shortName]}
                          isLintPDF={c.shortName === "lintpdf"}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="text-center mt-10">
          <a
            href="#pricing"
            className="inline-flex items-center gap-2 rounded-xl bg-brand-900 px-8 py-3 text-sm font-semibold text-white transition-all hover:bg-brand-800 shadow-md shadow-brand-200"
          >
            Start your free preflight in 5 minutes
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 8l4 4m0 0l-4 4m4-4H3"
              />
            </svg>
          </a>
        </div>
      </div>
    </section>
  );
}
