export const dynamic = "force-dynamic";

import { requestMagicLink } from "@thinkneverland/pixie-dust-auth";
import {
  env,
  RATE_LIMIT_MAGIC_LINK_PER_EMAIL,
  RATE_LIMIT_WINDOW_HOURS,
} from "@thinkneverland/pixie-dust-config";
import { checkRateLimit } from "@thinkneverland/pixie-dust-core";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { sendMagicLinkEmail } from "@thinkneverland/pixie-dust-email";
import { NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z.object({
  email: z.string().email("Invalid email address."),
});

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const parsed = requestSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message ?? "Invalid input." },
        { status: 400 },
      );
    }

    const { email } = parsed.data;

    const emailRateLimit = checkRateLimit(`email:${email}`, {
      windowMs: RATE_LIMIT_WINDOW_HOURS * 60 * 60 * 1000,
      maxRequests: RATE_LIMIT_MAGIC_LINK_PER_EMAIL,
    });

    if (!emailRateLimit.allowed) {
      return NextResponse.json(
        { error: "Too many requests. Please try again later." },
        {
          status: 429,
          headers: {
            "Retry-After": String(
              Math.ceil((emailRateLimit.resetAt - Date.now()) / 1000),
            ),
          },
        },
      );
    }

    const result = await requestMagicLink(prisma, email, {
      withCode: true,
    });

    // Always return generic success to prevent email enumeration
    if ("error" in result) {
      return NextResponse.json({
        success: true,
        message:
          "If that email is in our system, you'll receive a sign-in link and code.",
      });
    }

    const magicLinkUrl = `${env.APP_URL}/api/auth/verify?token=${result.token}`;
    await sendMagicLinkEmail(email, magicLinkUrl, result.code);

    return NextResponse.json({
      success: true,
      pollingToken: result.pollingToken,
      message: "Check your email for a sign-in link and code.",
    });
  } catch (err) {
    console.error("[magic-link] Error:", err instanceof Error ? err.message : err);
    console.error("[magic-link] Stack:", err instanceof Error ? err.stack : "no stack");
    return NextResponse.json(
      { error: "Failed to send magic link. Please try again." },
      { status: 500 },
    );
  }
}
