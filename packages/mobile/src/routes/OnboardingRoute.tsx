import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, ArrowRight, Loader, XCircle } from "lucide-react";
import {
  TenantNotFoundError,
  captureTenant,
  lookupTenant,
} from "../lib/tenant";
import type { CapturedTenant } from "../lib/types";

interface OnboardingRouteProps {
  onCaptured: (t: CapturedTenant) => void;
}

/**
 * First-run gate. Captures the tenant identifier so the app can theme
 * itself with that tenant's branding. The captured tenant is persisted
 * via `saveTenant` (localStorage today, `tauri-plugin-store` once the
 * native shell lands).
 *
 * No API-key step on mobile — the v1 surfaces (read-only viewer at
 * `/view/:token`, approval at `/approve/:token`) authenticate via the
 * URL token, not via an API key. A future "Queue" route will require
 * an authenticated session and will gate on its own auth flow.
 */
export function OnboardingRoute({ onCaptured }: OnboardingRouteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) {
      setError("Enter a tenant name, slug, id, or domain.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await lookupTenant(q);
      const captured = await captureTenant(data);
      onCaptured(captured);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof TenantNotFoundError) {
        setError(
          "We couldn't find a tenant matching that. Double-check the name or use the tenant id from your account.",
        );
      } else {
        setError(
          `Lookup failed: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col bg-gray-50">
      <header className="flex items-center gap-2 border-b border-gray-200 bg-white px-4 py-3">
        <Activity className="h-5 w-5 text-brand-600" />
        <h1 className="text-sm font-semibold text-gray-900">
          LintPDF — Welcome
        </h1>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Connect to your tenant
          </h2>
          <p className="mt-1 text-sm text-gray-600">
            Enter the name, slug, id, or custom domain of the LintPDF tenant
            you belong to. We'll load that tenant's branding so the app looks
            like home.
          </p>

          <form onSubmit={handleSubmit} className="mt-5 space-y-3">
            <input
              type="text"
              autoFocus
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="acme-printers"
              className="w-full rounded-lg border border-gray-300 px-3 py-3 text-base shadow-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
            />

            {error && (
              <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-3 text-base font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader className="h-5 w-5 animate-spin" />
                  Looking up tenant…
                </>
              ) : (
                <>
                  Continue
                  <ArrowRight className="h-5 w-5" />
                </>
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
