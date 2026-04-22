"use client";

import { useState } from "react";
import { useBeta } from "./BetaContext";
import { WaitlistModal } from "./WaitlistModal";
import { pricingTiers } from "@/lib/brand";

export function PricingSection() {
  const { betaMode } = useBeta();
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <section id="pricing" className="bg-brand-50/50 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl mb-4">
            Simple, transparent pricing
          </h2>
          <p className="text-slate-500">
            {betaMode
              ? "Pricing shown for reference. Join the waitlist for early access."
              : "Start free. Scale as your preflight volume grows."}
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {pricingTiers
            .filter((plan) => plan.name !== "Viewer")
            .map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl border-2 p-6 flex flex-col transition-all hover:-translate-y-1 ${
                plan.highlighted
                  ? "border-brand-500 bg-white ring-2 ring-brand-200/50 shadow-xl shadow-brand-100"
                  : "border-slate-200 bg-white shadow-sm hover:shadow-md hover:border-brand-200"
              }`}
            >
              {plan.highlighted && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white shadow-md whitespace-nowrap">
                  Most Popular
                </span>
              )}
              <h3 className="text-xl font-semibold text-slate-900">
                {plan.name}
              </h3>
              <div className="mt-3 mb-1">
                <span className="text-3xl font-bold text-slate-900">
                  {plan.price}
                </span>
                {plan.period && (
                  <span className="text-sm text-slate-400 ml-1">
                    {plan.period}
                  </span>
                )}
              </div>
              <p className="text-xs font-medium text-brand-600 mb-1">
                {plan.filesPerMonth}
              </p>
              <p className="text-sm text-slate-500 mb-6">{plan.description}</p>

              <ul className="mb-8 flex-1 space-y-3 text-sm text-slate-600">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <svg
                      className="h-4 w-4 mt-0.5 flex-shrink-0 text-brand-500"
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
                    {feature}
                  </li>
                ))}
              </ul>

              {betaMode ? (
                <button
                  type="button"
                  onClick={() => setWaitlistOpen(true)}
                  className={`block w-full rounded-xl py-2.5 text-center text-sm font-semibold transition-all ${
                    plan.highlighted
                      ? "bg-brand-900 text-white hover:bg-brand-800 shadow-md shadow-brand-200"
                      : "bg-slate-100 text-slate-700 hover:bg-brand-50 hover:text-brand-700 border border-slate-200 hover:border-brand-200"
                  }`}
                >
                  Join the Waitlist
                </button>
              ) : (
                <a
                  href={plan.href}
                  className={`block rounded-xl py-2.5 text-center text-sm font-semibold transition-all ${
                    plan.highlighted
                      ? "bg-brand-900 text-white hover:bg-brand-800 shadow-md shadow-brand-200"
                      : "bg-slate-100 text-slate-700 hover:bg-brand-50 hover:text-brand-700 border border-slate-200 hover:border-brand-200"
                  }`}
                >
                  {plan.cta}
                </a>
              )}
            </div>
          ))}
        </div>

        {(() => {
          const viewerPlan = pricingTiers.find((p) => p.name === "Viewer");
          if (!viewerPlan) return null;

          const included: string[] = [];
          const caveats: string[] = [];
          for (const f of viewerPlan.features) {
            if (f.toLowerCase().startsWith("no ")) {
              caveats.push(f);
            } else if (f === viewerPlan.filesPerMonth) {
              continue;
            } else {
              included.push(f);
            }
          }

          return (
            <div className="mt-8 overflow-hidden rounded-2xl border-2 border-brand-200 shadow-sm hover:shadow-md transition-all">
              <div className="grid md:grid-cols-5">
                <div className="md:col-span-2 bg-brand-50/60 p-4 md:p-5 flex flex-col">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center rounded-full bg-brand-100 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-700">
                      Alternative workflow
                    </span>
                    <h3 className="text-lg font-bold text-slate-900">
                      {viewerPlan.name}
                    </h3>
                  </div>
                  <div className="mt-2 flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-slate-900 leading-none">
                      {viewerPlan.price}
                    </span>
                    {viewerPlan.period && (
                      <span className="text-xs text-slate-400">
                        {viewerPlan.period}
                      </span>
                    )}
                    <span className="text-xs font-medium text-brand-600">
                      · {viewerPlan.filesPerMonth}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-600 leading-snug">
                    {viewerPlan.description}
                  </p>
                  <div className="mt-3">
                    {betaMode ? (
                      <button
                        type="button"
                        onClick={() => setWaitlistOpen(true)}
                        className="block w-full rounded-lg bg-brand-900 py-2 text-center text-xs font-semibold text-white hover:bg-brand-800 shadow-sm shadow-brand-200 transition-all"
                      >
                        Join the Waitlist
                      </button>
                    ) : (
                      <a
                        href={viewerPlan.href}
                        className="block w-full rounded-lg bg-brand-900 py-2 text-center text-xs font-semibold text-white hover:bg-brand-800 shadow-sm shadow-brand-200 transition-all"
                      >
                        {viewerPlan.cta}
                      </a>
                    )}
                  </div>
                </div>

                <div className="md:col-span-3 bg-white p-4 md:p-5">
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
                    What&apos;s included
                  </h4>
                  <ul className="grid gap-x-5 gap-y-1.5 sm:grid-cols-2 text-xs text-slate-600">
                    {included.map((feature) => (
                      <li key={feature} className="flex items-start gap-1.5">
                        <svg
                          className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-brand-500"
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
                        {feature}
                      </li>
                    ))}
                  </ul>
                  {caveats.length > 0 && (
                    <p className="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400 leading-snug">
                      {caveats.join(". ")}. The same Viewer workflow is{" "}
                      <span className="font-medium text-slate-500">
                        included in every paid plan above
                      </span>{" "}
                      — pick this tier only if you don&apos;t need engine
                      preflight. Need more than 150 files / mo? Buy a top-up
                      file pack or enable per-file overage billing at $0.10 /
                      file (paid plans only; Free is blocked at the limit).
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })()}

        <p className="mt-8 text-center text-xs text-slate-500 max-w-3xl mx-auto leading-relaxed">
          Need more files than your plan includes? Every paid tier (including
          Viewer) can buy{" "}
          <span className="font-medium text-slate-700">top-up file packs</span>{" "}
          that roll over for 12 months, or opt into{" "}
          <span className="font-medium text-slate-700">
            per-file overage billing at $0.10 / file
          </span>{" "}
          with a configurable monthly cap. Free plan submissions are blocked at
          the limit. See{" "}
          <a href="/pricing" className="text-brand-700 hover:underline">
            full pricing
          </a>{" "}
          for AI credit packs and the metered-resource breakdown.
        </p>
      </div>

      <WaitlistModal
        open={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
      />
    </section>
  );
}
