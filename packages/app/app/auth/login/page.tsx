"use client";

/* eslint-disable @next/next/no-img-element */

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, useRef, useCallback, useEffect } from "react";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}

interface Branding {
  brandName: string;
  brandLogoUrl: string;
  primaryColor: string | null;
  loginBgColor: string | null;
  loginHeading: string | null;
  loginSubheading: string | null;
}

const DEFAULT_BRANDING: Branding = {
  brandName: "LintPDF",
  brandLogoUrl: "/logo.png",
  primaryColor: null,
  loginBgColor: null,
  loginHeading: null,
  loginSubheading: null,
};

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error" | "code"
  >("idle");
  const [message, setMessage] = useState("");
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const codeInputs = useRef<(HTMLInputElement | null)[]>([]);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  const pollingRef = useRef<string | null>(null);
  const [branding, setBranding] = useState<Branding>(DEFAULT_BRANDING);

  // Fetch platform branding from AppSettings (via Pixie Dust getBranding pattern)
  useEffect(() => {
    fetch("/api/auth/branding")
      .then((r) => r.json())
      .then((data) => setBranding({ ...DEFAULT_BRANDING, ...data }))
      .catch(() => {}); // Keep defaults on error
  }, []);

  // Store plan param in sessionStorage for post-auth redirect
  useEffect(() => {
    const plan = searchParams.get("plan");
    if (plan) {
      sessionStorage.setItem("lintpdf_signup_plan", plan);
    }
  }, [searchParams]);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    pollingRef.current = null;
  }, []);

  const getPostAuthRedirect = useCallback(() => {
    const plan = sessionStorage.getItem("lintpdf_signup_plan");
    if (plan) {
      sessionStorage.removeItem("lintpdf_signup_plan");
      return `/dashboard/billing/checkout?plan=${encodeURIComponent(plan)}`;
    }
    return "/dashboard";
  }, []);

  const startPolling = useCallback(
    (token: string) => {
      stopPolling();
      pollingRef.current = token;

      pollingIntervalRef.current = setInterval(() => {
        void (async () => {
          try {
            const res = await fetch(
              `/api/auth/magic-link/status?pollingToken=${encodeURIComponent(token)}`,
            );
            const data = await res.json();

            if (data.verified) {
              stopPolling();
              setStatus("success");
              setMessage("Signed in! Redirecting\u2026");
              window.location.href = `/api/auth/claim-session?pollingToken=${encodeURIComponent(token)}`;
            }
          } catch {
            // Silently retry on network errors
          }
        })();
      }, 3000);
    },
    [stopPolling],
  );

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  useEffect(() => {
    const error = searchParams.get("error");
    if (error) {
      setStatus("error");
      setMessage(decodeURIComponent(error));
    }
  }, [searchParams]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setMessage("");

    try {
      const res = await fetch("/api/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();

      if (res.ok) {
        if (data.pollingToken) {
          setStatus("code");
          setMessage(
            data.message ?? "Check your email for a sign-in link and code.",
          );
          startPolling(data.pollingToken);
        } else {
          setStatus("success");
          setMessage(data.message ?? "Check your email for a sign-in link.");
        }
      } else {
        setStatus("error");
        setMessage(data.error ?? "Something went wrong.");
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Please try again.");
    }
  }

  function handleCodeChange(index: number, value: string) {
    if (!/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value.slice(-1);
    setCode(newCode);

    if (value && index < 5) {
      codeInputs.current[index + 1]?.focus();
    }

    const fullCode = newCode.join("");
    if (fullCode.length === 6) {
      void submitCode(fullCode);
    }
  }

  function handleCodeKeyDown(index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      codeInputs.current[index - 1]?.focus();
    }
  }

  function handleCodePaste(e: React.ClipboardEvent) {
    e.preventDefault();
    const pasted = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (!pasted) return;

    const newCode = [...code];
    for (let i = 0; i < 6; i++) {
      newCode[i] = pasted[i] ?? "";
    }
    setCode(newCode);

    if (pasted.length === 6) {
      void submitCode(pasted);
    } else {
      codeInputs.current[pasted.length]?.focus();
    }
  }

  async function submitCode(fullCode: string) {
    stopPolling();
    setStatus("loading");
    setMessage("");

    try {
      const res = await fetch("/api/auth/verify-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code: fullCode }),
      });

      const data = await res.json();

      if (res.ok) {
        setStatus("success");
        setMessage("Signed in! Redirecting\u2026");
        router.push(getPostAuthRedirect());
      } else {
        setStatus("error");
        setMessage(data.error ?? "Invalid code.");
        setCode(["", "", "", "", "", ""]);
        codeInputs.current[0]?.focus();
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Please try again.");
    }
  }

  const bgStyle = branding.loginBgColor
    ? { backgroundColor: branding.loginBgColor }
    : undefined;
  const btnStyle = branding.primaryColor
    ? { backgroundColor: branding.primaryColor }
    : undefined;

  return (
    <main
      className="flex min-h-screen items-center justify-center bg-white p-4"
      style={bgStyle}
    >
      {/* Subtle brand gradient background — matches marketing hero */}
      {!branding.loginBgColor && (
        <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-white via-brand-50/30 to-white" />
      )}

      <div className="relative z-10 w-full max-w-[420px]">
        {/* Branding — dynamic logo + name from AppSettings */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <img
            src={branding.brandLogoUrl}
            alt={branding.brandName}
            className="h-12 w-12"
          />
          <span className="text-xl font-semibold tracking-tight text-brand-900">
            {branding.brandName}
          </span>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-slate-200/60 bg-white p-8 shadow-lg shadow-brand-900/5">
          <div className="mb-6 text-center">
            <h1 className="text-[22px] font-bold tracking-tight text-slate-900">
              {status === "code"
                ? "Check your email"
                : branding.loginHeading ?? "Sign in"}
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-slate-500">
              {status === "code" ? (
                <>
                  We sent a code to{" "}
                  <strong className="text-slate-900">{email}</strong>
                </>
              ) : (
                branding.loginSubheading ??
                  "Enter your email to sign in or create an account."
              )}
            </p>
          </div>

          {status === "success" ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center">
              <p className="text-sm font-medium text-emerald-700">{message}</p>
            </div>
          ) : status === "code" ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
                <p className="text-sm font-medium text-emerald-700">
                  Enter the 6-digit code, or click the link in your email.
                </p>
              </div>

              <div
                className="flex justify-center gap-2"
                onPaste={handleCodePaste}
              >
                {code.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => {
                      codeInputs.current[i] = el;
                    }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleCodeChange(i, e.target.value)}
                    onKeyDown={(e) => handleCodeKeyDown(i, e)}
                    className="h-12 w-10 rounded-lg border border-slate-200 bg-white text-center text-lg font-semibold text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                ))}
              </div>

              <p className="text-center text-xs text-slate-400">
                Waiting for verification\u2026
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-slate-700"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                  className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {status === "error" && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="text-sm text-red-700">{message}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={status === "loading"}
                className="w-full rounded-lg bg-brand-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-50"
                style={btnStyle}
              >
                {status === "loading" ? "Sending..." : "Continue with Email"}
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          No password needed. We&apos;ll send you a secure link.
        </p>
      </div>
    </main>
  );
}
