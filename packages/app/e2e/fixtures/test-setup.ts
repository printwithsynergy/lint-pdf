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
): Promise<{ userId: string; sessionToken: string }> {
  const key = process.env.MCP_SECRET_KEY ?? MCP_SECRET_KEY;

  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await ctx.post(`${APP_BASE}/api/auth/mcp-backdoor`, {
      data: { email, mcpSecretKey: key },
    });

    if (res.ok()) {
      const data = await res.json();
      return { userId: data.userId, sessionToken: data.sessionToken };
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

  const users: TestState["users"] = {};
  const emails: Record<string, string> = {
    "super-admin": "super-admin@e2e.lintpdf.com",
    owner: "owner@e2e.lintpdf.com",
    admin: "admin@e2e.lintpdf.com",
    operator: "operator@e2e.lintpdf.com",
    member: "member@e2e.lintpdf.com",
    viewer: "viewer@e2e.lintpdf.com",
  };

  // Step 1: Create all users via MCP backdoor
  console.log("👤 Creating test users...");
  for (const [role, email] of Object.entries(emails)) {
    try {
      const auth = await mcpAuth(ctx, email);
      users[role] = { email, ...auth };
      console.log(`  ✅ ${role}: ${email} (${auth.userId})`);
    } catch (err) {
      console.log(`  ❌ ${role}: ${err}`);
    }
  }

  // Step 2: Promote super-admin
  if (users["super-admin"]) {
    console.log("👑 Promoting super admin...");
    await promoteAdmin(ctx, emails["super-admin"]);
  }

  // Step 3: Create test tenant via super admin session
  let tenantId = "";
  let tenantSlug = "e2e-test-org";
  let engineApiKey = "";

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

  // Step 4: Assign roles to users for the test tenant
  if (tenantId && users["super-admin"]) {
    console.log("🎭 Assigning tenant roles...");
    const adminCtx = await pwRequest.newContext({
      baseURL: APP_BASE,
      ignoreHTTPSErrors: true,
      ...(PROXY ? { proxy: PROXY } : {}),
      extraHTTPHeaders: {
        Cookie: `pixie-dust-session=${users["super-admin"].sessionToken}`,
      },
    });

    const roleMap: Record<string, string> = {
      owner: "OWNER",
      admin: "ADMIN",
      operator: "OPERATOR",
      member: "MEMBER",
      viewer: "VIEWER",
    };

    for (const [roleName, roleValue] of Object.entries(roleMap)) {
      if (!users[roleName]) continue;
      try {
        // Invite user via tRPC or direct API
        const inviteRes = await adminCtx.post("/api/trpc/tenant.invite", {
          data: {
            json: {
              tenantId,
              email: users[roleName].email,
              role: roleValue,
            },
          },
        });
        if (inviteRes.ok()) {
          console.log(`  ✅ ${roleName} → ${roleValue}`);
        } else {
          const body = await inviteRes.text();
          // May already be a member
          if (body.includes("already") || inviteRes.status() === 409) {
            console.log(`  ℹ️ ${roleName} already in tenant`);
          } else {
            console.log(`  ⚠️ ${roleName}: ${inviteRes.status()} ${body.slice(0, 100)}`);
          }
        }
      } catch (err) {
        console.log(`  ⚠️ ${roleName}: ${err}`);
      }
    }

    await adminCtx.dispose();
  }

  // Step 5: Generate engine API keys
  if (ADMIN_API_KEY || tenantId) {
    console.log("🔑 Generating engine API keys...");
    try {
      const adminKey = ADMIN_API_KEY;
      if (adminKey && tenantId) {
        const keyRes = await ctx.post(`${ENGINE_BASE}/api/v1/admin/tenants/${tenantId}/keys`, {
          headers: { "X-Admin-Key": adminKey },
          data: { label: "e2e-test-key" },
        });
        if (keyRes.ok()) {
          const keyData = await keyRes.json();
          engineApiKey = keyData.api_key ?? keyData.key ?? "";
          console.log(`  ✅ Engine API key created`);
        }
      }
    } catch (err) {
      console.log(`  ⚠️ API key gen: ${err}`);
    }
  }

  // Persist state
  const state: TestState = {
    tenantId,
    tenantSlug,
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
