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
// type doesn't expose them. Runtime columns are guaranteed by
// startup.sh. Cast through ``any`` to bridge the type gap.

const db = prisma as any;

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
        // Find or create tenant by slug
        let tenant = await prisma.tenant.findUnique({
          where: { slug: tenantSlug },
        });
        if (!tenant) {
          tenant = await db.tenant.create({
            data: {
              name: tenantSlug,
              slug: tenantSlug,
              engineTenantId: process.env.ENGINE_ADMIN_TENANT_ID ?? null,
            },
          });
        }
        if (!tenant) {
          // Defensive: create() always resolves to a row, but TS can't
          // narrow through the earlier findUnique chain without help.
          throw new Error("Failed to resolve tenant");
        }
        tenantId = tenant.id;

        // Ensure engineTenantId is set on existing tenants
        const tenantAny = tenant as { engineTenantId?: string | null; id: string };
        if (!tenantAny.engineTenantId && process.env.ENGINE_ADMIN_TENANT_ID) {
          await db.tenant.update({
            where: { id: tenantAny.id },
            data: { engineTenantId: process.env.ENGINE_ADMIN_TENANT_ID },
          });
        }

        // Upsert tenant membership with requested role
        const memberRole = role ?? "MEMBER";
        const existing = await prisma.tenantUser.findUnique({
          where: { userId_tenantId: { userId: user.id, tenantId: tenant.id } },
        });
        if (existing) {
          if (existing.role !== memberRole) {
            await db.tenantUser.update({
              where: { id: existing.id },
              data: { role: memberRole },
            });
          }
        } else {
          await db.tenantUser.create({
            data: {
              userId: user.id,
              tenantId: tenant.id,
              role: memberRole,
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
        await db.session.update({
          where: { token: session.token },
          data: { impersonatingTenantId: tenantId },
        });
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
