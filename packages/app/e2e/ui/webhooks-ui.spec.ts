import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Webhooks Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");
    await expect(
      page.locator("main").getByRole("heading", { name: /webhooks/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows description text", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");
    await expect(
      page.getByText(/receive real-time notifications/i),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows existing webhooks or empty state", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");
    await page.waitForTimeout(3_000);

    const hasWebhooks = await page.getByRole("button", { name: /test/i }).first().isVisible().catch(() => false);
    if (!hasWebhooks) {
      await expect(page.getByText(/no webhooks configured/i)).toBeVisible({ timeout: 15_000 });
      await expect(
        page.getByText(/add one to start receiving event notifications/i),
      ).toBeVisible();
    }
    await context.close();
  });

  test("add webhook button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");

    const addButton = page.getByRole("button", { name: /add webhook/i }).first();
    await expect(addButton).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("clicking add webhook shows create form with URL input", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");

    await page.getByRole("button", { name: /add webhook/i }).first().click();

    await expect(
      page.locator("main").getByRole("heading", { name: /new webhook/i }).first(),
    ).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("#webhook-url")).toBeVisible();
    await context.close();
  });

  test("create form shows event type checkboxes", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");

    await page.getByRole("button", { name: /add webhook/i }).first().click();
    await page.waitForTimeout(1_000);

    // Should show event checkboxes (use .first() since existing webhooks may also display these event names)
    await expect(page.getByText("job.completed").first()).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("job.failed").first()).toBeVisible();

    // Checkboxes should be checked by default
    const completedCheckbox = page.locator("input[type='checkbox']").first();
    await expect(completedCheckbox).toBeChecked();
    await context.close();
  });

  test("create webhook button is disabled without URL", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");

    await page.getByRole("button", { name: /add webhook/i }).first().click();
    await page.waitForTimeout(1_000);

    const createButton = page.getByRole("button", { name: /create webhook/i });
    await expect(createButton).toBeVisible({ timeout: 5_000 });
    await expect(createButton).toBeDisabled();
    await context.close();
  });

  test("existing webhooks show URL, events, and action buttons", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");
    await page.waitForTimeout(3_000);

    const testButton = page.getByRole("button", { name: /test/i }).first();
    const hasWebhooks = await testButton.isVisible().catch(() => false);
    if (hasWebhooks) {
      // Should show event badges
      await expect(
        page.getByText(/job\.completed|job\.failed/).first(),
      ).toBeVisible();
      // Should have action buttons
      await expect(testButton).toBeVisible();
      await expect(page.getByRole("button", { name: /edit/i }).first()).toBeVisible();
      await expect(page.getByRole("button", { name: /disable|enable/i }).first()).toBeVisible();
      await expect(page.getByRole("button", { name: /delete/i }).first()).toBeVisible();
    }
    await context.close();
  });

  test("delete webhook opens confirm dialog", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");
    await page.waitForTimeout(3_000);

    const deleteButton = page.getByRole("button", { name: /delete/i }).first();
    const hasWebhooks = await deleteButton.isVisible().catch(() => false);
    if (hasWebhooks) {
      await deleteButton.click();
      await expect(page.getByText(/delete webhook\?/i)).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/this action cannot be undone/i)).toBeVisible();
    }
    await context.close();
  });

  test("edit button shows edit form inline", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/webhooks");
    await page.waitForTimeout(3_000);

    const editButton = page.getByRole("button", { name: /edit/i }).first();
    const hasWebhooks = await editButton.isVisible().catch(() => false);
    if (hasWebhooks) {
      await editButton.click();
      // Edit form should show save and cancel buttons
      await expect(page.getByRole("button", { name: /save/i })).toBeVisible({ timeout: 5_000 });
      await expect(page.getByRole("button", { name: /cancel/i })).toBeVisible();
    }
    await context.close();
  });
});
