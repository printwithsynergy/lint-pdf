import { ensureRegistry } from "@/lib/plugins";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  const registry = await ensureRegistry();
  const PageComponent = registry.getPageComponent(
    "/dashboard/preflight/[jobId]",
  );

  if (PageComponent) {
    return <PageComponent jobId={jobId} />;
  }

  return (
    <main className="p-8">
      <h1 className="font-display text-2xl font-bold">Job Details</h1>
      <p className="mt-2 text-muted-foreground">Job ID: {jobId}</p>
    </main>
  );
}
