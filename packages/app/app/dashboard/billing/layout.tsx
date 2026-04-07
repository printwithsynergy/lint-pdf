import { requirePermission } from "@/lib/require-permission";

export default async function BillingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePermission("billing:manage");
  return children as React.JSX.Element;
}
