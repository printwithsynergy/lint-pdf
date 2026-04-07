import { requirePermission } from "@/lib/require-permission";

export default async function WebhooksLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePermission("webhooks:manage");
  return children as React.JSX.Element;
}
