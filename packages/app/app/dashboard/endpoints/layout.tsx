import { requirePermission } from "@/lib/require-permission";

export default async function EndpointsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePermission("endpoints:manage");
  return children as React.JSX.Element;
}
