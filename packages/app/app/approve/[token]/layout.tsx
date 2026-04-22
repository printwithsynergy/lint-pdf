import { getBranding } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";

import { buildBrandingCss, type BrandingColors } from "@/lib/branding-css";

// Runtime-only rendering; see packages/app/app/auth/layout.tsx for the
// same reason — getBranding(prisma) needs a live DATABASE_URL.
export const dynamic = "force-dynamic";

/**
 * Public approval-chain route. Injects AppSettings branding so the
 * page's `bg-background` / `text-foreground` / `text-primary`
 * tokens resolve against the tenant's palette instead of Tailwind
 * defaults. The page body (`page.tsx`) still uses tenant-agnostic
 * semantic classes; this layout supplies the CSS-variable chain
 * they consume.
 */
export default async function ApproveLayout({
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
          data-branding="approve"
        />
      ) : null}
      {children}
    </>
  );
}
