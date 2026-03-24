import { validateSession, getBranding } from "@thinkneverland/pixie-dust-auth";
import { getCookieName } from "@thinkneverland/pixie-dust-config";
import {
  DashboardShell,
  filterNavByUser,
} from "@thinkneverland/pixie-dust-dashboard";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ensureRegistry } from "@/lib/plugins";
import { SuperAdminToolbar } from "@/components/super-admin-toolbar";

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
  const navItems = filterNavByUser(registry.getNavItems(), user);

  // When impersonating, load the target tenant's branding instead
  const branding = await getBranding(prisma);

  return (
    <div className="flex min-h-screen flex-col">
      {user.isSuperAdmin && <SuperAdminToolbar />}
      <DashboardShell
        navItems={navItems}
        user={user}
        brandName={branding.brandName ?? "LintPDF"}
        brandLogoUrl={branding.brandLogoUrl ?? "/logo.svg"}
        customCss={branding.customCss}
      >
        {children}
      </DashboardShell>
    </div>
  );
}
