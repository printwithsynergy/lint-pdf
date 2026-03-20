import { ensureRegistry } from "@/lib/plugins";

export default async function TeamPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/team");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Team</h1>
      <p className="mt-2 text-muted-foreground">
        Manage team members and permissions.
      </p>
    </main>
  );
}
