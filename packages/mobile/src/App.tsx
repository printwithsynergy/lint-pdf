import { useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ThemeProvider } from "./components/ThemeProvider";
import { ApproveRoute } from "./routes/ApproveRoute";
import { OnboardingRoute } from "./routes/OnboardingRoute";
import { SettingsRoute } from "./routes/SettingsRoute";
import { ViewRoute } from "./routes/ViewRoute";
import { loadTenant } from "./lib/tenant";
import { onDeepLink } from "./lib/tauri";
import type { CapturedTenant } from "./lib/types";

export default function App() {
  const [tenant, setTenant] = useState<CapturedTenant | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const t = await loadTenant();
      if (cancelled) return;
      setTenant(t);
      setHydrated(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Universal-link / App Link taps land here once the app is open.
  // The native shell forwards them through `tauri-plugin-deep-link`;
  // web preview is a no-op (the browser already handles them).
  const navigate = useNavigate();
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    void (async () => {
      unlisten = await onDeepLink((path) => {
        navigate(path, { replace: false });
      });
    })();
    return () => {
      unlisten?.();
    };
  }, [navigate]);

  const branding = useMemo(() => tenant?.branding ?? null, [tenant]);

  if (!hydrated) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-gray-500">
        Loading…
      </div>
    );
  }

  return (
    <ThemeProvider branding={branding}>
      <Routes>
        <Route
          path="/onboarding"
          element={
            tenant ? (
              <Navigate to="/" replace />
            ) : (
              <OnboardingRoute onCaptured={setTenant} />
            )
          }
        />
        {tenant ? (
          <>
            <Route
              path="/"
              element={
                <Layout tenant={tenant}>
                  <Home tenant={tenant} />
                </Layout>
              }
            />
            <Route
              path="/view/:token"
              element={
                <Layout tenant={tenant}>
                  <ViewRoute tenant={tenant} />
                </Layout>
              }
            />
            <Route
              path="/approve/:token"
              element={
                <Layout tenant={tenant}>
                  <ApproveRoute tenant={tenant} />
                </Layout>
              }
            />
            <Route
              path="/settings"
              element={
                <Layout tenant={tenant}>
                  <SettingsRoute
                    tenant={tenant}
                    onChangeTenant={() => setTenant(null)}
                  />
                </Layout>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </>
        ) : (
          <Route path="*" element={<Navigate to="/onboarding" replace />} />
        )}
      </Routes>
    </ThemeProvider>
  );
}

function Home({ tenant }: { tenant: CapturedTenant }) {
  return (
    <div className="mx-auto max-w-md px-4 py-8 text-center">
      <h1 className="text-lg font-semibold text-gray-900">
        Welcome, {tenant.name}
      </h1>
      <p className="mt-2 text-sm text-gray-600">
        Open a LintPDF share link or approval link from your email or messages
        — this app will handle them once universal links are wired up.
      </p>
      <p className="mt-6 text-xs text-gray-400">
        Direct routes for testing during development:
      </p>
      <div className="mt-2 space-y-1 text-xs">
        <p className="font-mono text-gray-500">/view/&lt;token&gt;</p>
        <p className="font-mono text-gray-500">/approve/&lt;token&gt;</p>
      </div>
    </div>
  );
}
