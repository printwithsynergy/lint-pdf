import { requirePermission } from "@/lib/require-permission";

export default async function ApprovalsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePermission("preflight:manage");
  return children as React.JSX.Element;
}
