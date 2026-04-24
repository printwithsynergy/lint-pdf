import { validateSession, getBranding } from "@thinkneverland/pixie-dust-auth";
import { getCookieName } from "@thinkneverland/pixie-dust-config";
import {
  DashboardShell,
  filterNavByUser,
} from "@thinkneverland/pixie-dust-dashboard";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import {
  getTenantFeatureFlags,
  resolveEngineTenantId,
} from "@thinkneverland/grounded-plugin";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ensureRegistry } from "@/lib/plugins";
import { SuperAdminToolbar } from "@/components/super-admin-toolbar";
import { ClientProviders } from "@/components/client-providers";
import { buildBrandingCss, type BrandingColors } from "@/lib/branding-css";
import { getHostBranding } from "@/lib/host-branding";

const ACTIVE_TENANT_COOKIE = "pd-active-tenant";

// Nav items that should only render when a tenant feature flag is on.
// Keyed by href, value picks the flag to read from the engine's effective
// entitlements payload. Super admins bypass this entirely.
const TENANT_FEATURE_GATED_HREFS: Record<
  string,
  keyof Awaited<ReturnType<typeof getTenantFeatureFlags>>
> = {
  "/dashboard/downloads": "desktop_app_enabled",
};

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const token = cookieStore.get(getCookieName())?.value;
  if (!token) redirect("/auth/login");

  const session = await validateSession(prisma, token);
  if (!session.valid) redirect("/auth/login");

  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    select: {
      id: true,
      email: true,
      name: true,
      avatarUrl: true,
      isSuperAdmin: true,
    },
  });
  if (!user) redirect("/auth/login");

  const registry = await ensureRegistry();
  let navItems = filterNavByUser(registry.getNavItems(), user);

  // Entitlement-gate tenant-feature-flag nav items (desktop, etc.) for
  // non-super-admin sessions. Super admins always see every entry so ops
  // can download / QA regardless of which tenant they're impersonating.
  if (!user.isSuperAdmin) {
    const gatedHrefs = Object.keys(TENANT_FEATURE_GATED_HREFS);
    const hasGatedItem = navItems.some((item) =>
      gatedHrefs.includes(item.href),
    );
    const activeTenantId = cookieStore.get(ACTIVE_TENANT_COOKIE)?.value;
    if (hasGatedItem && activeTenantId) {
      const engineId = await resolveEngineTenantId(activeTenantId);
      const flags = await getTenantFeatureFlags(engineId);
      navItems = navItems.filter((item) => {
        const flagKey = TENANT_FEATURE_GATED_HREFS[item.href];
        return !flagKey || flags[flagKey];
      });
    } else if (hasGatedItem) {
      // No active tenant selected yet — hide the gated items rather than
      // showing something the user can't actually use.
      navItems = navItems.filter((item) => !gatedHrefs.includes(item.href));
    }
  }

  // When impersonating, load the target tenant's branding instead
  const branding = await getBranding(prisma);
  const { fallbackName, isPrimary } = await getHostBranding();

  const brandingCss = buildBrandingCss(branding as BrandingColors);
  const customCss = [brandingCss, branding.customCss]
    .filter((s): s is string => Boolean(s && s.trim()))
    .join("\n\n");

  return (
    <ClientProviders>
      <DashboardShell
        navItems={navItems}
        user={user}
        brandName={branding.brandName ?? fallbackName}
        brandLogoUrl={
          branding.brandLogoUrl ?? (isPrimary ? "/logo.svg" : undefined)
        }
        customCss={customCss || undefined}
        topSlot={user.isSuperAdmin ? <SuperAdminToolbar /> : undefined}
      >
        {children}
      </DashboardShell>
    </ClientProviders>
  );
}
