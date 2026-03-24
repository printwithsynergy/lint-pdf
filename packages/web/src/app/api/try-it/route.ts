import { NextResponse } from "next/server";

const ENGINE_URL = process.env.LINTPDF_ENGINE_URL ?? "http://localhost:8000";
const TRIAL_SECRET = process.env.LINTPDF_TRIAL_SECRET ?? "";

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
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";

  if (isRateLimited(ip)) {
    return NextResponse.json(
      { error: "Too many requests. Please try again later." },
      { status: 429 },
    );
  }

  if (!TRIAL_SECRET) {
    return NextResponse.json(
      { error: "Trial submissions are not configured." },
      { status: 503 },
    );
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  // Honeypot check
  const hpField = formData.get("_hp_field");
  if (hpField && String(hpField).length > 0) {
    // Silently accept to not tip off bots
    return NextResponse.json({ ok: true });
  }

  const name = String(formData.get("name") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();

  if (!name || !email) {
    return NextResponse.json(
      { error: "Name and email are required." },
      { status: 400 },
    );
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json(
      { error: "Invalid email address." },
      { status: 400 },
    );
  }

  const files = formData.getAll("files");
  if (!files.length) {
    return NextResponse.json(
      { error: "At least one PDF file is required." },
      { status: 400 },
    );
  }

  // Build FormData to forward to engine
  const engineForm = new FormData();
  engineForm.append("name", name);
  engineForm.append("email", email);
  engineForm.append("company", String(formData.get("company") ?? ""));
  engineForm.append("phone", String(formData.get("phone") ?? ""));
  for (const file of files) {
    engineForm.append("files", file);
  }

  try {
    const resp = await fetch(`${ENGINE_URL}/api/v1/trial/submit`, {
      method: "POST",
      headers: {
        "X-Trial-Secret": TRIAL_SECRET,
      },
      body: engineForm,
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      const detail = (data as { detail?: string }).detail;
      return NextResponse.json(
        { error: detail ?? "Failed to submit files. Please try again." },
        { status: resp.status >= 500 ? 500 : resp.status },
      );
    }

    const result = await resp.json();
    return NextResponse.json(result, { status: 201 });
  } catch {
    return NextResponse.json(
      { error: "Failed to submit files. Please try again." },
      { status: 500 },
    );
  }
}
