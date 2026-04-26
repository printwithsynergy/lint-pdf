import { useState } from "react";
import { Activity, ArrowRight, CheckCircle, Loader, XCircle } from "lucide-react";
import type {
  AppConfig,
  TenantLookupResponse,
  TestConnectionResult,
} from "../lib/types";
import { testConnection } from "../lib/tauri";

interface OnboardingProps {
  config: AppConfig;
  onComplete: (next: AppConfig) => Promise<void>;
}

type Step = "tenant" | "api-key";

/**
 * First-run gate. Captures the tenant identifier (so the app loads
 * that tenant's branding) and the API key (so subsequent engine
 * calls authenticate). Persists everything via the existing
 * `saveConfig` round-trip — no new Tauri commands needed.
 *
 * The user can re-enter this flow from Settings → "Change tenant"
 * which clears `tenant_id`, `tenant_name`, `tenant_branding`, and
 * `api_key`.
 */
export function Onboarding({ config, onComplete }: OnboardingProps) {
  const [step, setStep] = useState<Step>("tenant");
  const [tenantQuery, setTenantQuery] = useState(config.tenant_name || "");
  const [tenantLookup, setTenantLookup] = useState<TenantLookupResponse | null>(
    null,
  );
  const [tenantError, setTenantError] = useState<string | null>(null);
  const [tenantLoading, setTenantLoading] = useState(false);

  const [apiKey, setApiKey] = useState(config.api_key || "");
  const [apiKeyError, setApiKeyError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(
    null,
  );
  const [testing, setTesting] = useState(false);
  const [persisting, setPersisting] = useState(false);

  async function handleTenantSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = tenantQuery.trim();
    if (!q) {
      setTenantError("Enter a tenant name, slug, id, or domain.");
      return;
    }

    setTenantLoading(true);
    setTenantError(null);
    setTenantLookup(null);

    try {
      const url = new URL("/api/public/tenant-lookup", config.app_base_url);
      url.searchParams.set("q", q);
      const res = await fetch(url.toString(), { method: "GET" });

      if (res.status === 404) {
        setTenantError(
          "We couldn't find a tenant matching that. Double-check the name or use the tenant id from your account.",
        );
        return;
      }
      if (!res.ok) {
        setTenantError(
          `Lookup failed (HTTP ${res.status}). Check your network connection and try again.`,
        );
        return;
      }
      const data = (await res.json()) as TenantLookupResponse;
      setTenantLookup(data);
      setStep("api-key");
    } catch (err) {
      setTenantError(
        `Lookup failed: ${err instanceof Error ? err.message : String(err)}`,
      );
    } finally {
      setTenantLoading(false);
    }
  }

  async function handleApiKeySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!tenantLookup) return;
    const key = apiKey.trim();
    if (!key) {
      setApiKeyError("Paste an API key to continue.");
      return;
    }

    setTesting(true);
    setApiKeyError(null);
    setTestResult(null);

    let result: TestConnectionResult;
    try {
      result = await testConnection(config.base_url, key);
    } catch (err) {
      setApiKeyError(
        `Connection probe failed: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
      setTesting(false);
      return;
    }
    setTestResult(result);
    setTesting(false);

    if (!result.health_ok || !result.auth_ok) {
      setApiKeyError(
        result.error ??
          "API key was rejected. Check the key in your dashboard and try again.",
      );
      return;
    }

    setPersisting(true);
    try {
      await onComplete({
        ...config,
        api_key: key,
        tenant_id: tenantLookup.tenantId,
        tenant_name: tenantLookup.name,
        tenant_branding: tenantLookup.branding,
      });
    } catch (err) {
      setApiKeyError(
        `Failed to save configuration: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
      setPersisting(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <header className="flex items-center gap-2 border-b border-gray-200 bg-white px-6 py-3">
        <Activity className="h-5 w-5 text-brand-600" />
        <h1 className="text-sm font-semibold text-gray-900">
          LintPDF Hot Folders — Welcome
        </h1>
      </header>

      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
          <StepIndicator step={step} />

          {step === "tenant" && (
            <form onSubmit={handleTenantSubmit} className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Connect to your tenant
                </h2>
                <p className="mt-1 text-sm text-gray-600">
                  Enter the name, slug, id, or custom domain of the LintPDF
                  tenant you belong to. We'll load that tenant's branding so
                  the app looks like home.
                </p>
              </div>

              <input
                type="text"
                autoFocus
                value={tenantQuery}
                onChange={(e) => setTenantQuery(e.target.value)}
                placeholder="acme-printers"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
              />

              {tenantError && (
                <div className="flex items-start gap-2 rounded-md bg-red-50 p-3 text-sm text-red-700">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{tenantError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={tenantLoading}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {tenantLoading ? (
                  <>
                    <Loader className="h-4 w-4 animate-spin" />
                    Looking up tenant…
                  </>
                ) : (
                  <>
                    Continue
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {step === "api-key" && tenantLookup && (
            <form onSubmit={handleApiKeySubmit} className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Sign in to {tenantLookup.name}
                </h2>
                <p className="mt-1 text-sm text-gray-600">
                  Paste an API key from{" "}
                  <span className="font-medium text-gray-800">
                    {tenantLookup.slug}
                  </span>
                  's dashboard → API Keys. We'll validate it before saving.
                </p>
              </div>

              <input
                type="password"
                autoFocus
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="lp_live_…"
                className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm shadow-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
              />

              {testResult?.health_ok && testResult.auth_ok && !apiKeyError && (
                <div className="flex items-start gap-2 rounded-md bg-green-50 p-3 text-sm text-green-700">
                  <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>Connected (latency {testResult.latency_ms}ms)</span>
                </div>
              )}

              {apiKeyError && (
                <div className="flex items-start gap-2 rounded-md bg-red-50 p-3 text-sm text-red-700">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{apiKeyError}</span>
                </div>
              )}

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setStep("tenant");
                    setApiKeyError(null);
                    setTestResult(null);
                  }}
                  className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={testing || persisting}
                  className="flex flex-1 items-center justify-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {testing ? (
                    <>
                      <Loader className="h-4 w-4 animate-spin" />
                      Validating…
                    </>
                  ) : persisting ? (
                    <>
                      <Loader className="h-4 w-4 animate-spin" />
                      Saving…
                    </>
                  ) : (
                    <>
                      Finish setup
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}

function StepIndicator({ step }: { step: Step }) {
  return (
    <div className="mb-6 flex items-center gap-2 text-xs">
      <span
        className={
          step === "tenant"
            ? "rounded-full bg-brand-600 px-2 py-0.5 font-medium text-white"
            : "rounded-full bg-green-500 px-2 py-0.5 font-medium text-white"
        }
      >
        1 · Tenant
      </span>
      <span className="h-px flex-1 bg-gray-200" />
      <span
        className={
          step === "api-key"
            ? "rounded-full bg-brand-600 px-2 py-0.5 font-medium text-white"
            : "rounded-full bg-gray-200 px-2 py-0.5 font-medium text-gray-600"
        }
      >
        2 · API key
      </span>
    </div>
  );
}
