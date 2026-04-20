/**
 * Global setup for E2E tests.
 *
 * 1. Optionally enables MCP_BACKDOOR on Railway via GraphQL API
 * 2. Creates test users for every role
 * 3. Promotes the super-admin user
 * 4. Creates a test tenant and assigns roles
 * 5. Generates engine API keys and persists them
 */
import "../proxy-setup";
import { request as pwRequest } from "@playwright/test";
import { writeFileSync } from "fs";
import { resolve } from "path";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";
const ENGINE_BASE = process.env.ENGINE_BASE_URL ?? "https://engine.lintpdf.com";
const MCP_SECRET_KEY = process.env.MCP_SECRET_KEY ?? "";
const RAILWAY_TOKEN = process.env.RAILWAY_TOKEN ?? "";
const RAILWAY_PROJECT_ID = process.env.RAILWAY_LINTPDF ?? "5da33de4-8f03-4700-baa6-69a72518b52d";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "";
const RAW_PROXY = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || "";

function parseProxy(url: string) {
  if (!url) return undefined;
  try {
    const u = new URL(url);
    return {
      server: `${u.protocol}//${u.hostname}:${u.port}`,
      username: decodeURIComponent(u.username) || undefined,
      password: decodeURIComponent(u.password) || undefined,
    };
  } catch {
    return { server: url };
  }
}
const PROXY = parseProxy(RAW_PROXY);

const STATE_FILE = resolve(__dirname, "../.test-state.json");

export interface TestState {
  tenantId: string;
  tenantSlug: string;
  engineTenantId: string;
  engineApiKey: string;
  adminApiKey: string;
  users: Record<string, { email: string; userId: string; sessionToken: string }>;
}

// ---------- Railway helpers ----------

