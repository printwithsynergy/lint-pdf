export const dynamic = "force-dynamic";

import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";
import { z } from "zod";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const requestSchema = z.object({
  email: z.string().email("Invalid email address."),
  name: z.string().nullish(),
  company: z.string().nullish(),
  useCase: z.string().nullish(),
});

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const parsed = requestSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message ?? "Invalid input." },
        { status: 400, headers: corsHeaders },
      );
    }

    const { email, name, company, useCase } = parsed.data;

    // Check for existing entry
    const existing = await prisma.waitlistEntry.findUnique({
      where: { email },
    });

    if (existing) {
      return NextResponse.json(
        { status: "already_on_waitlist" },
        { status: 200, headers: corsHeaders },
      );
    }

    const entry = await prisma.waitlistEntry.create({
      data: {
        email,
        name: name ?? undefined,
        company: company ?? undefined,
        useCase: useCase ?? undefined,
      },
    });

    return NextResponse.json(
      { id: entry.id },
      { status: 201, headers: corsHeaders },
    );
  } catch (err) {
    // Handle race condition: unique constraint violation on concurrent insert
    if (
      err instanceof Error &&
      "code" in err &&
      (err as { code: string }).code === "P2002"
    ) {
      return NextResponse.json(
        { status: "already_on_waitlist" },
        { status: 200, headers: corsHeaders },
      );
    }

    console.error(
      "[waitlist] Error:",
      err instanceof Error ? err.message : err,
    );
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500, headers: corsHeaders },
    );
  }
}
