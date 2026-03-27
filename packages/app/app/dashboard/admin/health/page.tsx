"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { Button } from "@thinkneverland/pixie-dust-ui";

interface HealthStatus {
  status: string;
  service: string;
  version?: string;
  database?: string;
  redis?: string;
  queue_depth?: number;
  queue_depths?: Record<string, number>;
  worker_count?: number;
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-3 w-3 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
    />
  );
}

export default function AdminHealthPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchHealth = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/admin/health");
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(
          (data as { error?: string }).error ??
            `Health check failed (${resp.status})`,
        );
      }
      setHealth(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Health check failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  if (loading) {
    return <SkeletonDashboard type="cards" />;
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold">System Health</h1>
        <Button
          variant="secondary"
          onClick={() => {
            setLoading(true);
            fetchHealth();
          }}
        >
          Refresh
        </Button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {health && (
        <div className="mt-6 space-y-4">
          <div className="rounded-lg border p-4">
            <div className="flex items-center gap-3">
              <StatusDot
                ok={health.status === "ok" || health.status === "healthy"}
              />
              <div>
                <span className="text-lg font-semibold">
                  {health.service} Engine
                </span>
                {health.version && (
                  <span className="ml-2 text-sm text-muted-foreground">
                    v{health.version}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <StatusDot
                  ok={
                    health.database === "ok" || health.database === "connected"
                  }
                />
                <span className="font-medium">Database</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {health.database ?? "unknown"}
              </p>
            </div>
            <div className="rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <StatusDot
                  ok={health.redis === "ok" || health.redis === "connected"}
                />
                <span className="font-medium">Redis</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {health.redis ?? "unknown"}
              </p>
            </div>
          </div>

          <div className="rounded-lg border p-4">
            <h2 className="font-semibold">Queue</h2>
            <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
              <div>
                <span className="text-muted-foreground">Total Depth:</span>{" "}
                <strong>{health.queue_depth ?? 0}</strong>
              </div>
              <div>
                <span className="text-muted-foreground">Workers:</span>{" "}
                <strong>{health.worker_count ?? 0}</strong>
              </div>
            </div>
            {health.queue_depths &&
              Object.keys(health.queue_depths).length > 0 && (
                <div className="mt-2 space-y-1">
                  {Object.entries(health.queue_depths).map(([q, depth]) => (
                    <div
                      key={q}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="text-muted-foreground">{q}</span>
                      <span className="font-medium">{Math.max(0, depth)}</span>
                    </div>
                  ))}
                </div>
              )}
          </div>
        </div>
      )}
    </>
  );
}
