export const dynamic = "force-dynamic";

import { NextResponse } from "next/server";

/**
 * Apple App Site Association (AASA) — declares which iOS apps may
 * claim universal links for `app.lintpdf.com`. Read by Apple's CDN
 * shortly after a fresh install of the LintPDF mobile app, with no
 * file extension and `Content-Type: application/json`.
 *
 * Two env vars drive the contents:
 *   LINTPDF_AASA_APP_ID — `<TEAMID>.<bundle id>`, e.g. `ABCD1234.com.lintpdf.mobile`.
 *   LINTPDF_AASA_PATHS — comma-separated path patterns the app claims (defaults to `/view/*,/approve/*`).
 *
 * Until both an iOS bundle exists and the human has set
 * `LINTPDF_AASA_APP_ID`, this endpoint returns 404. That keeps the
 * deployment honest — no AASA file means iOS won't try to associate
 * a placeholder bundle id, and the underlying `https://app.lintpdf.com/view/{token}`
 * URL keeps falling back to the responsive web viewer (which is
 * already mobile-friendly).
 */
export async function GET() {
  const appId = process.env.LINTPDF_AASA_APP_ID?.trim();
  if (!appId) {
    // 404 rather than empty 200 — Apple's CDN treats malformed AASA
    // as cause to back off retries, but it treats 404 as "no AASA
    // configured here" and re-checks on app updates. 404 is safer.
    return new NextResponse(
      "Apple App Site Association not configured.",
      { status: 404 },
    );
  }

  const paths = (process.env.LINTPDF_AASA_PATHS ?? "/view/*,/approve/*")
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);

  // Modern AASA shape (iOS 13+). The legacy `apps: []` and `paths`
  // entries are still required by some carrier proxies that haven't
  // updated their parsers, but iOS itself ignores them.
  const aasa = {
    applinks: {
      apps: [],
      details: [
        {
          appID: appId,
          appIDs: [appId],
          paths,
        },
      ],
    },
    webcredentials: {
      apps: [appId],
    },
  };

  return new NextResponse(JSON.stringify(aasa), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
