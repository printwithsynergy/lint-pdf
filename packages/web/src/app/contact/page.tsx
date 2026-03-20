"use client";

import { useState, useCallback } from "react";
import type { FormEvent } from "react";

type FormState = "idle" | "submitting" | "success" | "error";

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [state, setState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setState("submitting");
      setErrorMsg("");

      try {
        const resp = await fetch("/api/contact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: name.trim(),
            email: email.trim(),
            subject: subject.trim(),
            message: message.trim(),
            _hp_field: honeypot,
          }),
        });

        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setErrorMsg(
            (data as { error?: string }).error ??
              "Something went wrong. Please try again.",
          );
          setState("error");
          return;
        }

        setState("success");
      } catch {
        setErrorMsg("Network error. Please check your connection and try again.");
        setState("error");
      }
    },
    [name, email, subject, message, honeypot],
  );

  return (
    <main>
      <section className="bg-brand-50/50 pt-20 pb-16">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h1 className="text-4xl font-bold text-slate-900 md:text-5xl mb-4">
            Contact Us
          </h1>
          <p className="text-lg text-slate-500">
            Questions, feedback, or partnership inquiries — we&rsquo;d love to
            hear from you.
          </p>
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-xl px-6">
          {state === "success" ? (
            <div className="rounded-2xl border border-brand-200 bg-brand-50/50 p-8 text-center">
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
              <h2 className="text-xl font-bold text-slate-900 mb-2">
                Message sent!
              </h2>
              <p className="text-slate-500">
                We&rsquo;ll get back to you as soon as possible.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Honeypot — hidden from real users */}
              <div className="absolute -left-[9999px]" aria-hidden="true">
                <label htmlFor="ct-hp">
                  Leave empty
                  <input
                    id="ct-hp"
                    type="text"
                    tabIndex={-1}
                    autoComplete="off"
                    value={honeypot}
                    onChange={(e) => setHoneypot(e.target.value)}
                  />
                </label>
              </div>

              <div>
                <label
                  htmlFor="ct-name"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Name
                </label>
                <input
                  id="ct-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="Jane Smith"
                />
              </div>

              <div>
                <label
                  htmlFor="ct-email"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  id="ct-email"
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
                  htmlFor="ct-subject"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Subject
                </label>
                <input
                  id="ct-subject"
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="API integration question"
                />
              </div>

              <div>
                <label
                  htmlFor="ct-message"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Message <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="ct-message"
                  required
                  rows={5}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none resize-none"
                  placeholder="Tell us how we can help..."
                />
              </div>

              {state === "error" && (
                <p className="text-sm text-red-600">{errorMsg}</p>
              )}

              <button
                type="submit"
                disabled={state === "submitting"}
                className="w-full rounded-xl bg-brand-900 py-3 text-sm font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {state === "submitting" ? "Sending..." : "Send Message"}
              </button>

              <p className="text-xs text-slate-400 text-center">
                You can also reach us at{" "}
                <a
                  href="mailto:hello@thinkneverland.com"
                  className="text-brand-600 hover:text-brand-700"
                >
                  hello@thinkneverland.com
                </a>
              </p>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}
