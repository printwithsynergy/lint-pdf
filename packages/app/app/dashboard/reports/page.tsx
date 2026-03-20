import { ensureRegistry } from "@/lib/plugins";

export default async function ReportsPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/reports");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Reports</h1>
      <p className="mt-2 text-muted-foreground">
        View and download your preflight reports.
      </p>
    </main>
  );
}
