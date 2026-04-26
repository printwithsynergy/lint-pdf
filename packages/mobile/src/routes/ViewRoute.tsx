import { useParams } from "react-router-dom";
import { XCircle } from "lucide-react";
import { PdfViewer } from "@lintpdf/viewer-shared";
import type { CapturedTenant } from "../lib/types";
import { getApiBaseUrl } from "../lib/api";

interface ViewRouteProps {
  tenant: CapturedTenant;
}

/**
 * Mounts the shared `<PdfViewer>` against the captured tenant's
 * LintPDF host. The shared viewer is already mobile-responsive
 * (768px breakpoint, MobileBottomSheet, auto-fit zoom at 96 DPI),
 * so the mobile app gets the full feature set — annotations,
 * measure, densitometer, color-picker — for free.
 *
 * Token-only auth: the URL token IS the credential (no session
 * cookie required). `apiBaseUrl` is set so the viewer's tile and
 * findings fetches resolve to `app.lintpdf.com` instead of the
 * mobile bundle's own origin.
 */
export function ViewRoute(_props: ViewRouteProps) {
  const { token } = useParams<{ token: string }>();

  if (!token) {
    return (
      <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center px-4 py-12 text-center">
        <XCircle className="mb-3 h-10 w-10 text-red-500" />
        <h1 className="text-lg font-semibold text-gray-900">
          Missing share token
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          The link you opened doesn't include a viewer token.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full">
      <PdfViewer
        jobId=""
        publicToken={token}
        apiBaseUrl={getApiBaseUrl()}
      />
    </div>
  );
}
