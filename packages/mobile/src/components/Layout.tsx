import { Link, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { Activity, Settings as SettingsIcon } from "lucide-react";
import type { CapturedTenant } from "../lib/types";

interface LayoutProps {
  tenant: CapturedTenant;
  children: ReactNode;
}

export function Layout({ tenant, children }: LayoutProps) {
  const location = useLocation();
  const onSettings = location.pathname.startsWith("/settings");

  return (
    <div className="flex min-h-full flex-col bg-gray-50">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-brand-600" />
          <h1 className="text-sm font-semibold text-gray-900">
            {tenant.branding.brandName ?? "LintPDF"}
          </h1>
        </Link>
        <Link
          to={onSettings ? "/" : "/settings"}
          className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-900"
          aria-label={onSettings ? "Close settings" : "Open settings"}
        >
          <SettingsIcon className="h-5 w-5" />
        </Link>
      </header>

      <main className="flex-1">{children}</main>
    </div>
  );
}
