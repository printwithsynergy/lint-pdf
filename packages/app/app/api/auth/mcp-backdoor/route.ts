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

const requestSchema = z.object({
  email: z.string().email(),
  mcpSecretKey: z.string().min(1),
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

    const { email, mcpSecretKey } = parsed.data;
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

    // Auto-set tenant context: find user's first tenant membership
    let tenantId: string | null = null;
    try {
      const membership = await prisma.tenantUser.findFirst({
        where: { userId: user.id },
        select: { tenantId: true },
        orderBy: { joinedAt: "desc" },
      });
      if (membership) {
        tenantId = membership.tenantId;
        // Set impersonatingTenantId on the session so plugin routes have tenant context
        await prisma.session.update({
          where: { token: session.token },
          data: { impersonatingTenantId: membership.tenantId },
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
