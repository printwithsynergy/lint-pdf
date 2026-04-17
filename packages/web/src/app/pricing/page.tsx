"use client";

import { useState } from "react";
import { useBeta } from "@/components/BetaContext";
import { WaitlistModal } from "@/components/WaitlistModal";
import {
  pricingTiers,
  comparisonFeatures,
  pricingFaq,
  AI_CREDIT_PACKAGES,
  FILE_PACK_OPTIONS,
} from "@/lib/brand";

export default function PricingPage() {
  const { betaMode } = useBeta();
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const tierKeys = [
    "free",
    "viewer",
    "starter",
    "growth",
    "scale",
    "enterprise",
  ] as const;

  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

  return (
    <main>
      {/* Hero */}
      <section className="bg-brand-50/50 pt-20 pb-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h1 className="text-4xl font-bold text-slate-900 md:text-5xl mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto">
            Start free with 50 files per month. Scale as your preflight volume
            grows. Every plan includes 500+ checks — the only difference is
            volume and features.
          </p>
        </div>
      </section>

      {/* Tier Cards */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-6">
          {/* Monthly / Yearly toggle */}
          <div className="mb-10 flex items-center justify-center gap-3">
            <div className="inline-flex rounded-full border border-slate-200 bg-white p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setBilling("monthly")}
                aria-pressed={billing === "monthly"}
                className={`rounded-full px-5 py-1.5 text-sm font-medium transition-colors ${
                  billing === "monthly"
                    ? "bg-brand-900 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => setBilling("yearly")}
                aria-pressed={billing === "yearly"}
                className={`rounded-full px-5 py-1.5 text-sm font-medium transition-colors ${
                  billing === "yearly"
                    ? "bg-brand-900 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Yearly
              </button>
            </div>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
              Save 20%
            </span>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {pricingTiers.map((plan) => {
              const showYearly =
                billing === "yearly" && plan.yearlyPrice !== undefined;
              const displayPrice = showYearly
                ? (plan.yearlyPrice as string)
                : plan.price;
              const displayPeriod = showYearly
                ? plan.yearlyPeriod
                : plan.period;
              const lookupKey = showYearly
                ? plan.stripeYearlyLookupKey
                : plan.stripeMonthlyLookupKey;
              const href = lookupKey
                ? `${plan.href}${plan.href.includes("?") ? "&" : "?"}price=${lookupKey}`
                : plan.href;

              return (
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
                      {displayPrice}
                    </span>
                    {displayPeriod && (
                      <span className="text-sm text-slate-400 ml-1">
                        {displayPeriod}
                      </span>
                    )}
                  </div>
                  {showYearly && plan.yearlyTotal && (
                    <p className="text-xs text-slate-400 mb-1">
                      {plan.yearlyTotal} · {plan.yearlySavings}
                    </p>
                  )}
                  <p className="text-xs font-medium text-brand-600 mb-1">
                    {plan.filesPerMonth}
                  </p>
                  <p className="text-sm text-slate-500 mb-6">
                    {plan.description}
                  </p>

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
                      href={href}
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
              );
            })}
          </div>
        </div>
      </section>

      {/* Overage Rates */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Per-file overage billing
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto mb-6">
            Paid plans can opt into billable overages at{" "}
            <span className="font-semibold text-slate-700">$0.10 per file</span>{" "}
            beyond the included monthly limit. Set a spending cap to control
            maximum monthly overage spend. Free plan submissions are blocked at
            the limit.
          </p>
        </div>
      </section>

      {/* AI Credits + File Packs (metered resources) */}
      <section className="py-16">
        <div className="mx-auto max-w-5xl px-6">
          <div className="text-center mb-10">
            <div className="flex items-center justify-center gap-3 mb-4">
              <h2 className="text-2xl font-bold text-slate-900">
                Metered Resources
              </h2>
              <span className="rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white">
                Invite-Only Alpha
              </span>
            </div>
            <p className="text-slate-500 max-w-2xl mx-auto">
              Core preflight checks (500+) stay unlimited on every paid plan.
              AI inspections and file submissions are metered separately — each
              plan grants a monthly allotment that resets every billing cycle,
              and you can buy top-up packs at any time that roll over for 12
              months.
            </p>
          </div>

          {/* Plan-Included Monthly Allotments */}
          <div className="mb-10 rounded-2xl border border-slate-200 bg-white p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-3">
              Monthly allotments included with your plan
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              Every paid plan grants a monthly bucket of AI credits plus a
              monthly file quota that resets each billing cycle. Unused monthly
              allotments don&rsquo;t roll over — purchased packs (below) do.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-2 pr-4">Plan</th>
                    <th className="py-2 pr-4 text-right">AI credits / mo</th>
                    <th className="py-2 pr-4 text-right">Files / mo</th>
                  </tr>
                </thead>
                <tbody className="text-slate-700">
                  <tr className="border-t border-slate-100"><td className="py-2 pr-4">Free</td><td className="py-2 pr-4 text-right font-mono">0</td><td className="py-2 pr-4 text-right font-mono">50</td></tr>
                  <tr className="border-t border-slate-100"><td className="py-2 pr-4">Viewer</td><td className="py-2 pr-4 text-right font-mono">0</td><td className="py-2 pr-4 text-right font-mono">50</td></tr>
                  <tr className="border-t border-slate-100"><td className="py-2 pr-4">Starter</td><td className="py-2 pr-4 text-right font-mono">100</td><td className="py-2 pr-4 text-right font-mono">500</td></tr>
                  <tr className="border-t border-slate-100"><td className="py-2 pr-4">Growth</td><td className="py-2 pr-4 text-right font-mono">500</td><td className="py-2 pr-4 text-right font-mono">2,500</td></tr>
                  <tr className="border-t border-slate-100"><td className="py-2 pr-4">Scale</td><td className="py-2 pr-4 text-right font-mono">2,000</td><td className="py-2 pr-4 text-right font-mono">10,000</td></tr>
                  <tr className="border-t border-slate-100"><td className="py-2 pr-4">Enterprise</td><td className="py-2 pr-4 text-right font-mono">10,000</td><td className="py-2 pr-4 text-right font-mono">100,000</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <h3 className="text-lg font-semibold text-slate-900 mb-3">
            Top-up AI credit packs
          </h3>
          <p className="text-sm text-slate-500 mb-4">
            Running low mid-month? Buy a fixed pack through Stripe Checkout.
            Purchased packs roll over for 12 months.
          </p>

          {/* Credit Package Cards */}
          <div className="grid gap-6 md:grid-cols-3 mb-10">
            {AI_CREDIT_PACKAGES.map((pkg) => (
              <div
                key={pkg.name}
                className={`relative rounded-2xl border-2 p-6 flex flex-col transition-all hover:-translate-y-1 ${
                  pkg.highlighted
                    ? "border-brand-500 bg-white ring-2 ring-brand-200/50 shadow-xl shadow-brand-100"
                    : "border-slate-200 bg-white shadow-sm hover:shadow-md hover:border-brand-200"
                }`}
              >
                {pkg.highlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white shadow-md whitespace-nowrap">
                    Best Value
                  </span>
                )}
                <h3 className="text-xl font-semibold text-slate-900">
                  {pkg.name}
                </h3>
                <div className="mt-3 mb-1">
                  <span className="text-3xl font-bold text-slate-900">
                    ${pkg.price}
                  </span>
                </div>
                <p className="text-xs font-medium text-brand-600 mb-1">
                  {pkg.credits.toLocaleString()} credits
                </p>
                <p className="text-sm text-slate-500 mb-4">
                  {pkg.perCredit} per credit
                </p>
                <p className="text-xs font-medium text-emerald-600">
                  {pkg.savings}
                </p>
              </div>
            ))}
          </div>

          {/* File pack tiles — run parallel to credit packs. Same
              pattern, different SKU. Prices pulled from brand.ts. */}
          <h3 className="text-lg font-semibold text-slate-900 mb-3">
            Top-up file packs
          </h3>
          <p className="text-sm text-slate-500 mb-4">
            Each PDF submission consumes one file from your monthly allotment.
            Once the monthly pool is empty, buy a pack or enable per-file
            overage billing. Packs roll over for 12 months.
          </p>
          <div className="grid gap-6 md:grid-cols-3 mb-10">
            {FILE_PACK_OPTIONS.map((pkg) => (
              <div
                key={`files-${pkg.name}`}
                className={`relative rounded-2xl border-2 p-6 flex flex-col transition-all hover:-translate-y-1 ${
                  pkg.highlighted
                    ? "border-brand-500 bg-white ring-2 ring-brand-200/50 shadow-xl shadow-brand-100"
                    : "border-slate-200 bg-white shadow-sm hover:shadow-md hover:border-brand-200"
                }`}
              >
                {pkg.highlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white shadow-md whitespace-nowrap">
                    Best Value
                  </span>
                )}
                <h3 className="text-xl font-semibold text-slate-900">
                  {pkg.name}
                </h3>
                <div className="mt-3 mb-1">
                  <span className="text-3xl font-bold text-slate-900">
                    ${pkg.price}
                  </span>
                </div>
                <p className="text-xs font-medium text-brand-600 mb-1">
                  {pkg.files.toLocaleString()} files
                </p>
                <p className="text-sm text-slate-500 mb-4">
                  {pkg.perFile} per file
                </p>
                <p className="text-xs font-medium text-emerald-600">
                  {pkg.savings}
                </p>
              </div>
            ))}
          </div>

          {/* Credit Cost Breakdown */}
          <div className="grid gap-6 md:grid-cols-2 mb-10">
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-block h-3 w-3 rounded-full bg-emerald-400" />
                <h3 className="font-semibold text-slate-900">
                  Text Tier — 1 credit
                </h3>
              </div>
              <p className="text-sm text-slate-500 mb-3">
                Sub-second latency. Text and structure analysis.
              </p>
              <ul className="space-y-1 text-xs text-slate-500">
                <li>Barcode decode, QR validation, barcode dimensions</li>
                <li>Spell check, language detection, duplicate detection</li>
                <li>Brand palette check, WCAG contrast, version diff</li>
                <li>FDA nutrition, EU FIR 1169, GHS CLP, pharma font</li>
                <li>Dieline by name, submission quality SPC</li>
              </ul>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-block h-3 w-3 rounded-full bg-violet-400" />
                <h3 className="font-semibold text-slate-900">
                  Vision Tier — 2 credits
                </h3>
              </div>
              <p className="text-sm text-slate-500 mb-3">
                1-5 second latency. Vision and ML models.
              </p>
              <ul className="space-y-1 text-xs text-slate-500">
                <li>Image quality, NSFW detection, image similarity</li>
                <li>File classification, auto ruleset</li>
                <li>Logo detection, safe zone violations</li>
                <li>NL ruleset, NL report interpret</li>
                <li>Multi-language translation, text as outlines</li>
                <li>Regulatory symbols, processing steps fallback</li>
              </ul>
            </div>
          </div>

          {/* Estimator */}
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-6">
            <h3 className="font-semibold text-slate-900 mb-4">
              Credit Estimator
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b-2 border-slate-200">
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">
                      Preset
                    </th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">
                      Est. Credits/File
                    </th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">
                      100 Files
                    </th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">
                      1,000 Files
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    {
                      preset: "FDA Food Label",
                      credits: "8-14",
                      est100: "~$60-$84",
                      est1000: "~$320-$560",
                    },
                    {
                      preset: "EU Food Label",
                      credits: "8-14",
                      est100: "~$60-$84",
                      est1000: "~$320-$560",
                    },
                    {
                      preset: "GHS Chemical",
                      credits: "8-12",
                      est100: "~$48-$72",
                      est1000: "~$320-$480",
                    },
                    {
                      preset: "Packaging QC",
                      credits: "12-20",
                      est100: "~$72-$120",
                      est1000: "~$480-$800",
                    },
                    {
                      preset: "Brand Compliance",
                      credits: "8-14",
                      est100: "~$48-$84",
                      est1000: "~$320-$560",
                    },
                    {
                      preset: "Full AI Scan",
                      credits: "45-55",
                      est100: "~$270-$330",
                      est1000: "~$1,800-$2,200",
                    },
                  ].map((row) => (
                    <tr key={row.preset} className="border-b border-slate-100">
                      <td className="py-2 px-3 font-medium text-slate-800">
                        {row.preset}
                      </td>
                      <td className="py-2 px-3 text-slate-600">
                        {row.credits}
                      </td>
                      <td className="py-2 px-3 text-slate-600">{row.est100}</td>
                      <td className="py-2 px-3 text-slate-600">
                        {row.est1000}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-xs text-slate-400">
              Estimates use Scale package pricing ($0.06/credit). Actual credit
              consumption depends on which inspections are enabled and file
              complexity. Credits never expire.
            </p>
          </div>
        </div>
      </section>

      {/* Feature Comparison Matrix */}
      <section className="py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-8 text-center">
            Feature comparison
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left py-3 px-3 text-slate-500 font-medium">
                    Feature
                  </th>
                  {pricingTiers.map((tier) => (
                    <th
                      key={tier.name}
                      className={`text-center py-3 px-3 font-semibold ${tier.highlighted ? "text-brand-700" : "text-slate-900"}`}
                    >
                      {tier.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonFeatures.map((feature) => (
                  <tr key={feature.name} className="border-b border-slate-100">
                    <td className="py-3 px-3 text-slate-600 font-medium">
                      {feature.name}
                    </td>
                    {tierKeys.map((key) => {
                      const val = feature[key];
                      return (
                        <td key={key} className="text-center py-3 px-3">
                          {typeof val === "boolean" ? (
                            val ? (
                              <svg
                                className="h-5 w-5 mx-auto text-brand-500"
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
                            ) : (
                              <span className="text-slate-300">&mdash;</span>
                            )
                          ) : (
                            <span className="text-slate-600">{val}</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-5 text-xs text-slate-500 leading-relaxed">
            <p className="font-semibold text-slate-700 mb-2">
              How submissions are counted
            </p>
            <ul className="space-y-1.5">
              <li>
                <span className="font-medium text-slate-600">Engine mode</span>{" "}
                submissions (the full 500+ check pipeline) count as{" "}
                <span className="font-medium text-slate-700">one file</span>{" "}
                against your monthly limit.
              </li>
              <li>
                <span className="font-medium text-slate-600">
                  External imports
                </span>{" "}
                (PitStop, callas, Acrobat, or LintPDF-native reports) also count
                as <span className="font-medium text-slate-700">one file</span>.
                You are not billed for checks you ran upstream — only for
                storage, viewer rendering, and share-link infrastructure.
              </li>
              <li>
                <span className="font-medium text-slate-600">
                  Viewer-only (minimal) submissions
                </span>{" "}
                count as{" "}
                <span className="font-medium text-slate-700">one file</span>.
                Page geometry is computed on ingest; deeper analyzers only run
                if you invoke on-demand capability fill-in.
              </li>
              <li>
                <span className="font-medium text-slate-600">Viewer tier</span>{" "}
                files count one-for-one against your monthly limit. Engine
                preflight, capability fill-in, annotations, and report
                downloads are not available on this tier — bring your own
                preflight report (PitStop, callas, Acrobat, LintPDF JSON) or
                upgrade to Starter.
              </li>
              <li>
                <span className="font-medium text-slate-600">
                  Capability fill-in
                </span>{" "}
                invocations (separations, TAC, fonts, images) are counted{" "}
                <span className="font-medium text-slate-700">
                  one per analyzer run
                </span>{" "}
                in addition to the original submission. A job with all four
                fill-ins runs as 1 submission + 4 capability runs = 5 billable
                units.
              </li>
              <li>
                <span className="font-medium text-slate-600">
                  AI inspections
                </span>{" "}
                are metered separately as AI credits (see above) and never draw
                from your file-per-month allocation.
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-8 text-center">
            Frequently asked questions
          </h2>
          <div className="space-y-3">
            {pricingFaq.map((item, i) => (
              <div
                key={item.question}
                className="rounded-xl border border-slate-200 bg-white overflow-hidden"
              >
                <button
                  type="button"
                  className="w-full flex items-center justify-between px-6 py-4 text-left text-sm font-semibold text-slate-900 hover:bg-brand-50/50 transition-colors"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                >
                  {item.question}
                  <svg
                    className={`h-4 w-4 flex-shrink-0 text-slate-400 transition-transform ${openFaq === i ? "rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
                {openFaq === i && (
                  <div className="px-6 pb-4 text-sm text-slate-500 leading-relaxed">
                    {item.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <WaitlistModal
        open={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
      />
    </main>
  );
}
