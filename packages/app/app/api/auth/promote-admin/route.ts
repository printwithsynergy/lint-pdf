export const dynamic = "force-dynamic";

import crypto from "node:crypto";

import { prisma } from "@thinkneverland/pixie-dust-database";
import { env } from "@thinkneverland/pixie-dust-config";
import { NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z.object({
  email: z.string().email(),
  mcpSecretKey: z.string().min(1),
});

/**
 * POST /api/auth/promote-admin
 *
 * Promotes a user to super admin. Requires MCP secret key.
 * This is a one-time setup endpoint for bootstrapping the first admin.
 */
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
        { error: "MCP not configured." },
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

    const user = await prisma.user.findUnique({ where: { email } });

    if (!user) {
      return NextResponse.json(
        {
          error: `User ${email} not found. Create them first via /api/auth/mcp-backdoor.`,
        },
        { status: 404 },
      );
    }

    const updated = await prisma.user.update({
      where: { email },
      data: { isSuperAdmin: true },
    });

    return NextResponse.json({
      success: true,
      userId: updated.id,
      email: updated.email,
      isSuperAdmin: updated.isSuperAdmin,
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to promote admin." },
      { status: 500 },
    );
  }
}
