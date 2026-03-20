import { ensureRegistry } from "@/lib/plugins";

export default async function FlightPlansPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/flight-plans");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Flight Plans</h1>
      <p className="mt-2 text-muted-foreground">
        Manage your preflight inspection profiles.
      </p>
    </main>
  );
}
