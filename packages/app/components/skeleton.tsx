/**
 * Skeleton loading components for dashboard pages.
 *
 * Re-exports from Pixie Dust UI where possible, with app-specific
 * composite skeletons for common page layouts.
 */

export { Skeleton, SkeletonText, SkeletonCard } from "@thinkneverland/pixie-dust-ui";

import { Skeleton, SkeletonCard } from "@thinkneverland/pixie-dust-ui";
import { Card, CardContent, CardHeader } from "@thinkneverland/pixie-dust-ui";

export function SkeletonTable({
  rows = 5,
  cols = 4,
}: {
  rows?: number;
  cols?: number;
}) {
  return (
    <Card>
      <CardContent>
        <div className="flex gap-4 py-3">
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} className="flex-1">
              <Skeleton className="h-4 w-3/5" />
            </div>
          ))}
        </div>
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4 border-t py-3">
            {Array.from({ length: cols }).map((_, c) => (
              <div key={c} className="flex-1">
                <Skeleton className={c === 0 ? "h-4 w-4/5" : "h-4 w-1/2"} />
              </div>
            ))}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function SkeletonForm({ fields = 4 }: { fields?: number }) {
  return (
    <Card>
      <CardContent className="space-y-6">
        {Array.from({ length: fields }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-1/5" />
            <Skeleton className="h-10 w-full" />
          </div>
        ))}
        <Skeleton className="h-10 w-full" />
      </CardContent>
    </Card>
  );
}

export function SkeletonPageHeader() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-6 w-1/3" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}

export function SkeletonDashboard({
  type,
}: {
  type: "table" | "cards" | "form" | "detail";
}) {
  return (
    <>
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
    </>
  );
}
