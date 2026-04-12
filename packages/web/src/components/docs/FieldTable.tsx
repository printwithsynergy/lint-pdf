export interface FieldRow {
  name: string;
  type: string;
  required?: boolean;
  default?: string;
  description: string;
}

export function FieldTable({ rows }: { rows: FieldRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 mb-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Field
            </th>
            <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Type
            </th>
            <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Required
            </th>
            <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Default
            </th>
            <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Description
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name} className="border-b border-slate-100 last:border-0">
              <td className="py-2 px-3 align-top">
                <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                  {row.name}
                </code>
              </td>
              <td className="py-2 px-3 align-top text-xs font-mono text-slate-600">
                {row.type}
              </td>
              <td className="py-2 px-3 align-top text-xs">
                {row.required ? (
                  <span className="text-red-600 font-medium">Yes</span>
                ) : (
                  <span className="text-slate-400">No</span>
                )}
              </td>
              <td className="py-2 px-3 align-top text-xs font-mono text-slate-500">
                {row.default ?? "—"}
              </td>
              <td className="py-2 px-3 align-top text-slate-600">
                {row.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
