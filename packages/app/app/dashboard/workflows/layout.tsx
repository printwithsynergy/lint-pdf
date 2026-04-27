import { requirePermission } from "@/lib/require-permission";

export default async function WorkflowsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Reuse the same permission gate as legacy /dashboard/endpoints —
  // workflows are the Phase 0.7 substrate replacing CustomEndpoint.
  await requirePermission("endpoints:manage");
  return children as React.JSX.Element;
}
