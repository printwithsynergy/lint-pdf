import { requirePermission } from "@/lib/require-permission";

export default async function TeamInviteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePermission("team:manage");
  return children as React.JSX.Element;
}
