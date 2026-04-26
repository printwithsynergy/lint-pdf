import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import type { CapturedTenant } from "../lib/types";
import { clearTenant } from "../lib/tenant";

interface SettingsRouteProps {
  tenant: CapturedTenant;
  onChangeTenant: () => void;
}

export function SettingsRoute({ tenant, onChangeTenant }: SettingsRouteProps) {
  const navigate = useNavigate();

  function handleChangeTenant() {
    clearTenant();
    onChangeTenant();
    navigate("/onboarding", { replace: true });
  }

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <h1 className="mb-5 text-lg font-semibold text-gray-900">Settings</h1>

      <section className="rounded-2xl bg-white p-4 shadow-sm">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-900">
          <Building2 className="h-4 w-4 text-brand-600" />
          Tenant
        </h2>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-gray-900">
              {tenant.name}
            </p>
            <p className="truncate font-mono text-xs text-gray-500">
              {tenant.tenantId}
            </p>
          </div>
          <button
            type="button"
            onClick={handleChangeTenant}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            Change tenant
          </button>
        </div>
        <p className="mt-3 text-xs text-gray-400">
          Change tenant clears the captured tenant + branding and re-runs the
          Onboarding screen.
        </p>
      </section>
    </div>
  );
}
