import { ensureRegistry } from "@/lib/plugins";

export default async function AdminPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/admin");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Site Administration</h1>
      <p className="mt-2 text-muted-foreground">
        Manage platform settings and users.
      </p>
    </main>
  );
}
