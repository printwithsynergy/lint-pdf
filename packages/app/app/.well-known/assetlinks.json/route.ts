export const dynamic = "force-dynamic";

import { NextResponse } from "next/server";

/**
 * Android Digital Asset Links — declares which Android apps may
 * claim App Links for `app.lintpdf.com`. Read by the Play Services
 * verifier on first install (and on every app update) to decide
 * whether tapping a `https://app.lintpdf.com/view/{token}` link
 * launches the app or the browser.
 *
 * Two env vars drive the contents:
 *   LINTPDF_ASSETLINKS_PACKAGE — Android package id, e.g. `com.lintpdf.mobile`.
 *   LINTPDF_ASSETLINKS_FINGERPRINTS — comma-separated SHA256 fingerprints
 *     of the signing certificate(s). Get them from `keytool -list -v
 *     -keystore release.jks` and copy the `SHA256:` line. Multiple
 *     values let dev / staging / prod keystores coexist.
 *
 * Until both an Android bundle exists and the human has set both
 * env vars, this endpoint returns 404. Same reasoning as the AASA
 * companion: incorrect placeholder values would actively confuse
 * the Play Services verifier, while 404 is treated as "no app
 * claims this domain yet" and re-checked on next install.
 */
export async function GET() {
  const pkg = process.env.LINTPDF_ASSETLINKS_PACKAGE?.trim();
  const fingerprintsEnv = process.env.LINTPDF_ASSETLINKS_FINGERPRINTS?.trim();

  if (!pkg || !fingerprintsEnv) {
    return new NextResponse("Android assetlinks not configured.", {
      status: 404,
    });
  }

  const fingerprints = fingerprintsEnv
    .split(",")
    .map((f) => f.trim())
    .filter(Boolean);

  if (fingerprints.length === 0) {
    return new NextResponse(
      "LINTPDF_ASSETLINKS_FINGERPRINTS is set but contains no values.",
      { status: 500 },
    );
  }

  const assetlinks = [
    {
      relation: ["delegate_permission/common.handle_all_urls"],
      target: {
        namespace: "android_app",
        package_name: pkg,
        sha256_cert_fingerprints: fingerprints,
      },
    },
  ];

  return new NextResponse(JSON.stringify(assetlinks), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
