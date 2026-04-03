#!/usr/bin/env tsx

/**
 * Seed Lint PDF Branding
 * 
 * This script seeds the Lint PDF branding data into the database
 * using Pixie Dust's branding system with Lint PDF's blue and gray theme.
 */

import { updateBranding } from "@thinkneverland/pixie-dust-auth/server";
import { prisma } from "@thinkneverland/pixie-dust-database/server";

async function seedLintPdfBranding() {
  console.log("🎨 Seeding Lint PDF branding...");

  try {
    // Read the Lint PDF logo as base64
    const fs = await import("fs/promises");
    const path = await import("path");
    
    const logoPath = path.join(process.cwd(), "public", "logo.svg");
    
    let logoBase64: string | null = null;
    
    try {
      const logoBuffer = await fs.readFile(logoPath);
      logoBase64 = `data:image/svg+xml;base64,${logoBuffer.toString("base64")}`;
      console.log("✅ Loaded Lint PDF logo");
    } catch (err) {
      console.log("⚠️  Lint PDF logo not found, using fallback");
    }

    // Update branding with Lint PDF theme (blue and gray from logo)
    const branding = await updateBranding(prisma, {
      brandName: "Lint PDF",
      brandLogoUrl: logoBase64,
      brandTagline: "PDF preflight and annotation platform powered by Pixie Dust",
      primaryColor: "#4087F7", // Lint PDF bright blue from logo
      accentColor: "#93C5FD", // Lint PDF light blue accent from logo
      emailButtonColor: "#2563eb", // Medium blue
      loginBgColor: "#1e293b", // Dark blue-gray background
      loginCardColor: "#334155", // Card surface
      loginTextColor: "#f8fafc", // Light text
      loginInputColor: "#475569", // Input background
      loginRingColor: "#4087F7", // Blue focus ring
      loginBgColorDark: "#0f172a", // Even darker
      loginCardColorDark: "#1e293b", // Dark mode card
      loginTextColorDark: "#f1f5f9", // Dark mode text
      loginInputColorDark: "#334155", // Dark mode input
      loginRingColorDark: "#4087F7", // Keep blue focus ring
      sidebarBgColor: "#1e293b", // Dark sidebar
      sidebarTextColor: "#f8fafc", // Light sidebar text
      sidebarAccentColor: "#334155", // Sidebar accent
      loginHeading: "Welcome to Lint PDF",
      loginSubheading: "Professional PDF preflight and annotation tools.",
    });

    console.log("✅ Lint PDF branding seeded successfully!");
    console.log("📊 Branding data:", {
      brandName: branding.brandName,
      hasLogo: !!branding.brandLogoUrl,
      primaryColor: branding.primaryColor,
      accentColor: branding.accentColor,
    });

  } catch (error) {
    console.error("❌ Failed to seed Lint PDF branding:", error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  seedLintPdfBranding()
    .then(() => {
      console.log("🎉 Lint PDF branding seeding complete!");
      process.exit(0);
    })
    .catch((error) => {
      console.error("💥 Lint PDF seeding failed:", error);
      process.exit(1);
    });
}

export { seedLintPdfBranding };
