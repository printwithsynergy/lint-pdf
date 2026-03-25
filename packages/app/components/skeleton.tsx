/**
 * Skeleton loading components for dashboard pages.
 *
 * Uses Tailwind `animate-pulse` for a shimmer effect that matches the
 * eventual layout, reducing perceived load time.
 */

function SkeletonLine({ width = "100%" }: { width?: string }) {
  return (
    <div className="h-4 animate-pulse rounded bg-muted" style={{ width }} />
  );
}

function SkeletonBlock({ height = "h-10" }: { height?: string }) {
  return <div className={`w-full animate-pulse rounded bg-muted ${height}`} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg border p-6 space-y-3">
      <SkeletonLine width="40%" />
      <SkeletonLine width="70%" />
      <SkeletonLine width="55%" />
    </div>
  );
}

export function SkeletonTable({
  rows = 5,
  cols = 4,
}: {
  rows?: number;
  cols?: number;
}) {
  return (
    <div className="rounded-lg border overflow-hidden">
      {/* Header */}
      <div className="border-b bg-muted/30 px-4 py-3 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="flex-1">
            <SkeletonLine width="60%" />
          </div>
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="border-b last:border-0 px-4 py-3 flex gap-4">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="flex-1">
              <SkeletonLine width={c === 0 ? "80%" : "50%"} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonForm({ fields = 4 }: { fields?: number }) {
  return (
    <div className="space-y-6">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          <SkeletonLine width="20%" />
          <SkeletonBlock />
        </div>
      ))}
      <SkeletonBlock height="h-10" />
    </div>
  );
}

export function SkeletonPageHeader() {
  return (
    <div className="space-y-2">
      <SkeletonLine width="30%" />
      <SkeletonLine width="50%" />
    </div>
  );
}

export function SkeletonDashboard({
  type,
}: {
  type: "table" | "cards" | "form" | "detail";
}) {
  return (
    <main className="p-8 max-w-4xl">
      <SkeletonPageHeader />
      <div className="mt-6">
        {type === "table" && <SkeletonTable />}
        {type === "cards" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        )}
        {type === "form" && <SkeletonForm />}
        {type === "detail" && (
          <>
            <SkeletonForm fields={3} />
            <div className="mt-6">
              <SkeletonTable rows={3} cols={3} />
            </div>
          </>
        )}
      </div>
    </main>
  );
}
