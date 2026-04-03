export const dynamic = "force-dynamic";

import crypto from "node:crypto";

import { createSession } from "@thinkneverland/pixie-dust-auth";
import {
  getCookieName,
  getCookieOptions,
  env,
} from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/lintpdf-database";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z.object({
  email: z.string().email(),
  mcpSecretKey: z.string().min(1),
  name: z.string().optional(),
  isSuperAdmin: z.boolean().optional(),
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

    const { email, mcpSecretKey, name, isSuperAdmin } = parsed.data;
    const mcpKey = env.MCP_SECRET_KEY;

    if (!mcpKey) {
      return NextResponse.json({ error: "Invalid MCP secret key." }, { status: 403 });
    }

    if (
      mcpSecretKey.length !== mcpKey.length ||
      !crypto.timingSafeEqual(Buffer.from(mcpSecretKey), Buffer.from(mcpKey))
    ) {
      return NextResponse.json({ error: "Invalid MCP secret key." }, { status: 403 });
    }

    let user = await prisma.user.findUnique({ where: { email } });

    if (!user) {
      user = await prisma.user.create({
        data: { email, name: name ?? `MCP Test User (${email})`, isSuperAdmin: isSuperAdmin ?? false },
      });
    } else {
      const updates: Record<string, unknown> = {};
      if (name !== undefined) updates.name = name;
      if (isSuperAdmin !== undefined) updates.isSuperAdmin = isSuperAdmin;
      if (Object.keys(updates).length > 0) {
        user = await prisma.user.update({ where: { id: user.id }, data: updates });
      }
    }

    const ipAddress = req.headers.get("x-forwarded-for") ?? undefined;
    const userAgent = "MCP-Backdoor-Test";

    const session = await createSession(prisma, user.id, { ipAddress, userAgent });

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
      isSuperAdmin: user.isSuperAdmin,
    });
  } catch {
    return NextResponse.json(
      { error: "MCP backdoor authentication failed." },
      { status: 500 },
    );
  }
}
