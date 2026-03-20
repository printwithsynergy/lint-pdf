"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface WaitlistModalProps {
  open: boolean;
  onClose: () => void;
}

const API_BASE =
  process.env.NEXT_PUBLIC_APP_URL ?? "https://app.nevergrounded.io";

type FormState = "idle" | "submitting" | "success" | "duplicate" | "error";

export function WaitlistModal({ open, onClose }: WaitlistModalProps) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [useCase, setUseCase] = useState("");
  const [state, setState] = useState<FormState>("idle");
  const [position, setPosition] = useState<number | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    else if (!open && el.open) el.close();
  }, [open]);

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
        setPosition(data.position ?? null);
        setState("success");
      } catch {
        setState("error");
      }
    },
    [email, name, company, useCase],
  );

  const handleClose = useCallback(() => {
    setState("idle");
    setEmail("");
    setName("");
    setCompany("");
    setUseCase("");
    setPosition(null);
    onClose();
  }, [onClose]);

  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-[100] m-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white p-0 shadow-2xl backdrop:bg-black/50"
      onClose={handleClose}
    >
      <div className="p-6">
        {/* Close button */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600"
          aria-label="Close"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        {state === "success" ? (
          <div className="text-center py-4">
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
            <h3 className="text-xl font-bold text-slate-900 mb-2">
              You&rsquo;re on the list!
            </h3>
            <p className="text-slate-500 mb-1">
              We&rsquo;ll email you when your spot is ready.
            </p>
            {position !== null && (
              <p className="text-sm text-slate-400">Position: #{position}</p>
            )}
            <button
              type="button"
              onClick={handleClose}
              className="mt-6 rounded-xl bg-brand-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-800"
            >
              Done
            </button>
          </div>
        ) : state === "duplicate" ? (
          <div className="text-center py-4">
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
            <h3 className="text-xl font-bold text-slate-900 mb-2">
              Already on the list
            </h3>
            <p className="text-slate-500">
              You&rsquo;re already on the waitlist — hang tight, we&rsquo;ll be
              in touch!
            </p>
            <button
              type="button"
              onClick={handleClose}
              className="mt-6 rounded-xl bg-brand-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-800"
            >
              Got it
            </button>
          </div>
        ) : (
          <>
            <h3 className="text-xl font-bold text-slate-900 mb-1">
              Join the Waitlist
            </h3>
            <p className="text-sm text-slate-500 mb-6">
              Never Grounded is in beta. Sign up for early access.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="wl-email"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  id="wl-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label
                  htmlFor="wl-name"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Name
                </label>
                <input
                  id="wl-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="Jane Smith"
                />
              </div>
              <div>
                <label
                  htmlFor="wl-company"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Company
                </label>
                <input
                  id="wl-company"
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                  placeholder="Acme Corp"
                />
              </div>
              <div>
                <label
                  htmlFor="wl-usecase"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  How will you use Never Grounded?
                </label>
                <textarea
                  id="wl-usecase"
                  value={useCase}
                  onChange={(e) => setUseCase(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none resize-none"
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
                className="w-full rounded-xl bg-brand-900 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {state === "submitting" ? "Joining..." : "Join Waitlist"}
              </button>
            </form>
          </>
        )}
      </div>
    </dialog>
  );
}
