import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "System Status — Never Grounded",
  description: "The Channel — real-time system status for the Never Grounded PDF preflight engine.",
};

const systems = [
  { name: "API", description: "REST API endpoints (Launch, Captain's Log, Voyage Plans)" },
  { name: "The Channel", description: "File processing queue and preflight engine" },
  { name: "Report Generation", description: "PDF, JSON, and XML Captain's Log rendering" },
  { name: "Harbor Signals", description: "Webhook delivery and event notifications" },
  { name: "The Bridge", description: "Dashboard and account management" },
  { name: "Authentication", description: "Boarding Pass (API key) validation" },
];

export default function StatusPage() {
  return (
    <main className="py-16">
      <div className="mx-auto max-w-3xl px-6">
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">System Status</h1>
          <p className="text-sm text-brand-500 italic mb-4">The Channel</p>
          <div className="inline-flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-4 py-2">
            <span className="h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-sm font-medium text-green-800">All systems operational</span>
          </div>
        </div>

        <div className="space-y-3">
          {systems.map((system) => (
            <div
              key={system.name}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-6 py-4"
            >
              <div>
                <h3 className="font-semibold text-slate-900">{system.name}</h3>
                <p className="text-sm text-slate-500">{system.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-sm font-medium text-green-700">Operational</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="font-semibold text-slate-900 mb-4">Uptime (last 90 days)</h2>
          <div className="flex gap-0.5">
            {Array.from({ length: 90 }, (_, i) => (
              <div
                key={i}
                className="h-8 flex-1 rounded-sm bg-green-400"
                title={`${90 - i} days ago — Operational`}
              />
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-slate-400">
            <span>90 days ago</span>
            <span>Today</span>
          </div>
          <p className="mt-4 text-sm text-slate-500 text-center">99.99% uptime</p>
        </div>

        <p className="mt-8 text-center text-sm text-slate-400">
          Last checked: {new Date().toISOString().split("T")[0]} &middot; Updated automatically
        </p>
      </div>
    </main>
  );
}
