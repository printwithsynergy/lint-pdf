import { requirePermission } from "@/lib/require-permission";

export default async function AccountLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePermission("account:manage");
  return children as React.JSX.Element;
}
