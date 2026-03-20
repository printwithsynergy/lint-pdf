import { ensureRegistry } from "@/lib/plugins";

export default async function WaitlistPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/waitlist");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Waitlist</h1>
      <p className="mt-2 text-muted-foreground">
        Manage waitlist entries and promotions.
      </p>
    </main>
  );
}
