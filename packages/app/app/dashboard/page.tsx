import { validateSession } from "@thinkneverland/pixie-dust-auth";
import {
  getCookieName,
  getPermissions,
} from "@thinkneverland/pixie-dust-config";
import {
  DashboardOverviewPage,
  filterNavByUser,
} from "@thinkneverland/pixie-dust-dashboard";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ensureRegistry } from "@/lib/plugins";

const ACTIVE_TENANT_COOKIE = "pd-active-tenant";

export default async function Page() {
  const cookieStore = await cookies();
  const token = cookieStore.get(getCookieName())?.value;
  if (!token) redirect("/auth/login");

  const session = await validateSession(prisma, token);
  if (!session.valid) redirect("/auth/login");

  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    select: { id: true, email: true, name: true, isSuperAdmin: true },
  });
  if (!user) redirect("/auth/login");

  const tenantMemberships = await prisma.tenantUser.findMany({
    where: { userId: session.user.id },
    include: {
      tenant: { select: { id: true, name: true, slug: true } },
    },
    orderBy: { joinedAt: "asc" },
  });

  let activeTenantId: string | null =
    cookieStore.get(ACTIVE_TENANT_COOKIE)?.value ?? null;
  if (
    activeTenantId &&
    !tenantMemberships.some((m) => m.tenant.id === activeTenantId)
  ) {
    activeTenantId = null;
  }
  if (!activeTenantId && tenantMemberships.length === 1) {
    activeTenantId = tenantMemberships[0]!.tenant.id;
  }

  const activeTenant = tenantMemberships.find(
    (m) => m.tenant.id === activeTenantId,
  );
  const tenantRole = activeTenant?.role ?? null;

  // Boot plugins before reading permissions — ctx.addPermission() populates
  // the registry, so getPermissions() returns {} if called first.
  const registry = await ensureRegistry();

  const allPermissions = getPermissions();
  const userPermissions = tenantRole
    ? Object.entries(allPermissions)
        .filter(([, roles]) => roles.includes(tenantRole))
        .map(([p]) => p)
    : [];

  const accessibleNavItems = filterNavByUser(registry.getNavItems(), {
    ...user,
    tenantRole,
    permissions: userPermissions,
  }).filter((i) => i.href !== "/dashboard");

  const teamMemberCount = activeTenantId
    ? await prisma.tenantUser.count({ where: { tenantId: activeTenantId } })
    : 0;
  const orgCount = user.isSuperAdmin
    ? await prisma.tenant.count()
    : tenantMemberships.length;

  return (
    <DashboardOverviewPage
      user={user}
      activeTenantId={activeTenantId}
      activeTenantName={activeTenant?.tenant.name ?? null}
      tenantRole={tenantRole}
      tenantCount={tenantMemberships.length}
      orgCount={orgCount}
      teamMemberCount={teamMemberCount}
      userPermissions={userPermissions}
      accessibleNavItems={accessibleNavItems}
      widgets={registry.getDashboardWidgets()}
      db={prisma}
    />
  );
}
