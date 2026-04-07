/**
 * Server-side permission check for dashboard pages.
 *
 * Reads the user's tenant role and checks it against the required permission.
 * Redirects to /dashboard if the user lacks the permission.
 *
 * Usage in a page or layout:
 *   await requirePermission("api-keys:manage");
 */

import { validateSession } from "@thinkneverland/pixie-dust-auth";
import { getCookieName } from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ensureRegistry } from "@/lib/plugins";

/**
 * Check if the current user has the required permission.
 * Redirects to /dashboard if not.
 */
export async function requirePermission(permission: string): Promise<void> {
  const cookieStore = await cookies();
  const token = cookieStore.get(getCookieName())?.value;
  if (!token) redirect("/auth/login");

  const session = await validateSession(prisma, token);
  if (!session.valid) redirect("/auth/login");

  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    select: { isSuperAdmin: true },
  });

  // Super admins bypass all permission checks
  if (user?.isSuperAdmin) return;

  // Get the user's tenant role
  const tenantUser = await prisma.tenantUser.findFirst({
    where: { userId: session.user.id },
    select: { role: true },
    orderBy: { joinedAt: "asc" },
  });

  if (!tenantUser) {
    redirect("/dashboard");
  }

  // Check if the role has the required permission via the plugin registry
  const registry = await ensureRegistry();
  const registeredPermissions = registry.getPermissions() as Array<{
    permission: string;
    allowedRoles: string[];
    pluginName: string;
  }>;

  if (!registeredPermissions || registeredPermissions.length === 0) {
    // No permissions registered — allow access by default
    return;
  }

  const entry = registeredPermissions.find((p) => p.permission === permission);
  if (!entry) {
    // Permission not registered — allow access by default
    return;
  }

  const userRole = tenantUser.role;
  if (!entry.allowedRoles.includes(userRole)) {
    redirect("/dashboard");
  }
}
