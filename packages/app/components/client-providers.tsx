"use client";

import { DashboardProviders } from "@thinkneverland/pixie-dust-dashboard";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return <DashboardProviders>{children}</DashboardProviders>;
}
