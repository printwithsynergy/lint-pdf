import { glossary } from "@/lib/brand";

export default function GlossaryPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Glossary</h2>
      <p className="text-slate-600 mb-6">LintPDF terminology reference.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b-2 border-slate-200">
              <th className="text-left py-2 px-3 text-slate-500 font-medium">
                Concept
              </th>
              <th className="text-left py-2 px-3 text-slate-500 font-medium">
                LintPDF Term
              </th>
              <th className="text-left py-2 px-3 text-slate-500 font-medium">
                Used In
              </th>
            </tr>
          </thead>
          <tbody>
            {glossary.map((item) => (
              <tr key={item.term} className="border-b border-slate-100">
                <td className="py-2 px-3 text-slate-600">{item.concept}</td>
                <td className="py-2 px-3 font-medium text-slate-800">
                  {item.term}
                </td>
                <td className="py-2 px-3 text-slate-500">{item.usage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
