"use client";

import { useState } from "react";
import { useBeta } from "./BetaContext";
import { WaitlistModal } from "./WaitlistModal";
import { pricingTiers } from "@/lib/brand";

export function PricingSection() {
  const { betaMode } = useBeta();
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    // skipcq: JS-0415
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
          {pricingTiers.map((plan) => (
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
                  Join Waitlist
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
      </div>

      <WaitlistModal
        open={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
      />
    </section>
  );
}
