"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { DesktopOnly } from "./DesktopOnly";
import { MarketingLogo } from "./Logo";
import { ParticleField } from "./ParticleField";
import { useBeta } from "./BetaContext";
import { WaitlistModal } from "./WaitlistModal";

const LEFT_CODE_LINES = Array.from({ length: 12 }, (_, i) => ({
  id: `left-line-${i + 1}`,
  width: 20 + ((i * 17) % 40),
}));

const RIGHT_CODE_LINES = Array.from({ length: 10 }, (_, i) => ({
  id: `right-line-${i + 1}`,
  width: 16 + ((i * 13) % 36),
}));

const TAGLINES: { lines: string[] }[] = [
  { lines: ["Preflights You", "Won't Hate."] },
  { lines: ["Every Byte. Every Page.", "Zero Mercy."] },
  { lines: ["Catch It Before", "Press Does."] },
];

function RotatingTagline() {
  const [index, setIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  const advance = useCallback(() => {
    setVisible(false);
    const t = setTimeout(() => {
      setIndex((i) => (i + 1) % TAGLINES.length);
      setVisible(true);
    }, 600);
    return t;
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      advance();
    }, 4000);
    return () => clearInterval(interval);
  }, [advance]);

  const tagline = TAGLINES[index];

  return (
    <div className="mb-4">
      <h1
        className={`text-4xl font-bold tracking-tight text-slate-900 md:text-6xl leading-tight transition-all duration-500 ${
          visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
        }`}
      >
        {tagline.lines[0]}
        <br />
        <span className="bg-gradient-to-r from-brand-800 via-brand-600 to-brand-400 bg-clip-text text-transparent">
          {tagline.lines[1]}
        </span>
      </h1>
    </div>
  );
}

