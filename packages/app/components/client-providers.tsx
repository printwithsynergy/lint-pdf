"use client";

import { DashboardProviders } from "@thinkneverland/pixie-dust-dashboard";
import { ToastProvider } from "@thinkneverland/pixie-dust-ui";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <DashboardProviders>
      <ToastProvider>{children}</ToastProvider>
    </DashboardProviders>
  );
}
