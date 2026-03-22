import Link from "next/link";

const steps = [
  {
    step: "1",
    title: "Configure folders",
    description:
      "Point the app at directories you want to watch. Set a preflight profile, pass/fail destinations, and file types.",
  },
  {
    step: "2",
    title: "Drop files",
    description:
      "Save or copy artwork into the watched folder from any application. The app detects new files automatically.",
  },
  {
    step: "3",
    title: "Get results instantly",
    description:
      "Files are preflighted and routed to pass or fail directories. Sidecar reports and a live results feed show every detail.",
  },
];

export function HotFolderSection() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid gap-12 md:grid-cols-2 items-center">
          {/* Left — copy */}
          <div>
            <span className="inline-block rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700 mb-4">
              New
            </span>
            <h2 className="text-3xl font-bold text-slate-900 md:text-4xl">
              Hot Folder Desktop App
            </h2>
            <p className="mt-4 text-lg text-slate-500 leading-relaxed">
              Drop files in a folder. Get preflight results. That&apos;s it.
            </p>
            <p className="mt-3 text-slate-500 leading-relaxed">
              A native app for macOS, Windows, and Linux that watches
              directories on your machine and preflights every new file through
              LintPDF. Runs silently in the system tray with a live results
              feed — no code, no scripts, no training.
            </p>
            <div className="mt-8 space-y-4">
              {steps.map((s) => (
                <div key={s.step} className="flex gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">
                    {s.step}
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">{s.title}</p>
                    <p className="text-sm text-slate-500">{s.description}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/docs/desktop-app"
                className="rounded-xl bg-brand-900 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
              >
                Get the Desktop App
              </Link>
              <Link
                href="/docs/integrations-hot-folder"
                className="rounded-xl border-2 border-slate-200 px-6 py-3 text-sm font-medium text-slate-600 transition-all hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50"
              >
                CLI & Docs
              </Link>
            </div>
          </div>

          {/* Right — feature cards */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <svg
                className="h-8 w-8 text-brand-600 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
              <h3 className="font-semibold text-slate-900">Multi-Folder</h3>
              <p className="mt-1 text-xs text-slate-500">
                Unlimited watched directories, each with its own profile and
                output routing.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <svg
                className="h-8 w-8 text-brand-600 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25h-13.5A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0v.894a1.5 1.5 0 01-.44 1.06l-3.06 3.06"
                />
              </svg>
              <h3 className="font-semibold text-slate-900">Cross-Platform</h3>
              <p className="mt-1 text-xs text-slate-500">
                Native app for macOS, Windows, and Linux. One install, no
                dependencies.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <svg
                className="h-8 w-8 text-brand-600 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5"
                />
              </svg>
              <h3 className="font-semibold text-slate-900">Live Results</h3>
              <p className="mt-1 text-xs text-slate-500">
                Real-time feed of every file processed with pass/fail status
                and finding counts.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <svg
                className="h-8 w-8 text-brand-600 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                />
              </svg>
              <h3 className="font-semibold text-slate-900">System Tray</h3>
              <p className="mt-1 text-xs text-slate-500">
                Runs quietly in the background. Desktop notifications when files
                finish.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
