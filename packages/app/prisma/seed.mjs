/**
 * Production seed — ensures super admin and default tenants exist.
 * Runs on every deploy (uses upsert, safe to re-run).
 */

import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
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
  console.log(
    `Test customer: ${testCustomer.email} (id: ${testCustomer.id})`,
  );

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

  // ── App Settings (branding) ─────────────────────────────────
  const appSettings = await prisma.appSettings.upsert({
    where: { id: "singleton" },
    update: {},
    create: {
      id: "singleton",
      brandName: "LintPDF",
      brandLogoUrl: "/logo.svg",
      brandTagline: "Preflights you won't hate.",
    },
  });
  console.log(
    `App settings: brandName=${appSettings.brandName}, logo=${appSettings.brandLogoUrl}`,
  );

  console.log("Seed complete.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
