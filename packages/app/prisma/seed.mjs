/**
 * Production seed — ensures super admin and default tenants exist.
 * Runs on every deploy (uses upsert, safe to re-run).
 */

import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";

// Prisma 7 requires an explicit driver adapter — the bare
// `new PrismaClient()` call throws PrismaClientInitializationError
// ("needs to be constructed with a non-empty, valid PrismaClientOptions")
// on the first db call. Wire up the pg adapter with DATABASE_URL.
const adapter = new PrismaPg({
  connectionString: process.env.DATABASE_URL,
});
const prisma = new PrismaClient({ adapter });

async function main() {
  // Ensure engineTenantId column exists (prisma db push may skip it
  // when engine tables trigger data-loss warnings)
  try {
    await prisma.$executeRawUnsafe(
      `ALTER TABLE "Tenant" ADD COLUMN IF NOT EXISTS "engineTenantId" TEXT`,
    );
    console.log("Ensured engineTenantId column exists.");
  } catch (e) {
    console.log("engineTenantId column check:", e.message ?? String(e));
  }

  // Upsert super admin user
  const superAdmin = await prisma.user.upsert({
    where: { email: "quincy@thinkneverland.com" },
    update: { isSuperAdmin: true },
    create: {
      email: "quincy@thinkneverland.com",
      name: "Quincy",
      isSuperAdmin: true,
    },
  });
  console.log(
    `Super admin: ${superAdmin.email} (id: ${superAdmin.id}, isSuperAdmin: ${superAdmin.isSuperAdmin})`,
  );

  // Ensure a tenant exists for the super admin
  const existingMembership = await prisma.tenantUser.findFirst({
    where: { userId: superAdmin.id },
    include: { tenant: true },
  });

  if (existingMembership) {
    console.log(
      `Already has tenant: ${existingMembership.tenant.name} (${existingMembership.tenant.id})`,
    );
    // Ensure engineTenantId is set
    if (
      !existingMembership.tenant.engineTenantId &&
      process.env.ENGINE_ADMIN_TENANT_ID
    ) {
      await prisma.tenant.update({
        where: { id: existingMembership.tenant.id },
        data: { engineTenantId: process.env.ENGINE_ADMIN_TENANT_ID },
      });
      console.log(
        `  Linked to engine tenant: ${process.env.ENGINE_ADMIN_TENANT_ID}`,
      );
    }
  } else {
    const tenant = await prisma.tenant.create({
      data: {
        name: "ThinkNeverland",
        slug: "thinkneverland",
        engineTenantId: process.env.ENGINE_ADMIN_TENANT_ID ?? null,
        users: {
          create: {
            userId: superAdmin.id,
            role: "OWNER",
          },
        },
      },
    });
    console.log(`Created tenant: ${tenant.name} (${tenant.id})`);
  }

  // ── MCP Backdoor Admin (if MCP_BACKDOOR is enabled) ──────────
  if (process.env.MCP_BACKDOOR === "true") {
    const mcpEmail = "admin@lintpdf.com";
    const mcpAdmin = await prisma.user.upsert({
      where: { email: mcpEmail },
      update: { isSuperAdmin: true },
      create: {
        email: mcpEmail,
        name: "MCP Test User (admin@lintpdf.com)",
        isSuperAdmin: true,
      },
    });
    console.log(
      `MCP admin: ${mcpAdmin.email} (id: ${mcpAdmin.id}, isSuperAdmin: ${mcpAdmin.isSuperAdmin})`,
    );

    const mcpMembership = await prisma.tenantUser.findFirst({
      where: { userId: mcpAdmin.id },
    });
    if (!mcpMembership) {
      // Find the ThinkNeverland tenant or create one
      const adminTenant = await prisma.tenant.findFirst({
        where: { slug: "thinkneverland" },
      });
      if (adminTenant) {
        await prisma.tenantUser.create({
          data: {
            userId: mcpAdmin.id,
            tenantId: adminTenant.id,
            role: "OWNER",
          },
        });
        console.log(`  Added MCP admin to tenant: ${adminTenant.name}`);
      }
    } else {
      console.log(`  MCP admin already has tenant membership`);
    }
  }

  // ── Test Customer ──────────────────────────────────────────
  const testCustomer = await prisma.user.upsert({
    where: { email: "testcustomer@lintpdf.com" },
    update: {},
    create: {
      email: "testcustomer@lintpdf.com",
      name: "Test Customer",
      isSuperAdmin: false,
    },
  });
  console.log(`Test customer: ${testCustomer.email} (id: ${testCustomer.id})`);

  const customerMembership = await prisma.tenantUser.findFirst({
    where: { userId: testCustomer.id },
    include: { tenant: true },
  });

  if (customerMembership) {
    console.log(
      `Already has tenant: ${customerMembership.tenant.name} (${customerMembership.tenant.id})`,
    );
  } else {
    const customerTenant = await prisma.tenant.create({
      data: {
        name: "Test Customer Org",
        slug: "test-customer",
        users: {
          create: {
            userId: testCustomer.id,
            role: "OWNER",
          },
        },
      },
    });
    console.log(
      `Created tenant: ${customerTenant.name} (${customerTenant.id})`,
    );
  }

  // ── Print With Synergy (PWS) demo tenant ───────────────────
  // Quincy needs a non-super-admin account so he can exercise the
  // tenant-facing UI without seeing the Admin section. PWS is the
  // reference "demo tenant" for LintPDF sales walkthroughs. Kept in
  // sync with seed.ts — if you update one, update both (startup.sh
  // runs seed.mjs on every deploy; prisma db seed runs seed.ts).
  const pwsAdmin = await prisma.user.upsert({
    where: { email: "quincy@printwithsynergy.com" },
    update: {},
    create: {
      email: "quincy@printwithsynergy.com",
      name: "Quincy (PWS)",
      isSuperAdmin: false,
    },
  });
  console.log(`PWS admin: ${pwsAdmin.email} (id: ${pwsAdmin.id})`);

  const pwsTenant = await prisma.tenant.upsert({
    where: { slug: "print-with-synergy" },
    update: {},
    create: {
      name: "Print With Synergy",
      slug: "print-with-synergy",
      engineTenantId: "df520bc7-fc77-44cf-a275-c756fbbfb618",
    },
  });
  console.log(`PWS tenant: ${pwsTenant.name} (${pwsTenant.id})`);

  const pwsMembership = await prisma.tenantUser.findUnique({
    where: {
      userId_tenantId: { userId: pwsAdmin.id, tenantId: pwsTenant.id },
    },
  });
  if (!pwsMembership) {
    await prisma.tenantUser.create({
      data: {
        userId: pwsAdmin.id,
        tenantId: pwsTenant.id,
        role: "ADMIN",
      },
    });
    console.log(`Linked ${pwsAdmin.email} as ADMIN of ${pwsTenant.name}`);
  } else {
    console.log(
      `${pwsAdmin.email} already a member of ${pwsTenant.name} (${pwsMembership.role})`,
    );
  }

  // ── App Settings (branding) ─────────────────────────────────
  // Full branding matching the marketing site and Pixie Dust theme
  const brandingData = {
    brandName: "LintPDF",
    brandLogoUrl: "/logo.svg",
    brandLogoUrlDark: "/logo.svg",
    brandTagline: "Preflights you won't hate.",
    primaryColor: "#1e40af",
    accentColor: "#2563eb",
    emailButtonColor: "#2563eb",
    // Light-mode login
    loginBgColor: "#ffffff",
    loginCardColor: "#f7f9fb",
    loginTextColor: "#020817",
    loginInputColor: "#f0f4f8",
    loginRingColor: "#1e40af",
    // Dark-mode login
    loginBgColorDark: "#080a0f",
    loginCardColorDark: "#1a1b24",
    loginTextColorDark: "#f0f0f5",
    loginInputColorDark: "#0f1019",
    loginRingColorDark: "#1e40af",
    // Sidebar
    sidebarBgColor: "#f5f6f8",
    sidebarTextColor: "#111621",
    sidebarAccentColor: "#eaedef",
    // Favicon & copy
    faviconUrl: "/favicon.svg",
    loginHeading: "Sign in to LintPDF",
    loginSubheading: "Enter your email for a magic link",
  };
  const appSettings = await prisma.appSettings.upsert({
    where: { id: "singleton" },
    update: brandingData,
    create: { id: "singleton", ...brandingData },
  });
  console.log(
    `App settings: brandName=${appSettings.brandName}, logo=${appSettings.brandLogoUrl}, primaryColor=${appSettings.primaryColor}`,
  );

  console.log("Seed complete.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
