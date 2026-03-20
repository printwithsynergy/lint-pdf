import { ensureRegistry } from "@/lib/plugins";

export default async function AccountPage() {
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent("/dashboard/account");

  if (PageComponent) {
    return <PageComponent />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Account</h1>
      <p className="mt-2 text-muted-foreground">
        Manage your account settings.
      </p>
    </main>
  );
}
