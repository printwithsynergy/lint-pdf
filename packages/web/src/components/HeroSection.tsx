"use client";

import { useState } from "react";
import { DesktopOnly } from "./DesktopOnly";
import { MarketingLogo } from "./Logo";
import { ParticleField } from "./ParticleField";
import { useBeta } from "./BetaContext";
import { WaitlistModal } from "./WaitlistModal";

export function HeroSection() {
  const { betaMode } = useBeta();
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    // skipcq: JS-0415
    <section className="relative overflow-hidden hero-gradient min-h-[90vh] flex items-center">
      {/* Animated particle pixie dust */}
      <ParticleField />

      {/* Soft background orbs — removed from DOM on mobile to avoid iOS WebKit GPU compositing artifacts from blur filters */}
      <DesktopOnly>
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
        >
          <div className="absolute top-10 left-1/4 w-[500px] h-[500px] rounded-full bg-brand-300/10 blur-[120px]" />
          <div className="absolute bottom-10 right-1/4 w-[400px] h-[400px] rounded-full bg-brand-200/15 blur-[100px]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full bg-brand-100/10 blur-[140px]" />
        </div>
      </DesktopOnly>

      {/* Preflight-themed decorative graphics */}
      <DesktopOnly>
        <div
          className="absolute inset-0 pointer-events-none overflow-hidden"
          aria-hidden="true"
        >
          {/* ── Left runway centerline dashes ── */}
          <div className="absolute top-[10%] left-[6%] flex flex-col gap-4 opacity-[0.12]">
            {/* skipcq: JS-0437 — static decorative elements that never reorder */}
            {[...Array(12)].map((_, i) => (
              <div
                key={`l${i}`}
                className="w-1.5 h-8 rounded-full bg-brand-900"
              />
            ))}
          </div>

          {/* ── Right runway centerline dashes ── */}
          <div className="absolute top-[8%] right-[7%] flex flex-col gap-4 opacity-[0.10]">
            {/* skipcq: JS-0437 — static decorative elements that never reorder */}
            {[...Array(10)].map((_, i) => (
              <div
                key={`r${i}`}
                className="w-1.5 h-8 rounded-full bg-brand-700"
              />
            ))}
          </div>

          {/* ── Runway threshold markings (left) ── */}
          <div className="absolute bottom-[18%] left-[4%] flex gap-2 opacity-[0.08]">
            {/* skipcq: JS-0437 — static decorative elements that never reorder */}
            {[...Array(4)].map((_, i) => (
              <div
                key={`tl${i}`}
                className="w-2 h-14 rounded-sm bg-brand-800"
              />
            ))}
          </div>

          {/* ── Runway threshold markings (right) ── */}
          <div className="absolute bottom-[25%] right-[5%] flex gap-2 opacity-[0.07]">
            {/* skipcq: JS-0437 — static decorative elements that never reorder */}
            {[...Array(3)].map((_, i) => (
              <div
                key={`tr${i}`}
                className="w-2 h-14 rounded-sm bg-brand-700"
              />
            ))}
          </div>

          {/* ── Compass rose (top-right) ── */}
          <svg
            className="absolute top-[6%] right-[12%] w-40 h-40 opacity-[0.07]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <circle
              cx="100"
              cy="100"
              r="80"
              stroke="#162d60"
              strokeWidth="1.5"
            />
            <circle
              cx="100"
              cy="100"
              r="60"
              stroke="#3b6fb5"
              strokeWidth="0.8"
              strokeDasharray="4 6"
            />
            {/* Cardinal lines */}
            <line
              x1="100"
              y1="10"
              x2="100"
              y2="190"
              stroke="#162d60"
              strokeWidth="1"
            />
            <line
              x1="10"
              y1="100"
              x2="190"
              y2="100"
              stroke="#162d60"
              strokeWidth="1"
            />
            {/* Ordinal lines */}
            <line
              x1="37"
              y1="37"
              x2="163"
              y2="163"
              stroke="#3b6fb5"
              strokeWidth="0.6"
            />
            <line
              x1="163"
              y1="37"
              x2="37"
              y2="163"
              stroke="#3b6fb5"
              strokeWidth="0.6"
            />
            {/* N arrow */}
            <polygon points="100,15 95,30 105,30" fill="#162d60" />
          </svg>

          {/* ── Altimeter / gauge arc (bottom-left) ── */}
          <svg
            className="absolute bottom-[8%] left-[8%] w-44 h-44 opacity-[0.08]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <path
              d="M 40 160 A 80 80 0 1 1 160 160"
              stroke="#162d60"
              strokeWidth="2"
              fill="none"
            />
            <path
              d="M 40 160 A 80 80 0 1 1 160 160"
              stroke="#5395ce"
              strokeWidth="2"
              strokeDasharray="8 6"
              fill="none"
            />
            {/* Tick marks */}
            {[0, 30, 60, 90, 120, 150, 180].map((deg) => {
              const rad = ((deg + 180) * Math.PI) / 180;
              const x1 = 100 + 72 * Math.cos(rad);
              const y1 = 100 + 72 * Math.sin(rad);
              const x2 = 100 + 80 * Math.cos(rad);
              const y2 = 100 + 80 * Math.sin(rad);
              return (
                <line
                  key={deg}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#162d60"
                  strokeWidth="2"
                />
              );
            })}
            {/* Needle */}
            <line
              x1="100"
              y1="100"
              x2="60"
              y2="60"
              stroke="#3b6fb5"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <circle cx="100" cy="100" r="4" fill="#162d60" />
          </svg>

          {/* ── Checklist checkmarks (left side) ── */}
          <svg
            className="absolute top-[35%] left-[3%] w-28 h-48 opacity-[0.09]"
            viewBox="0 0 100 200"
            fill="none"
          >
            {[0, 1, 2, 3, 4].map((i) => (
              <g key={`chk${i}`} transform={`translate(0, ${i * 40})`}>
                <rect
                  x="8"
                  y="4"
                  width="16"
                  height="16"
                  rx="3"
                  stroke="#3b6fb5"
                  strokeWidth="1.5"
                  fill="none"
                />
                <path
                  d="M12 12 L15 15 L22 7"
                  stroke="#162d60"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
                <line
                  x1="34"
                  y1="12"
                  x2="90"
                  y2="12"
                  stroke="#5395ce"
                  strokeWidth="1"
                  strokeDasharray="3 2"
                />
              </g>
            ))}
          </svg>

          {/* ── Dashed flight path arcs ── */}
          <svg
            className="absolute top-[12%] right-[22%] w-72 h-72 opacity-[0.06]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <path
              d="M20 180 Q 100 20, 180 100"
              stroke="#162d60"
              strokeWidth="2"
              strokeDasharray="8 10"
            />
            {/* Tiny plane at end of arc */}
            <polygon
              points="178,98 185,95 185,101 178,98"
              fill="#162d60"
              transform="rotate(-20, 180, 100)"
            />
          </svg>
          <svg
            className="absolute bottom-[12%] left-[18%] w-56 h-56 opacity-[0.06]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <path
              d="M180 180 Q 60 80, 20 20"
              stroke="#5395ce"
              strokeWidth="2"
              strokeDasharray="8 10"
            />
            <polygon
              points="22,22 15,19 15,25 22,22"
              fill="#5395ce"
              transform="rotate(45, 20, 20)"
            />
          </svg>

          {/* ── Attitude indicator horizon line (top-left) ── */}
          <svg
            className="absolute top-[5%] left-[18%] w-32 h-32 opacity-[0.06]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <circle
              cx="100"
              cy="100"
              r="85"
              stroke="#162d60"
              strokeWidth="1.5"
            />
            <line
              x1="20"
              y1="100"
              x2="180"
              y2="100"
              stroke="#3b6fb5"
              strokeWidth="1.5"
            />
            {/* Wings indicator */}
            <line
              x1="60"
              y1="100"
              x2="80"
              y2="100"
              stroke="#162d60"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <line
              x1="120"
              y1="100"
              x2="140"
              y2="100"
              stroke="#162d60"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <circle cx="100" cy="100" r="3" fill="#162d60" />
            {/* Pitch lines */}
            <line
              x1="75"
              y1="80"
              x2="125"
              y2="80"
              stroke="#5395ce"
              strokeWidth="0.8"
            />
            <line
              x1="80"
              y1="120"
              x2="120"
              y2="120"
              stroke="#5395ce"
              strokeWidth="0.8"
            />
          </svg>

          {/* ── Small scattered crosshair markers ── */}
          {[
            { top: "45%", right: "6%", size: "w-6 h-6" },
            { top: "70%", right: "15%", size: "w-5 h-5" },
            { top: "25%", left: "22%", size: "w-5 h-5" },
            { top: "65%", left: "6%", size: "w-4 h-4" },
            // skipcq: JS-0437 — static decorative elements that never reorder
          ].map((pos, i) => (
            <svg
              key={`xhair${i}`}
              className={`absolute ${pos.size} opacity-[0.10]`}
              style={{ top: pos.top, right: pos.right, left: pos.left }}
              viewBox="0 0 20 20"
              fill="none"
            >
              <circle cx="10" cy="10" r="6" stroke="#3b6fb5" strokeWidth="1" />
              <line
                x1="10"
                y1="2"
                x2="10"
                y2="18"
                stroke="#3b6fb5"
                strokeWidth="0.8"
              />
              <line
                x1="2"
                y1="10"
                x2="18"
                y2="10"
                stroke="#3b6fb5"
                strokeWidth="0.8"
              />
            </svg>
          ))}
        </div>
      </DesktopOnly>

      <div className="relative mx-auto max-w-5xl px-6 pt-28 pb-20 md:pt-36 md:pb-28 text-center min-w-0">
        <div className="flex flex-col items-center mb-10">
          <MarketingLogo className="h-44 w-auto md:h-56" />
          <p className="mt-3 text-sm font-medium tracking-widest text-slate-400 uppercase">
            Built to sail. Cleared for press.
          </p>
        </div>

        {betaMode ? (
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50/95 px-4 py-1.5 text-xs md:text-sm font-medium text-amber-800 mb-6 shadow-sm">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse shrink-0" />
            Beta &mdash; Limited Access
          </div>
        ) : (
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/95 px-4 py-1.5 text-xs md:text-sm font-medium text-brand-700 mb-6 shadow-sm max-w-full flex-wrap justify-center">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-brand-500 animate-pulse shrink-0" />
            250+ preflight checks &middot; PDF/X-4 &middot; PDF/A &middot; ISO
            15930 &middot; GWG 2022
          </div>
        )}

        <h1 className="text-4xl font-bold tracking-tight text-slate-900 md:text-6xl mb-4 leading-tight">
          Catch what&rsquo;s off{" "}
          <span className="bg-gradient-to-r from-brand-800 via-brand-600 to-brand-400 bg-clip-text text-transparent">
            before it sets sail.
          </span>
        </h1>

        <p className="mx-auto max-w-xl text-base text-slate-400 md:text-lg mb-8 tracking-wide font-medium italic">
          Your pre-departure checklist for every PDF.
        </p>

        <p className="mx-auto max-w-2xl text-lg text-slate-500 md:text-xl mb-10 leading-relaxed">
          Detection-only preflight engine. Inspect color spaces, fonts, images,
          transparency &amp; page geometry — without ever touching a single
          byte.
        </p>

        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          {betaMode ? (
            <button
              type="button"
              onClick={() => setWaitlistOpen(true)}
              className="rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
            >
              Join the Waitlist
            </button>
          ) : (
            <a
              href={`${process.env.NEXT_PUBLIC_APP_URL ?? "https://app.nevergrounded.io"}/auth/login?plan=free`}
              className="rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
            >
              Set Sail
            </a>
          )}
          <a
            href="/docs"
            className="rounded-xl border-2 border-slate-200 px-8 py-3.5 text-base font-medium text-slate-600 transition-all hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50"
          >
            View API Docs
          </a>
        </div>

        {/* Terminal preview */}
        <div className="mx-auto mt-16 max-w-2xl rounded-xl border border-slate-200 bg-brand-950 p-1 shadow-2xl shadow-brand-900/10">
          <div className="flex items-center gap-1.5 px-4 py-2.5">
            <span className="h-3 w-3 rounded-full bg-red-500/60" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/60" />
            <span className="h-3 w-3 rounded-full bg-green-500/60" />
          </div>
          <pre className="overflow-x-auto px-6 pb-6 text-left text-sm leading-relaxed text-slate-400">
            <code>{`$ curl -X POST https://api.nevergrounded.io/api/v1/launch \\
    -H "Authorization: Bearer grd_..." \\
    -F file=@brochure.pdf \\
    -F voyage_plan=gwg-sheetfed

{
  "id": "f47ac10b-...",
  "status": "underway",
  "voyage_plan": "gwg-sheetfed",
  "inspections": 250
}`}</code>
          </pre>
        </div>
      </div>

      <WaitlistModal
        open={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
      />
    </section>
  );
}
