export const dynamic = "force-dynamic";

import { prisma } from "@thinkneverland/pixie-dust-database";
import { NextResponse } from "next/server";

/**
 * GET /api/auth/branding
 *
 * Public endpoint — returns AppSettings branding fields for the login page.
 * No authentication required so the login page can show dynamic branding.
 */
export async function GET() {
  try {
    const settings = await prisma.appSettings.findUnique({
      where: { id: "singleton" },
      select: {
        brandName: true,
        brandLogoUrl: true,
        brandTagline: true,
        primaryColor: true,
        loginBgColor: true,
        loginHeading: true,
        loginSubheading: true,
      },
    });

    return NextResponse.json({
      brandName: settings?.brandName ?? "LintPDF",
      brandLogoUrl: settings?.brandLogoUrl ?? "/logo.png",
      brandTagline: settings?.brandTagline ?? "",
      primaryColor: settings?.primaryColor ?? null,
      loginBgColor: settings?.loginBgColor ?? null,
      loginHeading: settings?.loginHeading ?? null,
      loginSubheading: settings?.loginSubheading ?? null,
    });
  } catch {
    // Fallback to defaults if DB is unavailable
    return NextResponse.json({
      brandName: "LintPDF",
      brandLogoUrl: "/logo.png",
      brandTagline: "",
      primaryColor: null,
      loginBgColor: null,
      loginHeading: null,
      loginSubheading: null,
    });
  }
}
