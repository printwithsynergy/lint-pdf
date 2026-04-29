import Link from "next/link";
import { Logo } from "./Logo";
import { footerGroups } from "@/lib/navigation";
import { isSaasMode } from "@/lib/site-mode";

export function Footer() {
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "https://app.lintpdf.com";
  const showLogin = isSaasMode();

  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-8 md:grid-cols-5">
          <div className="md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <Logo className="h-12 w-12" />
              <span className="text-2xl font-bold text-brand-900">LintPDF</span>
            </div>
            <p className="text-sm text-slate-500 max-w-sm mb-4">
              Detection-only PDF preflight engine. 500+ checks, PDF/X-1a,
              PDF/X-3, PDF/X-4, and PDF/A conformance verification, zero file
              modifications. API-first, self-service pricing.
            </p>
            {showLogin && (
              <a
                href={`${appUrl}/auth/login`}
                className="inline-flex items-center gap-2 rounded-lg border border-brand-200 px-4 py-2 text-sm font-medium text-brand-700 transition-colors hover:bg-brand-50 hover:border-brand-300"
              >
                Log in
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
                    d="M13 7l5 5m0 0l-5 5m5-5H6"
                  />
                </svg>
              </a>
            )}
          </div>

          {footerGroups.map((group) => (
            <div key={group.title}>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">
                {group.title}
              </h3>
              <ul className="space-y-2 text-sm text-slate-500">
                {group.links.map((link) => (
                  <li key={link.href}>
                    {link.external ? (
                      <a
                        href={link.href}
                        className="hover:text-brand-700 transition-colors"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="hover:text-brand-700 transition-colors"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-slate-200 pt-6 text-center text-xs text-slate-400">
          Made with ✨ by Think Neverland | &copy; {new Date().getFullYear()}
        </div>
      </div>
    </footer>
  );
}
