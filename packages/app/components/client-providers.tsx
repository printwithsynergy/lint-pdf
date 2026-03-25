"use client";

import { ToastProvider } from "@thinkneverland/pixie-dust-ui";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
