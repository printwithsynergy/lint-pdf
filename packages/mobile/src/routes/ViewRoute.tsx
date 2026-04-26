import { useParams } from "react-router-dom";
import { FileText } from "lucide-react";
import type { CapturedTenant } from "../lib/types";

interface ViewRouteProps {
  tenant: CapturedTenant;
}

/**
 * Placeholder for the interactive viewer. The next slice will mount
 * `<PdfViewer publicToken={token} />` from `@lintpdf/viewer-shared`
 * and wire it through `apiFetch` so the canvas tile fetches and
 * findings calls land at the configured `app.lintpdf.com` host.
 *
 * Today this just confirms the route resolves and the tenant theme
 * applies — the heavy viewer integration lands in a follow-up so
 * this PR stays reviewable.
 */
export function ViewRoute({ tenant }: ViewRouteProps) {
  const { token } = useParams<{ token: string }>();

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col items-center justify-center px-4 py-12 text-center">
      <FileText className="mb-3 h-10 w-10 text-brand-600" />
      <h1 className="text-lg font-semibold text-gray-900">Report viewer</h1>
      <p className="mt-1 max-w-md text-sm text-gray-600">
        Tenant <span className="font-medium">{tenant.name}</span> · token{" "}
        <span className="font-mono text-xs text-gray-500">
          {token ?? "(missing)"}
        </span>
      </p>
      <p className="mt-4 max-w-md text-xs text-gray-400">
        The interactive PDF viewer + findings + annotations land in the next
        slice. This route exists today so universal-link routing can be
        validated against a real path.
      </p>
    </div>
  );
}
