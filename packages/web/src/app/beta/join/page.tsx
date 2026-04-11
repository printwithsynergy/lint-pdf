"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { Logo } from "@/components/Logo";

const API_BASE = process.env.NEXT_PUBLIC_APP_URL ?? "https://app.lintpdf.com";

type FormState = "idle" | "submitting" | "success" | "duplicate" | "error";

export default function BetaJoinPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [useCase, setUseCase] = useState("");
  const [state, setState] = useState<FormState>("idle");

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setState("submitting");

      try {
        const resp = await fetch(`${API_BASE}/api/waitlist/join`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim(),
            name: name.trim() || null,
            company: company.trim() || null,
            useCase: useCase.trim() || null,
          }),
        });

        if (!resp.ok) {
          setState("error");
          return;
        }

        const data = await resp.json();
        // New endpoint returns 200 for existing entries, 201 for new
        if (resp.status === 200 && !data.id) {
          setState("duplicate");
          return;
        }
        setState("success");
      } catch {
        setState("error");
      }
    },
    [email, name, company, useCase],
  );

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <Logo className="h-12 w-12" />
        </div>

        {state === "success" ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-lg text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-100">
              <svg
                className="h-7 w-7 text-brand-700"
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
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mb-2">
              You&rsquo;re on the list!
            </h1>
            <p className="text-slate-500 mb-1">
              We&rsquo;ll email you when your spot is ready.
            </p>
            <Link
              href="/"
              className="inline-block rounded-xl bg-brand-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-800"
            >
              Back to Home
            </Link>
          </div>
        ) : state === "duplicate" ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-lg text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-100">
              <svg
                className="h-7 w-7 text-brand-700"
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
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mb-2">
              Already on the list
            </h1>
            <p className="text-slate-500 mb-6">
              You&rsquo;re already on the waitlist — hang tight, we&rsquo;ll be
              in touch!
            </p>
            <Link
              href="/"
              className="inline-block rounded-xl bg-brand-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-800"
            >
              Back to Home
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
            <h1 className="text-2xl font-bold text-slate-900 mb-2 text-center">
              LintPDF is in beta
            </h1>
            <p className="text-sm text-slate-500 mb-8 text-center">
              We&rsquo;re letting people in gradually. Join the waitlist to get
              notified when your account is ready.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="join-email"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  id="join-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label
                  htmlFor="join-name"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Name
                </label>
                <input
                  id="join-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="Jane Smith"
                />
              </div>
              <div>
                <label
                  htmlFor="join-company"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Company
                </label>
                <input
                  id="join-company"
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="Acme Corp"
                />
              </div>
              <div>
                <label
                  htmlFor="join-usecase"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  How will you use LintPDF?
                </label>
                <textarea
                  id="join-usecase"
                  value={useCase}
                  onChange={(e) => setUseCase(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none resize-none"
                  placeholder="Automated preflight for our print workflow..."
                />
              </div>

              {state === "error" && (
                <p className="text-sm text-red-600">
                  Something went wrong. Please try again.
                </p>
              )}

              <button
                type="submit"
                disabled={state === "submitting"}
                className="w-full rounded-xl bg-brand-900 py-3 text-sm font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {state === "submitting" ? "Joining..." : "Join the Waitlist"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
