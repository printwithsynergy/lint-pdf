"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

export default function CheckoutPage() {
  return (
    <Suspense>
      <CheckoutContent />
    </Suspense>
  );
}

function CheckoutContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "error" | "redirecting">(
    "loading",
  );
  const [error, setError] = useState("");

  useEffect(() => {
    const plan =
      searchParams.get("plan") ??
      sessionStorage.getItem("grounded_signup_plan");
    sessionStorage.removeItem("grounded_signup_plan");

    const validPlans = ["starter", "growth", "scale", "enterprise"];
    if (!plan || !validPlans.includes(plan)) {
      setStatus("error");
      setError(
        plan
          ? `Invalid plan "${plan}". Please select a valid plan from the pricing page.`
          : "No plan specified. Please select a plan from the pricing page.",
      );
      return;
    }

    void (async () => {
      try {
        const res = await fetch("/api/grounded/billing/checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plan }),
        });

        const data = await res.json();

        if (res.ok && data.url) {
          setStatus("redirecting");
          window.location.href = data.url;
        } else {
          setStatus("error");
          setError(data.error ?? "Failed to create checkout session.");
        }
      } catch {
        setStatus("error");
        setError("Network error. Please try again.");
      }
    })();
  }, [searchParams]);

  return (
    <main className="flex min-h-[60vh] items-center justify-center p-8">
      <div className="text-center">
        {status === "loading" && (
          <>
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-muted-foreground">Preparing your checkout...</p>
          </>
        )}
        {status === "redirecting" && (
          <>
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-muted-foreground">Redirecting to Stripe...</p>
          </>
        )}
        {status === "error" && (
          <div className="max-w-md">
            <p className="text-destructive mb-4">{error}</p>
            <a
              href="/dashboard"
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-secondary transition-colors"
            >
              Back to Dashboard
            </a>
          </div>
        )}
      </div>
    </main>
  );
}
