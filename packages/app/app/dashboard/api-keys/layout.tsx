import { requirePermission } from "@/lib/require-permission";

export default async function ApiKeysLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePermission("api-keys:manage");
  return children as React.JSX.Element;
}
