import { getBranding } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";

import { buildBrandingCss, type BrandingColors } from "@/lib/branding-css";
import { getHostBranding } from "@/lib/host-branding";

// Force server-side rendering at request time — NOT at build time.
// Prerendering would try to call getBranding(prisma) during `next build`,
// which fails because the build environment has no DATABASE_URL wired up.
// That took down 31 consecutive App deploys today (first failure was
// immediately after PR #112 added this layout) until this flag landed.
export const dynamic = "force-dynamic";

/**
 * Wraps every route under /auth/* so the Pixie Dust LoginPage renders
 * with tenant branding (logo, colors, heading) from AppSettings.
 *
 * LoginPage reads its branding from a <script id="branding-data">
 * JSON blob on the client; see
 * plugins/dashboard/src/pages/LoginPage.tsx `useBranding()`.
 * It reads colors from `--color-login-*` / `--primary` / `--border`
 * CSS custom properties, which `buildBrandingCss()` populates from
 * AppSettings hex columns.
 */
export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const branding = await getBranding(prisma);
  const { fallbackName, isPrimary } = await getHostBranding();

  const brandingCss = buildBrandingCss(branding as BrandingColors);
  const customCss = [brandingCss, branding.customCss]
    .filter((s): s is string => Boolean(s && s.trim()))
    .join("\n\n");

  const brandingData = {
    brandName: branding.brandName ?? fallbackName ?? null,
    brandLogoUrl:
      branding.brandLogoUrl ?? (isPrimary ? "/logo.svg" : null),
    brandLogoUrlDark: branding.brandLogoUrlDark ?? null,
    brandTagline: branding.brandTagline ?? null,
    loginHeading: branding.loginHeading ?? null,
    loginSubheading: branding.loginSubheading ?? null,
  };

  return (
    <>
      {customCss ? (
        <style
          dangerouslySetInnerHTML={{ __html: customCss }}
          data-branding="auth"
        />
      ) : null}
      <script
        id="branding-data"
        type="application/json"
        // eslint-disable-next-line react/no-danger -- controlled server-side
        dangerouslySetInnerHTML={{ __html: JSON.stringify(brandingData) }}
      />
      {children}
    </>
  );
}
