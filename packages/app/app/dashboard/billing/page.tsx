import { ensureRegistry } from "@/lib/plugins";

export default async function BillingPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/billing");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Billing</h1>
      <p className="mt-2 text-muted-foreground">
        Manage your subscription and invoices.
      </p>
    </main>
  );
}
