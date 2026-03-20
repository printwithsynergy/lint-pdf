import { NextResponse } from "next/server";
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

const CONTACT_TO = process.env.CONTACT_EMAIL ?? "hello@thinkneverland.com";
const FROM_ADDRESS = process.env.CONTACT_FROM ?? "LintPDF <noreply@thinkneverland.com>";

/** Simple time-window rate limit: max 3 submissions per IP per 10 minutes. */
const rateMap = new Map<string, number[]>();
const RATE_WINDOW = 10 * 60 * 1000;
const RATE_LIMIT = 3;

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const hits = (rateMap.get(ip) ?? []).filter((t) => now - t < RATE_WINDOW);
  if (hits.length >= RATE_LIMIT) return true;
  hits.push(now);
  rateMap.set(ip, hits);
  return false;
}

export async function POST(request: Request) {
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    "unknown";

  if (isRateLimited(ip)) {
    return NextResponse.json(
      { error: "Too many requests. Please try again later." },
      { status: 429 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  const { name, email, subject, message, _hp_field } = body as {
    name?: string;
    email?: string;
    subject?: string;
    message?: string;
    _hp_field?: string;
  };

  // Honeypot — bots fill hidden fields
  if (_hp_field) {
    // Silently accept to not tip off bots
    return NextResponse.json({ ok: true });
  }

  if (!email?.trim() || !message?.trim()) {
    return NextResponse.json(
      { error: "Email and message are required." },
      { status: 400 },
    );
  }

  // Basic email validation
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
    return NextResponse.json(
      { error: "Invalid email address." },
      { status: 400 },
    );
  }

  try {
    await resend.emails.send({
      from: FROM_ADDRESS,
      to: CONTACT_TO,
      replyTo: email.trim(),
      subject: `[LintPDF Contact] ${subject?.trim() || "General Inquiry"}`,
      text: [
        `Name: ${name?.trim() || "Not provided"}`,
        `Email: ${email.trim()}`,
        `Subject: ${subject?.trim() || "General Inquiry"}`,
        "",
        message.trim(),
      ].join("\n"),
    });

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json(
      { error: "Failed to send message. Please try again." },
      { status: 500 },
    );
  }
}
