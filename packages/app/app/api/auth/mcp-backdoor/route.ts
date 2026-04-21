export const dynamic = "force-dynamic";

import crypto from "node:crypto";

import { createSession } from "@thinkneverland/pixie-dust-auth";
import {
  getCookieName,
  getCookieOptions,
  env,
} from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { z } from "zod";
import { getClientInfo } from "@/lib/auth-helpers";

// Local Prisma schema adds ``engineTenantId`` on Tenant and
// ``impersonatingTenantId`` on Session; the Pixie Dust PrismaClient
// bundled in ``@thinkneverland/pixie-dust-database/server`` doesn't
// know about those columns, so typed calls that reference them throw
// ``PrismaClientValidationError`` at runtime. The columns themselves
// are guaranteed to exist in Postgres by ``packages/app/scripts/startup.sh``
// — using ``$executeRaw`` / ``$queryRaw`` bypasses the client's field
// validator.

const requestSchema = z.object({
  email: z.string().email(),
  mcpSecretKey: z.string().min(1),
  tenantSlug: z.string().optional(),
  role: z.enum(["OWNER", "ADMIN", "OPERATOR", "MEMBER", "VIEWER"]).optional(),
});

export async function POST(req: Request) {
  if (!env.MCP_BACKDOOR) {
    return new NextResponse(null, { status: 404 });
  }

  try {
    const body = await req.json();
    const parsed = requestSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: "Invalid request. Provide email and mcpSecretKey." },
        { status: 400 },
      );
    }

    const { email, mcpSecretKey, tenantSlug, role } = parsed.data;
    const mcpKey = env.MCP_SECRET_KEY;

    if (!mcpKey) {
      return NextResponse.json(
        { error: "Invalid MCP secret key." },
        { status: 403 },
      );
    }

    if (
      mcpSecretKey.length !== mcpKey.length ||
      !crypto.timingSafeEqual(Buffer.from(mcpSecretKey), Buffer.from(mcpKey))
    ) {
      return NextResponse.json(
        { error: "Invalid MCP secret key." },
        { status: 403 },
      );
    }

    let user = await prisma.user.findUnique({ where: { email } });

    if (!user) {
      user = await prisma.user.create({
        data: { email, name: `MCP Test User (${email})` },
      });
    }

    const { ipAddress } = getClientInfo(req);

    const session = await createSession(prisma, user.id, {
      ipAddress,
      userAgent: "MCP-Backdoor-Test",
    });

    // Handle tenant membership: create/update if tenantSlug provided, else find existing
    let tenantId: string | null = null;
    try {
      if (tenantSlug) {
        // Find or create tenant by slug. The create path + the later
        // "ensure engineTenantId is set" branch both touch
        // ``Tenant.engineTenantId`` which the bundled client doesn't
        // know about, so both go through raw SQL.
        let tenant = await prisma.tenant.findUnique({
          where: { slug: tenantSlug },
        });
        if (!tenant) {
          const newId = cuidIsh();
          const engineTenantId = process.env.ENGINE_ADMIN_TENANT_ID ?? null;
          await prisma.$executeRaw`
            INSERT INTO "Tenant" (id, name, slug, "engineTenantId", "createdAt", "updatedAt")
            VALUES (${newId}, ${tenantSlug}, ${tenantSlug}, ${engineTenantId}, NOW(), NOW())
          `;
          tenant = await prisma.tenant.findUnique({
            where: { id: newId },
          });
        }
        if (!tenant) {
          throw new Error("Failed to resolve tenant");
        }
        tenantId = tenant.id;

        // Backfill engineTenantId on existing tenants that were created
        // before the column was wired up.
        if (process.env.ENGINE_ADMIN_TENANT_ID) {
          const engineRows = await prisma.$queryRaw<
            { engineTenantId: string | null }[]
          >`SELECT "engineTenantId" FROM "Tenant" WHERE id = ${tenant.id} LIMIT 1`;
          if (!engineRows[0]?.engineTenantId) {
            await prisma.$executeRaw`
              UPDATE "Tenant" SET "engineTenantId" = ${process.env.ENGINE_ADMIN_TENANT_ID}
              WHERE id = ${tenant.id}
            `;
          }
        }

        // Upsert tenant membership with requested role.
        //
        // Our zod schema accepts OPERATOR + VIEWER in addition to
        // the bundled Pixie Dust ``TenantRole`` enum's three values;
        // the role string ends up in the database verbatim either
        // way, so cast through ``any`` to satisfy the narrower typed
        // surface while preserving the wider runtime accept-set.
        const memberRole = role ?? "MEMBER";
        const existing = await prisma.tenantUser.findUnique({
          where: { userId_tenantId: { userId: user.id, tenantId: tenant.id } },
        });
        if (existing) {
          if (existing.role !== memberRole) {
            await prisma.tenantUser.update({
              where: { id: existing.id },
              data: { role: memberRole as never },
            });
          }
        } else {
          await prisma.tenantUser.create({
            data: {
              userId: user.id,
              tenantId: tenant.id,
              role: memberRole as never,
            },
          });
        }
      } else {
        // No slug provided — find user's first existing membership
        const membership = await prisma.tenantUser.findFirst({
          where: { userId: user.id },
          select: { tenantId: true },
          orderBy: { joinedAt: "desc" },
        });
        if (membership) {
          tenantId = membership.tenantId;
        }
      }

      // Set impersonatingTenantId on the session so plugin routes have tenant context
      if (tenantId) {
        await prisma.$executeRaw`
          UPDATE "Session" SET "impersonatingTenantId" = ${tenantId}
          WHERE token = ${session.token}
        `;
      }
    } catch {
      // Column may not exist yet — skip silently
    }

    const cookieStore = await cookies();
    cookieStore.set(getCookieName(), session.token, {
      ...getCookieOptions(),
      secure: false,
    });

    return NextResponse.json({
      success: true,
      userId: user.id,
      sessionToken: session.token,
      expiresAt: session.expiresAt.toISOString(),
      tenantId,
    });
  } catch {
    return NextResponse.json(
      { error: "MCP backdoor authentication failed." },
      { status: 500 },
    );
  }
}

/** cuid-ish random id for rows we insert via raw SQL.
 *
 * Prisma's ``cuid()`` default only runs on typed ``.create()`` — when
 * we insert through ``$executeRaw`` we need to supply the id ourselves.
 */
function cuidIsh(): string {
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";
  let s = "c";
  for (const b of bytes) {
    // eslint-disable-next-line security/detect-object-injection
    s += alphabet[b % alphabet.length];
  }
  return s;
}
