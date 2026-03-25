import { getCookieName } from "@thinkneverland/pixie-dust-config";

/**
 * Extract the session token from the raw cookie header string.
 */
export function parseSessionCookie(
  cookieHeader: string | null,
): string | undefined {
  if (!cookieHeader) return undefined;
  const cookieName = getCookieName();
  const cookies = cookieHeader.split(";").map((c) => c.trim());
  return cookies
    .find((c) => c.startsWith(`${cookieName}=`))
    ?.split("=")[1];
}

/**
 * Extract client IP address and user-agent from a request.
 */
export function getClientInfo(req: Request): {
  ipAddress: string | undefined;
  userAgent: string | undefined;
} {
  const ipAddress =
    req.headers.get("x-forwarded-for") ??
    req.headers.get("x-real-ip") ??
    undefined;
  const userAgent = req.headers.get("user-agent") ?? undefined;
  return { ipAddress, userAgent };
}
