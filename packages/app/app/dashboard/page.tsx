import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { getCookieName } from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get(getCookieName())?.value;
  const auth = await authenticateRequest(
    prisma,
    token ? `${getCookieName()}=${token}` : null,
  );

  if (!auth) {
    redirect("/auth/login");
  }

  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: { id: true, email: true, name: true },
  });

  const tenants = await prisma.tenantUser.findMany({
    where: { userId: auth.userId },
    include: {
      tenant: { select: { id: true, name: true, slug: true, status: true } },
    },
    orderBy: { joinedAt: "asc" },
  });

  return (
    <>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Welcome back, {user?.name ?? user?.email}
            </p>
          </div>
          <a
            href="/api/auth/logout"
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-secondary transition-colors"
          >
            Sign Out
          </a>
        </div>

        <div className="grid gap-6">
          <section>
            <h2 className="text-lg font-semibold mb-4">Your Organizations</h2>
            {tenants.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-8 text-center">
                <p className="text-muted-foreground">
                  You don&apos;t belong to any organizations yet.
                </p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {tenants.map((membership: (typeof tenants)[number]) => (
                  <a
                    key={membership.id}
                    href={`/dashboard/${membership.tenant.slug}`}
                    className="rounded-lg border border-border p-4 hover:bg-secondary/50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">
                        {membership.tenant.name}
                      </h3>
                      <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                        {membership.role}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      /{membership.tenant.slug}
                    </p>
                  </a>
                ))}
              </div>
            )}
          </section>
        </div>
    </>
  );
}
