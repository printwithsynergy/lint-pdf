import { useParams } from "react-router-dom";
import { CheckCircle } from "lucide-react";
import type { CapturedTenant } from "../lib/types";

interface ApproveRouteProps {
  tenant: CapturedTenant;
}

/**
 * Placeholder for the approval flow. The next slice will fetch the
 * approval chain summary via
 * `GET /api/lintpdf/approvals/info/{token}` and render Approve /
 * Reject buttons that POST to
 * `/api/lintpdf/approvals/decide/{token}`.
 */
export function ApproveRoute({ tenant }: ApproveRouteProps) {
  const { token } = useParams<{ token: string }>();

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col items-center justify-center px-4 py-12 text-center">
      <CheckCircle className="mb-3 h-10 w-10 text-brand-600" />
      <h1 className="text-lg font-semibold text-gray-900">Approval request</h1>
      <p className="mt-1 max-w-md text-sm text-gray-600">
        Tenant <span className="font-medium">{tenant.name}</span> · approval
        token{" "}
        <span className="font-mono text-xs text-gray-500">
          {token ?? "(missing)"}
        </span>
      </p>
      <p className="mt-4 max-w-md text-xs text-gray-400">
        The chain summary + Approve/Reject UI lands in the next slice.
      </p>
    </div>
  );
}
