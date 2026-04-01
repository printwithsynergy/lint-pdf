import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { notFound, redirect } from "next/navigation";

export default async function TenantSlugPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const tenant = await prisma.tenant.findUnique({ where: { slug } });
  if (!tenant) notFound();
  redirect("/dashboard/preflight");
}
