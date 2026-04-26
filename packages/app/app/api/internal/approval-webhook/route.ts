export const dynamic = "force-dynamic";

import { createHmac, timingSafeEqual } from "node:crypto";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

import {
  PushNotConfiguredError,
  sendPushToTokens,
  type PushPayload,
} from "@/lib/push";

/**
 * Internal webhook receiver for the approval-step lifecycle. Fired
 * by the LintPDF engine for every tenant when both
 * `LINTPDF_INTERNAL_WEBHOOK_URL` and
 * `LINTPDF_INTERNAL_WEBHOOK_SECRET` are configured (see
 * `packages/engine/src/lintpdf/approvals/service.py:_fire_webhook`).
 *
 * Responsibilities:
 *   1. Verify the engine's HMAC-SHA256 signature against
 *      `LINTPDF_INTERNAL_WEBHOOK_SECRET`. Mismatches return 401 so
 *      a leaked URL alone isn't enough to fan out push payloads.
 *   2. For `approval.step.started` events, resolve the new
 *      step's approver email to the User row, then fan out to
 *      every `MobileDevice` registered under that (user, tenant)
 *      via firebase-admin.
 *   3. Prune `MobileDevice` rows whose `pushToken` FCM rejects as
 *      permanently invalid so the next fan-out doesn't waste
 *      requests on dead tokens.
 *
 * Other events (`approval.step.decided`, `approval.chain.cancelled`,
 * etc.) ack with 200 but don't trigger push — those are visible in
 * the admin dashboard rather than worth a phone vibration.
 */

interface ApprovalWebhookPayload {
  event: string;
  job_id: string;
  chain_id: string;
  template_id: string | null;
  step_index: number;
  step_name: string | null;
  status: string;
  decision: string | null;
  approver_email: string | null;
  notes: string | null;
  timestamp: string;
  viewer_url: string;
  tenant_id: string;
}

interface DeviceRow {
  id: string;
  pushToken: string;
}

interface UserRow {
  id: string;
}

function verifySignature(rawBody: string, header: string | null): boolean {
  const secret = process.env.LINTPDF_INTERNAL_WEBHOOK_SECRET;
  if (!secret || secret.length === 0) return false;
  if (!header) return false;
  // Engine emits `sha256=<hex>` to match the tenant-webhook header
  // shape — strip the prefix before comparing.
  const provided = header.startsWith("sha256=") ? header.slice(7) : header;
  const expected = createHmac("sha256", secret).update(rawBody).digest("hex");
  if (provided.length !== expected.length) return false;
  try {
    return timingSafeEqual(Buffer.from(provided), Buffer.from(expected));
  } catch {
    return false;
  }
}

export async function POST(req: Request) {
  const rawBody = await req.text();

  if (!verifySignature(rawBody, req.headers.get("x-lintpdf-signature"))) {
    return NextResponse.json(
      { error: "Invalid or missing signature." },
      { status: 401 },
    );
  }

  let payload: ApprovalWebhookPayload;
  try {
    payload = JSON.parse(rawBody) as ApprovalWebhookPayload;
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body." },
      { status: 400 },
    );
  }

  if (payload.event !== "approval.step.started") {
    // Non-push events still ack 200 so the engine doesn't retry.
    return NextResponse.json({ ok: true, skipped: payload.event });
  }

  if (!payload.approver_email || !payload.tenant_id) {
    return NextResponse.json(
      { ok: false, reason: "missing approver_email or tenant_id" },
      { status: 200 },
    );
  }

  // Pixie Dust's bundled Prisma client doesn't know about
  // MobileDevice (same constraint as in /api/mobile/devices) so
  // the lookup runs through $queryRaw. User is in the bundled
  // schema, so it stays on the typed client.
  const user = await prisma.user.findUnique({
    where: { email: payload.approver_email.toLowerCase() },
    select: { id: true },
  });

  if (!user) {
    // Approver isn't a LintPDF user — they got the email link but
    // aren't running the mobile app. Ack and move on.
    return NextResponse.json({
      ok: true,
      skipped: "approver_not_a_user",
    });
  }

  const devices = await prisma.$queryRaw<DeviceRow[]>`
    SELECT "id", "pushToken"
      FROM "MobileDevice"
     WHERE "userId" = ${(user as UserRow).id}
       AND "tenantId" = ${payload.tenant_id}
  `;

  if (devices.length === 0) {
    return NextResponse.json({ ok: true, skipped: "no_devices" });
  }

  const pushPayload: PushPayload = buildPayload(payload);

  let results;
  try {
    results = await sendPushToTokens(
      devices.map((d) => d.pushToken),
      pushPayload,
    );
  } catch (err) {
    if (err instanceof PushNotConfiguredError) {
      return NextResponse.json(
        { ok: false, error: "push_not_configured" },
        { status: 503 },
      );
    }
    throw err;
  }

  // Prune rows whose tokens FCM said are permanently invalid so
  // the next event doesn't waste a request on them.
  const invalidTokens = results
    .filter((r) => !r.ok && r.invalid)
    .map((r) => r.pushToken);
  if (invalidTokens.length > 0) {
    await prisma.$executeRaw`
      DELETE FROM "MobileDevice"
       WHERE "pushToken" = ANY(${invalidTokens}::text[])
    `;
  }

  const sent = results.filter((r) => r.ok).length;
  const failed = results.filter((r) => !r.ok && !r.invalid).length;
  const pruned = invalidTokens.length;

  return NextResponse.json({ ok: true, sent, failed, pruned });
}

function buildPayload(p: ApprovalWebhookPayload): PushPayload {
  const stepLabel = p.step_name ?? `Step ${p.step_index + 1}`;
  return {
    title: "Approval needed",
    body: `${stepLabel} is waiting for your decision.`,
    // The mobile shell routes notification taps to this path. The
    // `viewer_url` from the engine is the absolute web URL — strip
    // the origin so the in-app router gets the same path universal
    // links would deliver on a cold launch.
    linkPath: viewerPathFromUrl(p.viewer_url) ?? "/",
    data: {
      event: p.event,
      jobId: p.job_id,
      chainId: p.chain_id,
      tenantId: p.tenant_id,
    },
  };
}

function viewerPathFromUrl(url: string): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return null;
  }
}
