import { ensureRegistry } from "@/lib/plugins";

export default async function PreflightPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/preflight");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Preflight Jobs</h1>
      <p className="mt-2 text-muted-foreground">
        Submit and manage your PDF preflight inspections.
      </p>
    </main>
  );
}
