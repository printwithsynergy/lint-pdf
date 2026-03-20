import { ensureRegistry } from "@/lib/plugins";

export default async function UsagePage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/usage");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Usage</h1>
      <p className="mt-2 text-muted-foreground">
        Track your preflight usage and limits.
      </p>
    </main>
  );
}