async function enableMcpBackdoor(): Promise<void> {
  if (!RAILWAY_TOKEN) {
    console.log("⏭ No RAILWAY_TOKEN — skipping Railway MCP toggle");
    return;
  }

  console.log("🚂 Enabling MCP_BACKDOOR on Railway...");

  // First get the app service ID
  const listRes = await fetch("https://backboard.railway.com/graphql/v2", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${RAILWAY_TOKEN}`,
    },
    body: JSON.stringify({
      query: `query { project(id: "${RAILWAY_PROJECT_ID}") { services { edges { node { id name } } } } }`,
    }),
  });

  const listData = await listRes.json();
  const services = listData?.data?.project?.services?.edges ?? [];
  const appService = services.find(
    (e: any) => e.node.name === "app" || e.node.name.toLowerCase().includes("app"),
  );

  if (!appService) {
    console.log("⚠️ Could not find app service on Railway. Available:", services.map((e: any) => e.node.name));
    return;
  }

  const serviceId = appService.node.id;
  console.log(`  Found app service: ${appService.node.name} (${serviceId})`);

  // Get environments
  const envRes = await fetch("https://backboard.railway.com/graphql/v2", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${RAILWAY_TOKEN}`,
    },
    body: JSON.stringify({
      query: `query { project(id: "${RAILWAY_PROJECT_ID}") { environments { edges { node { id name } } } } }`,
    }),
  });

  const envData = await envRes.json();
  const envs = envData?.data?.project?.environments?.edges ?? [];
  const prodEnv = envs.find(
    (e: any) => e.node.name === "production" || e.node.name === "main",
  );

  if (!prodEnv) {
    console.log("⚠️ Could not find production environment. Available:", envs.map((e: any) => e.node.name));
    return;
  }

  const envId = prodEnv.node.id;

  // Set env vars
  const mcpKey = MCP_SECRET_KEY || "e2e-mcp-secret-key-minimum-32-characters-long!!";

  const upsertRes = await fetch("https://backboard.railway.com/graphql/v2", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${RAILWAY_TOKEN}`,
    },
    body: JSON.stringify({
      query: `mutation {
        a: variableUpsert(input: { projectId: "${RAILWAY_PROJECT_ID}", environmentId: "${envId}", serviceId: "${serviceId}", name: "MCP_BACKDOOR", value: "true" })
        b: variableUpsert(input: { projectId: "${RAILWAY_PROJECT_ID}", environmentId: "${envId}", serviceId: "${serviceId}", name: "MCP_SECRET_KEY", value: "${mcpKey}" })
      }`,
    }),
  });

  const upsertData = await upsertRes.json();
  if (upsertData.errors) {
    console.log("⚠️ Railway variable upsert errors:", JSON.stringify(upsertData.errors));
    return;
  }

  console.log("  ✅ MCP_BACKDOOR + MCP_SECRET_KEY set. Waiting for redeploy...");

  // Poll health endpoint until the app is back
  const start = Date.now();
  const maxWait = 180_000; // 3 minutes
  while (Date.now() - start < maxWait) {
    try {
      const healthRes = await fetch(`${APP_BASE}/api/health`, { signal: AbortSignal.timeout(5000) });
      if (healthRes.ok) {
        // Check if MCP backdoor is now active by probing it
        const probeRes = await fetch(`${APP_BASE}/api/auth/mcp-backdoor`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: "probe@test.io", mcpSecretKey: "probe" }),
        });
        // 400 or 403 means it's enabled (just wrong creds), 404 means not yet
        if (probeRes.status !== 404) {
          console.log("  ✅ MCP backdoor is active!");
          // Set env for this process
          process.env.MCP_SECRET_KEY = mcpKey;
          return;
        }
      }
    } catch {
      // still deploying
    }
    await new Promise((r) => setTimeout(r, 5000));
  }

  console.log("⚠️ Timed out waiting for Railway redeploy");
}

// ---------- Auth helpers ----------

async function mcpAuth(
  ctx: Awaited<ReturnType<typeof pwRequest.newContext>>,
  email: string,
  options?: { tenantSlug?: string; role?: string },
): Promise<{ userId: string; sessionToken: string; tenantId?: string }> {
  const key = process.env.MCP_SECRET_KEY ?? MCP_SECRET_KEY;

  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await ctx.post(`${APP_BASE}/api/auth/mcp-backdoor`, {
      data: {
        email,
        mcpSecretKey: key,
        ...(options?.tenantSlug ? { tenantSlug: options.tenantSlug } : {}),
        ...(options?.role ? { role: options.role } : {}),
      },
    });

    if (res.ok()) {
      const data = await res.json();
      return { userId: data.userId, sessionToken: data.sessionToken, tenantId: data.tenantId };
    }

    if (res.status() === 429 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 3000 * (attempt + 1)));
      continue;
    }

    const body = await res.text();
    throw new Error(`MCP auth failed for ${email} (${res.status()}): ${body}`);
  }

  throw new Error(`MCP auth failed for ${email} after retries`);
}

async function promoteAdmin(
  ctx: Awaited<ReturnType<typeof pwRequest.newContext>>,
  email: string,
): Promise<void> {
  const key = process.env.MCP_SECRET_KEY ?? MCP_SECRET_KEY;
  const res = await ctx.post(`${APP_BASE}/api/auth/promote-admin`, {
    data: { email, mcpSecretKey: key },
  });

  if (!res.ok()) {
    const body = await res.text();
    console.log(`  ⚠️ promote-admin for ${email}: ${res.status()} ${body}`);
  }
}

// ---------- Main setup ----------

async function globalSetup() {
  console.log("\n🔧 E2E Global Setup\n");

  // Step 0: Enable MCP backdoor on Railway
  await enableMcpBackdoor();

  const ctx = await pwRequest.newContext({ baseURL: APP_BASE, ignoreHTTPSErrors: true, ...(PROXY ? { proxy: PROXY } : {}) });

  let tenantSlug = "e2e-test-org";
  let tenantId = "";
  let engineTenantId = "";
  let engineApiKey = "";

  const users: TestState["users"] = {};
  const emails: Record<string, string> = {
    "super-admin": "super-admin@e2e.lintpdf.com",
    owner: "owner@e2e.lintpdf.com",
    admin: "admin@e2e.lintpdf.com",
    operator: "operator@e2e.lintpdf.com",
    member: "member@e2e.lintpdf.com",
    viewer: "viewer@e2e.lintpdf.com",
  };

  const roleMap: Record<string, string> = {
    "super-admin": "OWNER",
    owner: "OWNER",
    admin: "ADMIN",
    operator: "OPERATOR",
    member: "MEMBER",
    viewer: "VIEWER",
  };

  // Step 1: Create all users via MCP backdoor with tenant + role
  console.log("👤 Creating test users with tenant memberships...");
  for (const [role, email] of Object.entries(emails)) {
    try {
      const auth = await mcpAuth(ctx, email, {
        tenantSlug: tenantSlug,
        // role comes from Object.entries of the local emails record — typed lookup.
        // eslint-disable-next-line security/detect-object-injection
        role: roleMap[role] ?? "MEMBER",
      });
      // eslint-disable-next-line security/detect-object-injection
      users[role] = { email, ...auth };
      console.log(`  ✅ ${role}: ${email} (${auth.userId}) tenant=${auth.tenantId ?? "none"}`);
    } catch (err) {
      console.log(`  ❌ ${role}: ${err}`);
    }
  }

  // Get tenantId from any user's auth result
  for (const user of Object.values(users)) {
    if ((user as any).tenantId) {
      tenantId = (user as any).tenantId;
      break;
    }
  }
  if (tenantId) {
    console.log(`  🏢 Tenant: ${tenantSlug} (${tenantId})`);
  }

  // Step 2: Promote super-admin
  if (users["super-admin"]) {
    const superAdminEmail = emails["super-admin"];
    if (superAdminEmail) {
      console.log("👑 Promoting super admin...");
      await promoteAdmin(ctx, superAdminEmail);
    }
  }

  // Step 3: Tenant already created by MCP backdoor in Step 1 — get the ID
  // The MCP backdoor creates the tenant and memberships automatically

  if (users["super-admin"]) {
    // Use tRPC to create tenant
    console.log("🏢 Creating test tenant...");
    try {
      const createCtx = await pwRequest.newContext({
        baseURL: APP_BASE,
        ignoreHTTPSErrors: true,
        ...(PROXY ? { proxy: PROXY } : {}),
        extraHTTPHeaders: {
          Cookie: `pixie-dust-session=${users["super-admin"].sessionToken}`,
        },
      });

      // Try tRPC tenant.create
      const createRes = await createCtx.post("/api/trpc/tenant.create", {
        data: { json: { name: "E2E Test Org", slug: tenantSlug } },
      });

      if (createRes.ok()) {
        const createData = await createRes.json();
        tenantId = createData?.result?.data?.json?.id ?? "";
        tenantSlug = createData?.result?.data?.json?.slug ?? tenantSlug;
        console.log(`  ✅ Tenant: ${tenantSlug} (${tenantId})`);
      } else {
        // Tenant may already exist — try listing
        const listRes = await createCtx.fetch(`${APP_BASE}/api/auth/me`);
        if (listRes.ok()) {
          const meData = await listRes.json();
          const membership = meData?.tenantMemberships?.find(
            (m: any) => m.tenant?.slug === tenantSlug,
          );
          if (membership) {
            tenantId = membership.tenant.id;
            console.log(`  ℹ️ Tenant already exists: ${tenantSlug} (${tenantId})`);
          }
        }
      }

      await createCtx.dispose();
    } catch (err) {
      console.log(`  ❌ Tenant creation: ${err}`);
    }
  }

  // Step 4: Roles assigned in Step 1 via MCP backdoor (tenantSlug + role params)
  console.log("🎭 Roles assigned via MCP backdoor in Step 1");

  // Step 5: Provision engine-side tenant + API key.
  //
  // The engine (SQLAlchemy, UUID tenant IDs) and app (Prisma, CUID tenant
  // IDs) live in the same database but use separate tables. We can't pass
  // the Prisma CUID to the engine — it expects UUIDs and rejects anything
  // else with ``Invalid UUID.``. Instead, find-or-create a dedicated
  // engine-side tenant for E2E tests and store its UUID + raw key so
  // engine-direct tests can hit /api/v1 endpoints.
  if (ADMIN_API_KEY) {
    console.log("🔑 Provisioning engine-side tenant + API key...");
    const E2E_ENGINE_TENANT_NAME = "E2E Test Engine";
    try {
      // Try to find an existing engine tenant with our known name so we
      // don't create a new one on every run.
      const listRes = await ctx.get(`${ENGINE_BASE}/api/v1/admin/tenants`, {
        headers: { "X-Admin-Key": ADMIN_API_KEY },
      });
      if (listRes.ok()) {
        const listData = await listRes.json();
        const existing = (listData?.tenants ?? []).find(
          (t: any) => t.name === E2E_ENGINE_TENANT_NAME,
        );
        if (existing) {
          engineTenantId = existing.id;
          console.log(`  ℹ️ Found engine tenant: ${engineTenantId}`);
        }
      } else {
        console.log(`  ⚠️ List tenants failed: ${listRes.status()}`);
      }

      // If none exists, create one. ``POST /api/v1/admin/tenants`` returns
      // the raw api_key in its response — the only time we ever see it.
      if (!engineTenantId) {
        const createRes = await ctx.post(`${ENGINE_BASE}/api/v1/admin/tenants`, {
          headers: { "X-Admin-Key": ADMIN_API_KEY },
          data: {
            name: E2E_ENGINE_TENANT_NAME,
            contact_email: "e2e@lintpdf.com",
            plan: "enterprise",
          },
        });
        if (createRes.ok()) {
          const createData = await createRes.json();
          engineTenantId = createData.id ?? "";
          engineApiKey = createData.api_key ?? "";
          console.log(`  ✅ Created engine tenant ${engineTenantId} + key`);
        } else {
          console.log(
            `  ⚠️ Create engine tenant failed: ${createRes.status()} ${await createRes.text()}`,
          );
        }
      }

      // For an existing tenant we don't have the raw key, so issue a
      // fresh one via ``POST /tenants/:id/keys``. Note: that endpoint
      // returns ``raw_key`` (not ``api_key`` like the tenant-create
      // endpoint does) — see ApiKeyCreateResponse in admin.py.
      if (engineTenantId && !engineApiKey) {
        const keyRes = await ctx.post(
          `${ENGINE_BASE}/api/v1/admin/tenants/${engineTenantId}/keys`,
          {
            headers: { "X-Admin-Key": ADMIN_API_KEY },
            data: { label: "e2e-test-key" },
          },
        );
        if (keyRes.ok()) {
          const keyData = await keyRes.json();
          engineApiKey =
            keyData.raw_key ?? keyData.api_key ?? keyData.key ?? "";
          console.log(`  ✅ Engine API key issued for existing tenant`);
        } else {
          console.log(
            `  ⚠️ Key creation failed: ${keyRes.status()} ${await keyRes.text()}`,
          );
        }
      }

      // Enable AI features for the E2E test tenant so the AI-focused
      // specs (ai-review interpret, ai-profile-generation,
      // ai-features, ai-presets-coverage, etc.) actually exercise the
      // AI pipeline instead of being silently gated out by the
      // entitlement check. This is idempotent — calling PUT /ai with
      // ai_enabled=true on an already-enabled tenant is a no-op.
      if (engineTenantId) {
        const aiRes = await ctx.fetch(
          `${ENGINE_BASE}/api/v1/admin/tenants/${engineTenantId}/ai?ai_enabled=true`,
          {
            method: "PUT",
            headers: { "X-Admin-Key": ADMIN_API_KEY },
          },
        );
        if (aiRes.ok()) {
          console.log(`  ✅ AI features enabled for engine tenant`);
        } else {
          console.log(
            `  ⚠️ AI enable failed: ${aiRes.status()} ${await aiRes.text()}`,
          );
        }

        // Grant a generous credit allowance so AI-gated tests never
        // fail for lack of credits. 100k credits covers thousands of
        // AI calls — plenty for a single test run.
        const creditsRes = await ctx.post(
          `${ENGINE_BASE}/api/v1/admin/tenants/${engineTenantId}/ai/credits?credit_amount=100000&price_paid=0`,
          { headers: { "X-Admin-Key": ADMIN_API_KEY } },
        );
        if (creditsRes.ok()) {
          console.log(`  ✅ AI credits granted`);
        } else {
          console.log(
            `  ⚠️ AI credit grant failed: ${creditsRes.status()} ${await creditsRes.text()}`,
          );
        }
      }
    } catch (err) {
      console.log(`  ⚠️ Engine provisioning: ${err}`);
    }
  } else {
    console.log("⏭ No ADMIN_API_KEY — skipping engine tenant provisioning");
  }

  // Persist state
  const state: TestState = {
    tenantId,
    tenantSlug,
    engineTenantId,
    engineApiKey,
    adminApiKey: ADMIN_API_KEY,
    users,
  };

  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  console.log(`\n📁 Test state saved to ${STATE_FILE}`);
  console.log("✅ Global setup complete\n");

  await ctx.dispose();
}

export default globalSetup;
