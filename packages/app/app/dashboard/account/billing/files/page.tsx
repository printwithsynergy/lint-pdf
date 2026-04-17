"use client";

// File-pack billing page. Mirrors the credits page but tracks the
// metered file-quota pool. The plan includes a monthly allotment;
// purchased packs roll over for 12 months.

import { useCallback, useEffect, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";

import { SkeletonDashboard } from "@/components/skeleton";

interface FileQuota {
  tenant_id: string;
  total_remaining: number;
  monthly_allotment_remaining: number;
  purchased_remaining: number;
  active_packages: number;
  monthly_allotment: number;
}

const FILE_PACKS: { size: "500" | "2500" | "10000"; usd: number; label: string }[] = [
  { size: "500", usd: 15, label: "500 files" },
  { size: "2500", usd: 60, label: "2,500 files — 20% off" },
  { size: "10000", usd: 200, label: "10,000 files — 33% off" },
];

export default function FilesBillingPage() {
  const [quota, setQuota] = useState<FileQuota | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [buyingSize, setBuyingSize] = useState<string | null>(null);
  const [toast, setToast] = useState<string>("");

  const fetchQuota = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/files/quota");
      if (!resp.ok) throw new Error(`Quota fetch failed (${resp.status})`);
      setQuota(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load quota");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchQuota();
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "success") {
      setToast(
        "Payment received — files land in your account within ~10 seconds after Stripe confirms.",
      );
    } else if (params.get("checkout") === "cancelled") {
      setToast("Purchase cancelled. Your quota is unchanged.");
    }
  }, [fetchQuota]);

  async function handleBuy(size: "500" | "2500" | "10000") {
    setBuyingSize(size);
    setError("");
    try {
      const resp = await fetch("/api/lintpdf/files/topup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pack: size }),
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || `Topup failed (${resp.status})`);
      }
      const { checkout_url } = await resp.json();
      if (!checkout_url) throw new Error("No checkout URL returned");
      window.location.href = checkout_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create checkout session");
      setBuyingSize(null);
    }
  }

  if (loading) return <SkeletonDashboard />;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">File Packs</h1>
        <p className="text-slate-600 mt-1 text-sm">
          Each PDF submission consumes one file from your monthly allotment (set
          by your plan). When the monthly pool is empty you can either enable
          overage billing or buy a file pack below. Purchased packs roll over
          for 12 months.
        </p>
      </div>

      {toast && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          {toast}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {error}
        </div>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Current quota
        </h2>
        <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Monthly allotment" value={quota?.monthly_allotment ?? 0} />
          <Stat
            label="Monthly remaining"
            value={quota?.monthly_allotment_remaining ?? 0}
          />
          <Stat label="Purchased remaining" value={quota?.purchased_remaining ?? 0} />
          <Stat label="Total files available" value={quota?.total_remaining ?? 0} />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-900">Buy more file packs</h2>
        <p className="text-sm text-slate-600">
          Purchased packs expire 12 months after the purchase date. Payments are
          processed by Stripe — we never see your card details.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {FILE_PACKS.map((p) => (
            <article
              key={p.size}
              className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-5"
            >
              <div>
                <h3 className="text-lg font-semibold text-slate-900">{p.label}</h3>
                <p className="mt-1 text-2xl font-bold text-slate-900">
                  ${p.usd.toLocaleString()}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  ${(p.usd / parseInt(p.size, 10)).toFixed(3)} per file
                </p>
              </div>
              <Button
                className="mt-4 w-full"
                onClick={() => handleBuy(p.size)}
                disabled={buyingSize !== null}
              >
                {buyingSize === p.size ? "Redirecting…" : "Buy"}
              </Button>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">
        {value.toLocaleString()}
      </p>
    </div>
  );
}
