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
  const branding = await getBranding(prisma);

  return (
    <DashboardShell
      navItems={navItems}
      user={user}
      brandName={branding.brandName ?? "LintPDF"}
      brandLogoUrl={branding.brandLogoUrl}
      customCss={branding.customCss}
    >
      {children}
    </DashboardShell>
  );
}
