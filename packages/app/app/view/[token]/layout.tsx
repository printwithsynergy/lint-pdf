import { getBranding } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";

import { buildBrandingCss, type BrandingColors } from "@/lib/branding-css";

/**
 * Public report-viewer route. Pulls AppSettings branding so the
 * primary / accent / ring colors match the tenant's theme, same
 * way /dashboard and /auth do. Per-tenant overrides (on share links
 * that belong to a specific tenant custom domain) continue to be
 * resolved by the viewer page itself via `hostFallbackClient()` +
 * `jobData.brandName / jobData.logoUrl`; this layout only provides
 * the base CSS-variable chain so `focus:ring-primary`, `bg-primary`,
 * etc. render against the right palette instead of an unstyled
 * fallback.
 */
export default async function ViewLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const branding = await getBranding(prisma);
  const brandingCss = buildBrandingCss(branding as BrandingColors);
  const customCss = [brandingCss, branding.customCss]
    .filter((s): s is string => Boolean(s && s.trim()))
    .join("\n\n");
  return (
    <>
      {customCss ? (
        <style
          dangerouslySetInnerHTML={{ __html: customCss }}
          data-branding="view"
        />
      ) : null}
      {children}
    </>
  );
}