export function HeroSection() {
  const { betaMode } = useBeta();
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
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

      {/* Lint-themed decorative graphics */}
      <DesktopOnly>
        <div
          className="absolute inset-0 pointer-events-none overflow-hidden"
          aria-hidden="true"
        >
          {/* ── Left code line indicators ── */}
          <div className="absolute top-[10%] left-[6%] flex flex-col gap-3 opacity-[0.12]">
            {LEFT_CODE_LINES.map((line) => (
              <div key={line.id} className="flex items-center gap-2">
                <div className="w-4 h-0.5 rounded-full bg-brand-900" />
                <div
                  className="h-0.5 rounded-full bg-brand-700"
                  style={{ width: `${line.width}px` }}
                />
              </div>
            ))}
          </div>

          {/* ── Right code line indicators ── */}
          <div className="absolute top-[8%] right-[7%] flex flex-col gap-3 opacity-[0.10]">
            {RIGHT_CODE_LINES.map((line) => (
              <div key={line.id} className="flex items-center gap-2">
                <div
                  className="h-0.5 rounded-full bg-brand-700"
                  style={{ width: `${line.width}px` }}
                />
              </div>
            ))}
          </div>

          {/* ── Bracket pair (left) ── */}
          <svg
            className="absolute bottom-[18%] left-[4%] w-16 h-32 opacity-[0.08]"
            viewBox="0 0 60 120"
            fill="none"
          >
            <path
              d="M40 10 Q 20 10, 20 30 L 20 50 Q 20 60, 10 60 Q 20 60, 20 70 L 20 90 Q 20 110, 40 110"
              stroke="#1e3a8a"
              strokeWidth="2"
              fill="none"
            />
          </svg>

          {/* ── Bracket pair (right) ── */}
          <svg
            className="absolute bottom-[25%] right-[5%] w-16 h-32 opacity-[0.07]"
            viewBox="0 0 60 120"
            fill="none"
          >
            <path
              d="M20 10 Q 40 10, 40 30 L 40 50 Q 40 60, 50 60 Q 40 60, 40 70 L 40 90 Q 40 110, 20 110"
              stroke="#1d4ed8"
              strokeWidth="2"
              fill="none"
            />
          </svg>

          {/* ── Magnifying glass / scan icon (top-right) ── */}
          <svg
            className="absolute top-[6%] right-[12%] w-40 h-40 opacity-[0.07]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <circle cx="85" cy="85" r="55" stroke="#1e3a8a" strokeWidth="2" />
            <line
              x1="125"
              y1="125"
              x2="170"
              y2="170"
              stroke="#1e3a8a"
              strokeWidth="3"
              strokeLinecap="round"
            />
            {/* Scan lines inside */}
            <line
              x1="55"
              y1="70"
              x2="115"
              y2="70"
              stroke="#2563eb"
              strokeWidth="1"
              strokeDasharray="4 3"
            />
            <line
              x1="55"
              y1="85"
              x2="115"
              y2="85"
              stroke="#2563eb"
              strokeWidth="1"
              strokeDasharray="4 3"
            />
            <line
              x1="55"
              y1="100"
              x2="100"
              y2="100"
              stroke="#2563eb"
              strokeWidth="1"
              strokeDasharray="4 3"
            />
          </svg>

          {/* ── Terminal / console (bottom-left) ── */}
          <svg
            className="absolute bottom-[8%] left-[8%] w-44 h-36 opacity-[0.08]"
            viewBox="0 0 200 160"
            fill="none"
          >
            <rect
              x="10"
              y="10"
              width="180"
              height="140"
              rx="8"
              stroke="#1e3a8a"
              strokeWidth="2"
            />
            <line
              x1="10"
              y1="35"
              x2="190"
              y2="35"
              stroke="#1e3a8a"
              strokeWidth="1"
            />
            {/* Terminal prompt */}
            <path
              d="M30 55 L45 70 L30 85"
              stroke="#3b82f6"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            <line
              x1="55"
              y1="70"
              x2="100"
              y2="70"
              stroke="#2563eb"
              strokeWidth="1.5"
              strokeDasharray="4 3"
            />
            <line
              x1="55"
              y1="90"
              x2="120"
              y2="90"
              stroke="#1d4ed8"
              strokeWidth="1"
              strokeDasharray="3 4"
            />
            <line
              x1="55"
              y1="110"
              x2="90"
              y2="110"
              stroke="#1d4ed8"
              strokeWidth="1"
              strokeDasharray="3 4"
            />
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
                  stroke="#2563eb"
                  strokeWidth="1.5"
                  fill="none"
                />
                <path
                  d="M12 12 L15 15 L22 7"
                  stroke="#1e3a8a"
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
                  stroke="#3b82f6"
                  strokeWidth="1"
                  strokeDasharray="3 2"
                />
              </g>
            ))}
          </svg>

          {/* ── Dashed connection lines ── */}
          <svg
            className="absolute top-[12%] right-[22%] w-72 h-72 opacity-[0.06]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <path
              d="M20 180 Q 100 20, 180 100"
              stroke="#1e3a8a"
              strokeWidth="2"
              strokeDasharray="8 10"
            />
            <circle cx="180" cy="100" r="4" fill="#1e3a8a" />
          </svg>
          <svg
            className="absolute bottom-[12%] left-[18%] w-56 h-56 opacity-[0.06]"
            viewBox="0 0 200 200"
            fill="none"
          >
            <path
              d="M180 180 Q 60 80, 20 20"
              stroke="#3b82f6"
              strokeWidth="2"
              strokeDasharray="8 10"
            />
            <circle cx="20" cy="20" r="4" fill="#3b82f6" />
          </svg>

          {/* ── Code block indicator (top-left) ── */}
          <svg
            className="absolute top-[5%] left-[18%] w-32 h-32 opacity-[0.06]"
            viewBox="0 0 200 200"
            fill="none"
          >
            {/* Opening angle bracket < */}
            <path
              d="M100 40 L50 100 L100 160"
              stroke="#1e3a8a"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            {/* Forward slash / */}
            <line
              x1="115"
              y1="40"
              x2="135"
              y2="160"
              stroke="#2563eb"
              strokeWidth="2"
              strokeLinecap="round"
            />
            {/* Closing angle bracket > */}
            <path
              d="M150 40 L200 100 L150 160"
              stroke="#1e3a8a"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>

          {/* ── Small scattered dot markers ── */}
          {[
            { id: "tr", top: "45%", right: "6%", size: "w-6 h-6" },
            { id: "br", top: "70%", right: "15%", size: "w-5 h-5" },
            { id: "tl", top: "25%", left: "22%", size: "w-5 h-5" },
            { id: "bl", top: "65%", left: "6%", size: "w-4 h-4" },
          ].map((pos) => (
            <svg
              key={pos.id}
              className={`absolute ${pos.size} opacity-[0.10]`}
              style={{ top: pos.top, right: pos.right, left: pos.left }}
              viewBox="0 0 20 20"
              fill="none"
            >
              <circle cx="10" cy="10" r="3" fill="#2563eb" />
              <circle
                cx="10"
                cy="10"
                r="7"
                stroke="#2563eb"
                strokeWidth="0.8"
              />
            </svg>
          ))}
        </div>
      </DesktopOnly>

      <div className="relative mx-auto max-w-5xl px-6 pt-28 pb-20 md:pt-36 md:pb-28 text-center min-w-0">
        <div className="flex flex-col items-center mb-10">
          <MarketingLogo className="h-52 w-auto md:h-64" />
        </div>

        {betaMode ? (
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50/95 px-4 py-1.5 text-xs md:text-sm font-medium text-amber-800 mb-6 shadow-sm">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse shrink-0" />
            Beta &mdash; Limited Access
          </div>
        ) : (
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/95 px-4 py-1.5 text-xs md:text-sm font-medium text-brand-700 mb-6 shadow-sm max-w-full flex-wrap justify-center">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-brand-500 animate-pulse shrink-0" />
            500+ preflight checks &middot; PDF/X-1a &middot; PDF/X-3 &middot;
            PDF/X-4 &middot; PDF/A &middot; ISO 15930 &middot; GWG 2022
          </div>
        )}

        <RotatingTagline />

        <p className="mx-auto max-w-2xl text-lg text-slate-500 md:text-xl mb-10 leading-relaxed">
          Detection-only preflight engine. Inspect color spaces, fonts, images,
          transparency, page geometry, packaging geometry &amp; barcodes —
          without ever touching a single byte.
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
              href={`${process.env.NEXT_PUBLIC_APP_URL ?? "https://app.lintpdf.com"}/auth/login?plan=free`}
              className="rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
            >
              Get Started
            </a>
          )}
          <Link
            href="/docs"
            className="rounded-xl border-2 border-slate-200 px-8 py-3.5 text-base font-medium text-slate-600 transition-all hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50"
          >
            View API Docs
          </Link>
        </div>

        {/* Terminal preview */}
        <div className="mx-auto mt-16 max-w-2xl rounded-xl border border-slate-200 bg-brand-950 p-1 shadow-2xl shadow-brand-900/10">
          <div className="flex items-center gap-1.5 px-4 py-2.5">
            <span className="h-3 w-3 rounded-full bg-red-500/60" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/60" />
            <span className="h-3 w-3 rounded-full bg-green-500/60" />
          </div>
          <pre className="overflow-x-auto px-6 pb-6 text-left text-sm leading-relaxed text-slate-400">
            <code>{`$ curl -X POST https://api.lintpdf.com/api/v1/submit \\
    -H "Authorization: Bearer lpdf_..." \\
    -F file=@brochure.pdf \\
    -F ruleset=gwg-sheetfed

{
  "id": "f47ac10b-...",
  "status": "processing",
  "ruleset": "gwg-sheetfed",
  "checks": 500
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
