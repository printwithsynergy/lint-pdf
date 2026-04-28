/**
 * Tenant invariant helper.
 *
 * The LintPDF app's contract is that every authenticated user belongs
 * to at least one tenant. Routes assume `req.auth.tenantId` is set;
 * pages render 400/403 cascades when it isn't. A user who lands on
 * the dashboard via magic-link signup, MCP back-door, or any other
 * flow must therefore be enrolled in a tenant before the session is
 * usable.
 *
 * `ensureTenantForUser` is the single place that enforces this:
 *
 *   - returns the user's first existing tenant id if one exists, or
 *   - auto-provisions a fresh tenant from the user's email and
 *     attaches them as OWNER, then returns that tenant id.
 *
 * The bundled Pixie Dust PrismaClient doesn't know about
 * `Tenant.engineTenantId` or `Session.impersonatingTenantId` — both
 * are local-schema-only columns. Raw SQL bypasses the field validator;
 * the columns themselves are guaranteed to exist by
 * `packages/app/scripts/startup.sh`.
 */

import { prisma } from "@thinkneverland/pixie-dust-database/server";

function cuidIsh(): string {
  // Lower-case alpha + base36 — close enough to a CUID for collision
  // resistance without pulling the full @paralleldrive/cuid2 surface.
  return (
    "c" +
    Date.now().toString(36) +
    Math.random().toString(36).slice(2, 12)
  );
}

function deriveSlugFromEmail(email: string): string {
  const localPart = email.split("@")[0] ?? "user";
  const sanitized = localPart
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 32) || "user";
  const shard = Math.random().toString(36).slice(2, 8);
  return `${sanitized}-${shard}`;
}

export interface EnsureTenantResult {
  tenantId: string;
  created: boolean;
}

/**
 * Idempotently guarantee that `userId` (with the given `email`) is a
 * member of at least one tenant. Returns the tenant id of their
 * primary membership and whether a fresh tenant was created here.
 */
export async function ensureTenantForUser(
  userId: string,
  email: string,
  opts: { defaultRole?: "OWNER" | "ADMIN" | "OPERATOR" | "MEMBER" | "VIEWER" } = {},
): Promise<EnsureTenantResult> {
  const existing = await prisma.tenantUser.findFirst({
    where: { userId },
    select: { tenantId: true },
    orderBy: { joinedAt: "asc" },
  });
  if (existing) {
    return { tenantId: existing.tenantId, created: false };
  }

  // No membership yet — provision a fresh tenant. Retry up to 3 times
  // on slug collision (the random shard makes that vanishingly rare,
  // but worth guarding against).
  let attempt = 0;
  while (attempt < 3) {
    const slug = deriveSlugFromEmail(email);
    const collision = await prisma.tenant.findUnique({ where: { slug } });
    if (collision) {
      attempt++;
      continue;
    }

    const tenantId = cuidIsh();
    const engineTenantId = process.env.ENGINE_ADMIN_TENANT_ID ?? null;
    await prisma.$executeRaw`
      INSERT INTO "Tenant" (id, name, slug, "engineTenantId", "createdAt", "updatedAt")
      VALUES (${tenantId}, ${slug}, ${slug}, ${engineTenantId}, NOW(), NOW())
    `;

    await prisma.tenantUser.create({
      data: {
        userId,
        tenantId,
        role: (opts.defaultRole ?? "OWNER") as never,
      },
    });

    return { tenantId, created: true };
  }

  throw new Error(
    "ensureTenantForUser: failed to provision a tenant after 3 attempts",
  );
}
