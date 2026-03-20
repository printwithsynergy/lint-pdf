"use client";

import { useState } from "react";
import { DesktopOnly } from "./DesktopOnly";
import { useBeta } from "./BetaContext";
import { WaitlistModal } from "./WaitlistModal";

export function CTASection() {
  const { betaMode } = useBeta();
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <section className="relative py-24 overflow-hidden">
      {/*
       * Use inline sRGB gradient instead of Tailwind's bg-gradient-to-*
       * to avoid iOS WebKit black compositing rectangles caused by
       * Tailwind v4's default oklab color interpolation.
       */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to bottom right, #1e3a8a, #1e40af, #172554)",
        }}
      />
      <DesktopOnly>
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
        >
          <div className="absolute top-0 left-1/4 w-[400px] h-[400px] rounded-full bg-brand-400/10 blur-[80px]" />
          <div className="absolute bottom-0 right-1/4 w-[300px] h-[300px] rounded-full bg-brand-300/10 blur-[60px]" />
        </div>
      </DesktopOnly>
      <div className="relative mx-auto max-w-3xl px-6 text-center">
        <h2 className="text-3xl font-bold text-white md:text-4xl mb-4">
          {betaMode ? "Get early access" : "Ready to get started?"}
        </h2>
        <p className="text-brand-200 mb-10 text-lg">
          {betaMode
            ? "Join the waitlist for priority access when we launch."
            : "Start inspecting your PDFs in minutes. Free tier included."}
        </p>
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          {betaMode ? (
            <button
              type="button"
              onClick={() => setWaitlistOpen(true)}
              className="rounded-xl bg-white px-8 py-3.5 text-base font-bold text-brand-900 transition-all hover:bg-brand-50 hover:shadow-xl hover:-translate-y-0.5"
            >
              Join the Waitlist
            </button>
          ) : (
            <a
              href={`${process.env.NEXT_PUBLIC_APP_URL ?? "https://app.lintpdf.com"}/auth/login?plan=free`}
              className="rounded-xl bg-white px-8 py-3.5 text-base font-bold text-brand-900 transition-all hover:bg-brand-50 hover:shadow-xl hover:-translate-y-0.5"
            >
              Get Started
            </a>
          )}
          <a
            href="/docs"
            className="rounded-xl border-2 border-white/20 px-8 py-3.5 text-base font-medium text-white transition-all hover:border-white/40 hover:bg-white/10"
          >
            Read the Docs
          </a>
        </div>
      </div>

      <WaitlistModal
        open={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
      />
    </section>
  );
}
