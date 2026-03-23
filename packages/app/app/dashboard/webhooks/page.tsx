"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface WebhookEndpoint {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

const AVAILABLE_EVENTS = ["job.completed", "job.failed"];

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newEvents, setNewEvents] = useState<string[]>([
    "job.completed",
    "job.failed",
  ]);
  const [creating, setCreating] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editUrl, setEditUrl] = useState("");
  const [editEvents, setEditEvents] = useState<string[]>([]);

  // Test state
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    id: string;
    success: boolean;
    status_code: number;
    error: string;
  } | null>(null);

  const fetchWebhooks = useCallback(async () => {
    try {
      const resp = await fetch("/api/grounded/webhook-endpoints");
      if (!resp.ok) throw new Error("Failed to load webhooks");
      const data = await resp.json();
      setWebhooks(data.webhooks ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load webhooks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWebhooks();
  }, [fetchWebhooks]);

  async function handleCreate() {
    setCreating(true);
    setError("");
    try {
      const resp = await fetch("/api/grounded/webhook-endpoints", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: newUrl, events: newEvents }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to create webhook");
      }
      setNewUrl("");
      setNewEvents(["job.completed", "job.failed"]);
      setShowCreate(false);
      await fetchWebhooks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create webhook");
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdate(id: string) {
    setError("");
    try {
      const resp = await fetch(`/api/grounded/webhook-endpoints/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: editUrl, events: editEvents }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to update webhook");
      }
      setEditingId(null);
      await fetchWebhooks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update webhook");
    }
  }

  async function handleToggle(id: string, is_active: boolean) {
    try {
      await fetch(`/api/grounded/webhook-endpoints/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !is_active }),
      });
      await fetchWebhooks();
    } catch {
      setError("Failed to toggle webhook");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this webhook?")) return;
    try {
      await fetch(`/api/grounded/webhook-endpoints/${id}`, {
        method: "DELETE",
      });
      await fetchWebhooks();
    } catch {
      setError("Failed to delete webhook");
    }
  }

  async function handleTest(id: string) {
    setTestingId(id);
    setTestResult(null);
    try {
      const resp = await fetch(`/api/grounded/webhook-endpoints/${id}/test`, {
        method: "POST",
      });
      const data = await resp.json();
      setTestResult({ id, ...data });
    } catch {
      setTestResult({
        id,
        success: false,
        status_code: 0,
        error: "Network error",
      });
    } finally {
      setTestingId(null);
    }
  }

  function toggleEvent(
    events: string[],
    setter: (e: string[]) => void,
    event: string,
  ) {
    setter(
      events.includes(event)
        ? events.filter((e) => e !== event)
        : [...events, event],
    );
  }

  if (loading) {
    return <SkeletonDashboard type="table" />;
  }

  return (
    <main className="p-8 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Webhooks</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Receive real-time notifications when preflight jobs complete or
            fail.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showCreate ? "Cancel" : "Add Webhook"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">New Webhook</h2>
          <div className="mt-3 space-y-3">
            <div>
              <label className="block text-sm font-medium">
                Endpoint URL (HTTPS)
              </label>
              <input
                type="url"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="https://your-app.com/webhooks/lintpdf"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">Events</label>
              <div className="mt-1 flex flex-wrap gap-2">
                {AVAILABLE_EVENTS.map((event) => (
                  <label
                    key={event}
                    className="flex items-center gap-1.5 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={newEvents.includes(event)}
                      onChange={() =>
                        toggleEvent(newEvents, setNewEvents, event)
                      }
                    />
                    {event}
                  </label>
                ))}
              </div>
            </div>
            <button
              onClick={handleCreate}
              disabled={creating || !newUrl}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Webhook"}
            </button>
          </div>
        </div>
      )}

      {/* Webhook list */}
      <div className="mt-6 space-y-4">
        {webhooks.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
            No webhooks configured. Add one to start receiving event
            notifications.
          </div>
        ) : (
          webhooks.map((wh) => (
            <div key={wh.id} className="rounded-lg border p-4">
              {editingId === wh.id ? (
                <div className="space-y-3">
                  <input
                    type="url"
                    value={editUrl}
                    onChange={(e) => setEditUrl(e.target.value)}
                    className="w-full rounded-md border px-3 py-2 text-sm"
                  />
                  <div className="flex flex-wrap gap-2">
                    {AVAILABLE_EVENTS.map((event) => (
                      <label
                        key={event}
                        className="flex items-center gap-1.5 text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={editEvents.includes(event)}
                          onChange={() =>
                            toggleEvent(editEvents, setEditEvents, event)
                          }
                        />
                        {event}
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdate(wh.id)}
                      className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="rounded-md border px-3 py-1.5 text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${wh.is_active ? "bg-green-500" : "bg-gray-300"}`}
                        />
                        <code className="truncate text-sm">{wh.url}</code>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {wh.events.map((ev) => (
                          <span
                            key={ev}
                            className="rounded bg-muted px-1.5 py-0.5 text-xs"
                          >
                            {ev}
                          </span>
                        ))}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Created {new Date(wh.created_at).toLocaleDateString()}
                      </p>
                      {testResult?.id === wh.id && (
                        <div
                          className={`mt-2 rounded px-2 py-1 text-xs ${testResult.success ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}
                        >
                          {testResult.success
                            ? `Test delivered (HTTP ${testResult.status_code})`
                            : `Test failed: ${testResult.error}`}
                        </div>
                      )}
                    </div>
                    <div className="ml-4 flex shrink-0 gap-1">
                      <button
                        onClick={() => handleTest(wh.id)}
                        disabled={testingId === wh.id}
                        className="rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                        title="Send test payload"
                      >
                        {testingId === wh.id ? "Testing..." : "Test"}
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(wh.id);
                          setEditUrl(wh.url);
                          setEditEvents(wh.events);
                        }}
                        className="rounded border px-2 py-1 text-xs hover:bg-muted"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleToggle(wh.id, wh.is_active)}
                        className="rounded border px-2 py-1 text-xs hover:bg-muted"
                      >
                        {wh.is_active ? "Disable" : "Enable"}
                      </button>
                      <button
                        onClick={() => handleDelete(wh.id)}
                        className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </main>
  );
}
