"use client";

import Link from "next/link";
import { useState } from "react";
import { Logo } from "./Logo";
import { useBeta } from "./BetaContext";
import { WaitlistModal } from "./WaitlistModal";
import { headerLinks } from "@/lib/navigation";

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const { betaMode } = useBeta();

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "https://app.lintpdf.com";
  const ctaLabel = betaMode ? "Join Waitlist" : "Get Started";
  const ctaHref = betaMode ? undefined : `${appUrl}/auth/login?plan=free`;

  return (
    // skipcq: JS-0415
    <>
      <header className="fixed top-0 z-50 w-full border-b border-slate-200/60 bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <Logo className="h-9 w-9" />
            <div className="flex flex-col leading-none">
              <span className="text-lg font-semibold tracking-tight text-brand-900">
                LintPDF
              </span>
              <span className="text-[9px] font-medium tracking-wide text-slate-400">
                Every check. Every page. Every time.
              </span>
            </div>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden items-center gap-8 md:flex">
            {headerLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-slate-500 transition-colors hover:text-brand-700"
              >
                {link.label}
              </Link>
            ))}
            {ctaHref ? (
              <a
                href={ctaHref}
                className="rounded-lg bg-brand-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800"
              >
                {ctaLabel}
              </a>
            ) : (
              <button
                type="button"
                onClick={() => setWaitlistOpen(true)}
                className="rounded-lg bg-brand-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800"
              >
                {ctaLabel}
              </button>
            )}
          </nav>

          {/* Mobile toggle */}
          <button
            className="md:hidden text-slate-500 hover:text-brand-900"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {mobileOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile nav */}
        {mobileOpen && (
          <nav className="border-t border-slate-200/60 bg-white px-6 py-4 md:hidden">
            {headerLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block py-2 text-sm text-slate-500 hover:text-brand-700"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            {ctaHref ? (
              <a
                href={ctaHref}
                className="mt-3 block rounded-lg bg-brand-900 px-4 py-2 text-center text-sm font-medium text-white"
              >
                {ctaLabel}
              </a>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setMobileOpen(false);
                  setWaitlistOpen(true);
                }}
                className="mt-3 w-full rounded-lg bg-brand-900 px-4 py-2 text-center text-sm font-medium text-white"
              >
                {ctaLabel}
              </button>
            )}
          </nav>
        )}
      </header>

      <WaitlistModal
        open={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
      />
    </>
  );
}
